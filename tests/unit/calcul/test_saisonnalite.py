"""R11 / 13.1 correction 4 - the median, never the mean, and the amplitude published."""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

from gisement.calcul import amplitude_publiee, calculer, moyenne, statistiques
from gisement.types import EntreeGisement, OccurrencesMensuelles

SERIE_AVEC_PIC = (Decimal(35), Decimal(38), Decimal(40), Decimal(42), Decimal(310), Decimal(45))


def test_la_mediane_est_utilisee_et_pas_la_moyenne() -> None:
    stats = statistiques(SERIE_AVEC_PIC)
    assert stats.mediane == Decimal("41")
    assert moyenne(list(SERIE_AVEC_PIC)) == Decimal("85.00")
    assert stats.minimum == Decimal(35)
    assert stats.maximum == Decimal(310)
    assert stats.nb_mois == 6


def test_l_amplitude_saisonniere_est_publiee() -> None:
    stats = statistiques(SERIE_AVEC_PIC)
    assert amplitude_publiee(stats) == "[35 - 310]"
    assert stats.amplitude > Decimal(6)


def test_un_mois_de_pointe_ne_gonfle_pas_le_gisement(cas_reference: EntreeGisement) -> None:
    """A peak month and a flat month with the same median give the same deposit."""
    pic = replace(
        cas_reference,
        occurrences=OccurrencesMensuelles(
            serie=SERIE_AVEC_PIC,
            mediane=Decimal(41),
            minimum=Decimal(35),
            maximum=Decimal(310),
            ecart_type=Decimal(42),
            nb_mois=6,
        ),
    )
    lisse = replace(
        cas_reference,
        occurrences=OccurrencesMensuelles(
            serie=(Decimal(41),) * 6,
            mediane=Decimal(41),
            minimum=Decimal(41),
            maximum=Decimal(41),
            ecart_type=Decimal(0),
            nb_mois=6,
        ),
    )
    assert calculer(pic).temps_net_heures == calculer(lisse).temps_net_heures


def test_l_ecart_type_est_un_ecart_type_pas_une_variance() -> None:
    """Regression: ecart_type returned the variance, which squared the Monte-Carlo
    spread and published an absurd interval ([0 - 117] for a 26 h deposit)."""
    from gisement.calcul.occurrences import ecart_type

    serie = [Decimal(x) for x in (270, 295, 310, 330, 355, 380)]
    assert ecart_type(serie) == Decimal("40.21")  # stdev, not 1616.67 (variance)
    stats = statistiques(serie)
    assert stats.ecart_type == Decimal("40.21")
    assert stats.mediane == Decimal("320")


def test_une_serie_vide_ne_casse_rien() -> None:
    stats = statistiques(())
    assert stats.mediane == Decimal(0)
    assert stats.nb_mois == 0
    assert amplitude_publiee(stats) == "[0 - 0]"


def test_le_piege_saisonnier_du_jeu_de_demo() -> None:
    """P-16: 41 per month in median, 310 in December - a mean would say 85."""
    from gisement.calcul import entree_depuis_spec
    from tests.fakes.builders import processus_verite

    spec = next(p for p in processus_verite() if p["id"] == "P-16")
    assert spec["piege"] == "pic_saisonnier"
    g = calculer(entree_depuis_spec(spec))
    occurrences = entree_depuis_spec(spec).occurrences
    assert occurrences.mediane == Decimal("41")
    assert occurrences.maximum == Decimal(310)
    assert moyenne(list(occurrences.serie)) > occurrences.mediane * Decimal(2)
    assert g.temps_net_heures < Decimal(20)
