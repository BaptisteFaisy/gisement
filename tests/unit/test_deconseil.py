"""Lot 15 - category E: what must not be automated (chapter 16, EF-44)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from gisement.deconseil import (
    ORDRE_MOTIFS,
    formuler,
    motif_deconseil,
    part_deconseilles,
    qualifier_portefeuille,
    tous_les_motifs,
    type_final,
)
from gisement.faisabilite import evaluer_faisabilite
from gisement.types import (
    DecompositionCout,
    Gisement,
    Intervalle,
    Langue,
    MotifDeconseil,
    Processus,
    StatutValidation,
    TypeAutomatisation,
)
from tests.fakes.builders import (
    faits_depuis_spec,
    gisement_depuis_attendu,
    identifiants_verite,
    processus_depuis_spec,
    processus_verite,
)

BASE = {
    "id": "P-TEST",
    "campagne_id": "CMP-DEMO",
    "nom": "test",
    "service": "adv",
    "validation": StatutValidation.EN_ATTENTE,
}


def processus(**kw) -> Processus:
    return Processus(**{**BASE, **kw})


def gisement(
    gain_annuel: str, delai: str | None = "12.0", net: str = "10.0", cout_annee_1: str = "5000"
) -> Gisement:
    return Gisement(
        processus_id="P-TEST",
        temps_brut_heures=Decimal(net),
        coefficient_fragmentation=Decimal("0.70"),
        temps_fragmente_heures=Decimal(net),
        temps_transfere_heures=Decimal(0),
        detail_transfert=(),
        temps_ineliminable_heures=Decimal(0),
        temps_net_heures=Decimal(net),
        temps_net_intervalle=Intervalle(bas=Decimal(net), haut=Decimal(net)),
        cout=DecompositionCout(annee_1=Decimal(cout_annee_1), recurrent=Decimal("500")),
        taux_horaire=Decimal("42"),
        gain_mensuel=Decimal(gain_annuel) / 12,
        gain_annuel=Decimal(gain_annuel),
        delai_retour_mois=Decimal(delai) if delai else None,
    )


def test_les_six_motifs_de_deconseil_se_declenchent_seuls():
    """16.1 - each reason is a rule on measured facts, not an opinion."""
    from gisement.types import FaitsFaisabilite

    assert motif_deconseil(processus(), gisement("1000"), FaitsFaisabilite()).motif == (
        MotifDeconseil.VOLUME_INSUFFISANT
    )
    assert motif_deconseil(processus(), gisement("9000", "40"), FaitsFaisabilite()).motif == (
        MotifDeconseil.RETOUR_TROP_LONG
    )
    assert (
        motif_deconseil(processus(), gisement("9000"), FaitsFaisabilite(), Decimal("0.55")).motif
        == MotifDeconseil.JUGEMENT_NON_FORMALISABLE
    )
    assert (
        motif_deconseil(processus(), gisement("9000"), FaitsFaisabilite(obligation_legale_humaine=True)).motif
        == MotifDeconseil.OBLIGATION_LEGALE
    )
    assert (
        motif_deconseil(processus(changements_douze_mois=3), gisement("9000"), FaitsFaisabilite()).motif
        == MotifDeconseil.INSTABILITE
    )
    assert (
        motif_deconseil(
            processus(), gisement("9000"), FaitsFaisabilite(dependance_externe_non_contractuelle=True)
        ).motif
        == MotifDeconseil.DEPENDANCE_EXTERNE
    )


def test_un_processus_sain_n_est_pas_deconseille():
    from gisement.types import FaitsFaisabilite

    assert motif_deconseil(processus(), gisement("9000", "10"), FaitsFaisabilite()) is None


def test_chaque_deconseil_porte_sa_condition_de_reexamen():
    """16.2 - a "no" is published as a "not yet"."""
    from gisement.types import FaitsFaisabilite

    for motif in MotifDeconseil:
        assert motif in ORDRE_MOTIFS
    deconseille = motif_deconseil(processus(), gisement("1000"), FaitsFaisabilite())
    assert "reexamen" in deconseille.condition_reexamen
    assert "15 occurrences" in deconseille.condition_reexamen


def test_la_formulation_reprend_les_chiffres_sans_les_calculer():
    """21.5 - the writer formats figures it is given, it never computes one."""
    from gisement.types import FaitsFaisabilite

    deconseille = motif_deconseil(
        processus(), gisement("3024", "44", net="6.0", cout_annee_1="11000"), FaitsFaisabilite()
    )
    texte = formuler(deconseille, Langue.FR)
    assert texte.startswith("Ne pas automatiser")
    assert "6.0" in texte and "3024" in texte and "11000" in texte and "44" in texte
    assert "reexamen" in texte
    anglais = formuler(deconseille, Langue.EN)
    assert anglais.startswith("Do not automate")
    assert "3024" in anglais


def test_tous_les_motifs_sont_publies_dans_l_ordre_du_chapitre_16():
    from gisement.types import FaitsFaisabilite

    motifs = tous_les_motifs(
        processus(changements_douze_mois=3),
        gisement("1000", "40"),
        FaitsFaisabilite(obligation_legale_humaine=True),
        Decimal("0.55"),
    )
    assert [m.motif for m in motifs] == [
        MotifDeconseil.OBLIGATION_LEGALE,
        MotifDeconseil.INSTABILITE,
        MotifDeconseil.VOLUME_INSUFFISANT,
        MotifDeconseil.JUGEMENT_NON_FORMALISABLE,
        MotifDeconseil.RETOUR_TROP_LONG,
    ]


def test_un_processus_deconseille_passe_en_categorie_E():
    from gisement.types import FaitsFaisabilite

    faits = FaitsFaisabilite(api_ou_flux_natif=True, interface_stable=True)
    faisabilite = evaluer_faisabilite(processus(), faits)
    assert faisabilite.type == TypeAutomatisation.B
    deconseille = motif_deconseil(processus(), gisement("1000"), faits)
    assert type_final(faisabilite, deconseille) == TypeAutomatisation.E
    assert type_final(faisabilite, None) == TypeAutomatisation.B


@pytest.mark.parametrize("spec", processus_verite(), ids=identifiants_verite())
def test_les_23_processus_du_jeu_de_demo(spec):
    """Ground truth: the headline reason and every reason match annex E."""
    processus_spec = processus_depuis_spec(spec)
    faits = faits_depuis_spec(spec)
    gisement_spec = gisement_depuis_attendu(spec)
    attendus = spec["deconseil_attendu"]
    motifs = tous_les_motifs(processus_spec, gisement_spec, faits, Decimal(spec["part_atypique"]))
    assert [m.motif.value for m in motifs] == [a["motif"] for a in attendus], spec["id"]
    headline = motif_deconseil(processus_spec, gisement_spec, faits, Decimal(spec["part_atypique"]))
    if attendus:
        assert headline is not None and headline.motif.value == attendus[0]["motif"]
        assert type_final(evaluer_faisabilite(processus_spec, faits), headline) == TypeAutomatisation.E
    else:
        assert headline is None


def test_r15_dix_processus_sous_le_seuil_donnent_dix_categorie_E():
    from gisement.types import FaitsFaisabilite

    deconseilles = []
    for index in range(10):
        processus_test = processus(id=f"P-FAIBLE-{index}")
        deconseille = motif_deconseil(processus_test, gisement("2900"), FaitsFaisabilite())
        assert deconseille is not None
        assert deconseille.motif == MotifDeconseil.VOLUME_INSUFFISANT
        assert deconseille.condition_reexamen
        deconseilles.append(deconseille)
    assert len(deconseilles) == 10


def test_r16_la_part_de_categorie_E_du_jeu_de_demo_est_saine():
    """KPI-9 - between 15 % and 30 % of the portfolio."""
    specs = processus_verite()
    nb_e = sum(1 for s in specs if s["type_final_attendu"] == "E")
    part = part_deconseilles(nb_e, len(specs))
    assert nb_e == 6
    assert Decimal("0.15") <= part <= Decimal("0.30")
    assert qualifier_portefeuille(part) == "portefeuille sain"


def test_les_bandes_de_qualification_du_portefeuille():
    assert "complaisant" in qualifier_portefeuille(Decimal("0.05"))
    assert "sain" in qualifier_portefeuille(Decimal("0.22"))
    assert "elevee" in qualifier_portefeuille(Decimal("0.35"))
    assert "mal choisi" in qualifier_portefeuille(Decimal("0.55"))
    assert part_deconseilles(0, 0) == Decimal(0)
