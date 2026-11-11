"""R4 / 17.2 - the interval is simulated, deterministic, and honest."""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

from gisement.calcul import calculer, incertitudes, simuler
from gisement.types import TIRAGES_MONTE_CARLO, EntreeGisement, FormeIncertitude, StatutDuree


def test_deux_executions_a_graine_identique_donnent_le_meme_intervalle(cas_reference) -> None:
    premier, _ = simuler(cas_reference)
    second, _ = simuler(cas_reference)
    assert (premier.bas, premier.haut) == (second.bas, second.haut)


def test_une_graine_differente_donne_un_intervalle_different(cas_reference) -> None:
    autre, _ = simuler(replace(cas_reference, graine=999))
    attendu, _ = simuler(cas_reference)
    assert (autre.bas, autre.haut) != (attendu.bas, attendu.haut)


def test_le_nombre_de_tirages_est_celui_du_contrat(cas_reference) -> None:
    g = calculer(cas_reference)
    assert g.tirages == TIRAGES_MONTE_CARLO == 10_000


def test_l_intervalle_contient_la_valeur_ponctuelle(cas_reference) -> None:
    g = calculer(cas_reference)
    assert g.temps_net_intervalle.contient(g.temps_net_heures)
    assert g.gain_mensuel_intervalle is not None
    assert g.gain_mensuel_intervalle.bas <= g.gain_mensuel <= g.gain_mensuel_intervalle.haut


def test_l_intervalle_du_cas_de_reference_reproduit_l_annexe_a6(cas_reference) -> None:
    """Annex A.6: net hours in [14.8 - 22.1], monthly gain in [622 - 928]."""
    g = calculer(cas_reference)
    assert abs(g.temps_net_intervalle.bas - Decimal("14.8")) <= Decimal("0.4")
    assert abs(g.temps_net_intervalle.haut - Decimal("22.1")) <= Decimal("0.4")
    assert abs(g.gain_mensuel_intervalle.bas - Decimal("622")) <= Decimal(20)
    assert abs(g.gain_mensuel_intervalle.haut - Decimal("928")) <= Decimal(20)
    assert g.temps_net_intervalle.niveau == Decimal("0.90")


def test_sans_taux_horaire_il_n_y_a_pas_d_intervalle_en_euros(cas_reference) -> None:
    heures_seul, gain = simuler(replace(cas_reference, taux_horaire=None))
    assert heures_seul.bas > 0
    assert gain is None


def test_les_distributions_sont_derivees_de_la_qualite_de_mesure(cas_reference) -> None:
    """D-02 / D-14 - the spread comes from the measurement, not from a guess."""
    d = incertitudes(cas_reference)
    assert d["occurrences"].forme == FormeIncertitude.NORMALE
    assert d["occurrences"].ecart == Decimal("17.1464")  # 42 / sqrt(6)
    assert d["duree_unitaire"].forme == FormeIncertitude.NORMALE
    assert d["duree_unitaire"].ecart < Decimal("0.05")  # 1.8 / sqrt(1840)
    assert d["coefficient_fragmentation"].forme == FormeIncertitude.UNIFORME
    assert d["coefficient_fragmentation"].ecart == Decimal("0.05")
    assert d["part_atypique"].ecart == Decimal("0.02")
    assert d["taux:revue"].ecart == Decimal("0.0500")  # 20 % +/- 25 % (annex A.6)


def test_une_duree_inferree_elargit_l_intervalle(cas_reference) -> None:
    """17.2 - an inferred duration carries a +/-40 % band."""
    inferree = replace(cas_reference, duree_statut=StatutDuree.INFERREE, duree_nb_cas=0)
    d = incertitudes(inferree)
    assert d["duree_unitaire"].forme == FormeIncertitude.UNIFORME
    assert d["duree_unitaire"].ecart == Decimal("3.6000")
    large, _ = simuler(inferree)
    etroite, _ = simuler(cas_reference)
    assert large.largeur > etroite.largeur


def test_le_temps_net_ne_descend_jamais_sous_zero() -> None:
    from gisement.types import (
        ComposanteTransfert,
        CoutAutomatisation,
        OccurrencesMensuelles,
        Repartition,
    )

    ecrase = EntreeGisement(
        processus_id="P-ECRASE",
        occurrences=OccurrencesMensuelles(mediane=Decimal(10), nb_mois=6),
        duree_unitaire_minutes=Decimal(2),
        repartition=Repartition.DIFFUSE,
        part_atypique=Decimal("0.90"),
        transfert=(ComposanteTransfert("supervision", forfait_heures=Decimal(50)),),
        taux_horaire=Decimal(42),
        cout=CoutAutomatisation(jours=Decimal(1)),
    )
    g = calculer(ecrase)
    assert g.temps_net_heures == Decimal(0)
    assert g.temps_net_intervalle.bas == Decimal(0)
    assert g.gain_mensuel == Decimal(0)
    assert g.ecart_naif is None
    assert g.delai_retour_mois is None
