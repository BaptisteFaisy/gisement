"""Idea #9 - a sequence is not a schedule: capacity and dependencies."""

from __future__ import annotations

from decimal import Decimal

from gisement.planification import (
    Capacite,
    Dependance,
    chemin_critique,
    gantt,
    jours_necessaires,
    planifier,
)
from gisement.types.communs import Risque, TypeAutomatisation, Vague
from gisement.types.economie import (
    DecompositionCout,
    Faisabilite,
    Gisement,
    Intervalle,
    Projet,
)


def projet(identifiant: str, score: str, cout: str, gain: str = "6000", type_: str = "B") -> Projet:
    gisement = Gisement(
        processus_id=identifiant,
        temps_brut_heures=Decimal(20),
        coefficient_fragmentation=Decimal("0.7"),
        temps_fragmente_heures=Decimal(14),
        temps_transfere_heures=Decimal(2),
        detail_transfert=(),
        temps_ineliminable_heures=Decimal(2),
        temps_net_heures=Decimal(10),
        temps_net_intervalle=Intervalle(bas=Decimal(8), haut=Decimal(12)),
        cout=DecompositionCout(developpement=Decimal(cout), annee_1=Decimal(cout), recurrent=Decimal(500)),
        taux_horaire=Decimal(42),
        gain_mensuel=Decimal(gain) / 12,
        gain_annuel=Decimal(gain),
        delai_retour_mois=Decimal(6),
    )
    return Projet(
        id=f"PRJ-{identifiant}",
        processus_id=identifiant,
        gisement=gisement,
        faisabilite=Faisabilite(processus_id=identifiant, type=TypeAutomatisation(type_)),
        risque=Risque.FAIBLE,
        score=Decimal(score),
        vague=Vague.STRUCTUREL,
    )


def test_les_jours_viennent_du_cout() -> None:
    assert jours_necessaires(projet("P-1", "0.8", "3000")) == Decimal(5)
    assert jours_necessaires(projet("P-2", "0.8", "3400")) == Decimal(6)  # arrondi au jour superieur


def test_trois_projets_sans_dependance_sont_planifies_par_score() -> None:
    projets = [projet("P-A", "0.5", "1500"), projet("P-B", "0.9", "1500"), projet("P-C", "0.7", "1500")]
    plan = planifier(projets, capacite=Capacite(consultants=1, jours_par_mois=15))
    # three projects of three days fit in one month; within a month the tasks are
    # listed by id, which keeps the plan deterministic
    assert {t.projet_id for t in plan.taches} == {"P-A", "P-B", "P-C"}
    assert {t.debut_mois for t in plan.taches} == {1}
    assert plan.impossibles == ()
    assert plan.duree_totale_mois >= 1
    assert Decimal(0) < plan.capacite_utilisee <= Decimal(1)


def test_les_dependances_sont_respectees() -> None:
    projets = [projet("P-A", "0.9", "1500"), projet("P-B", "0.5", "1500")]
    dependances = [Dependance(projet_id="P-A", apres=("P-B",), raison="le B supprime le volume du A")]
    plan = planifier(projets, dependances, capacite=Capacite(consultants=1, jours_par_mois=3))
    ordre = {t.projet_id: t.debut_mois for t in plan.taches}
    assert ordre["P-B"] < ordre["P-A"], "malgre son meilleur score, P-A attend P-B"
    tache_a = next(t for t in plan.taches if t.projet_id == "P-A")
    assert "P-B" in tache_a.dependances_respectees


def test_un_cycle_est_signale_et_non_bloquant() -> None:
    projets = [projet("P-A", "0.9", "1500"), projet("P-B", "0.5", "1500")]
    dependances = [
        Dependance(projet_id="P-A", apres=("P-B",)),
        Dependance(projet_id="P-B", apres=("P-A",)),
    ]
    plan = planifier(projets, dependances)
    assert set(plan.impossibles) == {"P-A", "P-B"}
    assert "circulaire" in plan.raisons["P-A"]


def test_un_projet_trop_gros_pour_un_mois_est_impossible() -> None:
    projets = [projet("P-GEANT", "0.9", "90000")]
    plan = planifier(projets, capacite=Capacite(consultants=1, jours_par_mois=15))
    assert plan.impossibles == ("P-GEANT",)
    assert "capacite mensuelle" in plan.raisons["P-GEANT"]


def test_la_capacite_mensuelle_est_saturee_avant_de_passer_au_mois_suivant() -> None:
    projets = [projet("P-A", "0.9", "6500"), projet("P-B", "0.8", "6500")]  # 10 jours chacun
    plan = planifier(projets, capacite=Capacite(consultants=1, jours_par_mois=15))
    mois = {t.projet_id: t.debut_mois for t in plan.taches}
    assert mois["P-A"] == 1 and mois["P-B"] == 2
    double = planifier(projets, capacite=Capacite(consultants=2, jours_par_mois=15))
    assert {t.debut_mois for t in double.taches} == {1}


def test_les_projets_deconseilles_ne_sont_pas_planifies() -> None:
    from gisement.types.communs import MotifDeconseil
    from gisement.types.economie import Deconseille

    deconseille = projet("P-E", "0.9", "1500", type_="E")
    from dataclasses import replace

    deconseille = replace(
        deconseille,
        deconseille=Deconseille(
            processus_id="P-E",
            motif=MotifDeconseil.VOLUME_INSUFFISANT,
            seuil_atteint="gain < 3000",
            condition_reexamen="volume > 15/mois",
        ),
    )
    plan = planifier([deconseille, projet("P-A", "0.5", "1500")])
    assert [t.projet_id for t in plan.taches] == ["P-A"]


def test_le_chemin_critique_est_la_plus_longue_chaine() -> None:
    projets = [projet("P-A", "0.9", "6500"), projet("P-B", "0.8", "13000"), projet("P-C", "0.7", "6500")]
    dependances = [
        Dependance(projet_id="P-C", apres=("P-B",)),
        Dependance(projet_id="P-B", apres=("P-A",)),
    ]
    assert chemin_critique(projets, dependances) == ("P-A", "P-B", "P-C")


def test_le_gantt_affiche_une_ligne_par_tache() -> None:
    projets = [projet("P-A", "0.9", "6500"), projet("P-B", "0.8", "6500")]
    plan = planifier(projets, capacite=Capacite(consultants=1, jours_par_mois=10))
    rendu = gantt(plan)
    assert "P-A" in rendu and "P-B" in rendu
    assert rendu.count("\n") == 1
    assert gantt(planifier([])) == "(aucune tache planifiee)"


def test_l_horizon_borne_le_plan() -> None:
    projets = [projet(f"P-{i}", "0.5", "6500") for i in range(6)]
    plan = planifier(projets, capacite=Capacite(consultants=1, jours_par_mois=10), horizon_mois=2)
    assert len(plan.taches) == 2
    assert len(plan.impossibles) == 4
    assert all("horizon" in plan.raisons[p] for p in plan.impossibles)


def test_le_gain_cumule_est_la_somme_des_projets_planifies() -> None:
    projets = [projet("P-A", "0.9", "1500", gain="6000"), projet("P-B", "0.8", "1500", gain="4000")]
    plan = planifier(projets)
    assert plan.gain_cumule == Decimal("10000.00")
