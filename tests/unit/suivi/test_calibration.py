"""Idea #4 - the engine learns from the realised, within bounds."""

from __future__ import annotations

from decimal import Decimal

from gisement.suivi.base import comparer
from gisement.suivi.calibration import BORNES, calibrer, ratio_par_projet


def suivi(projet: str, trimestre: str, predit: str, mesure: str):
    return comparer(Decimal(predit), Decimal(mesure), projet, trimestre)


def test_sans_realise_les_defauts_sont_conserves() -> None:
    calibres = calibrer([])
    assert {c.nom for c in calibres} == {"coefficient_fragmentation", "part_atypique", "taux_revue"}
    for calibre in calibres:
        assert calibre.valeur_calibree == calibre.valeur_par_defaut
        assert calibre.echantillons == 0
        assert "aucun realise" in calibre.commentaire


def test_un_realise_superieur_detend_les_coefficients_trop_prudents() -> None:
    """Systematically 30 % above the prediction: the corrections were too harsh."""
    suivis = [suivi(f"P-{i}", "2027-T1", "1000", "1300") for i in range(4)]
    calibres = {c.nom: c for c in calibrer(suivis)}
    assert calibres["taux_revue"].valeur_calibree < calibres["taux_revue"].valeur_par_defaut
    assert calibres["coefficient_fragmentation"].valeur_calibree > Decimal("0.70")
    assert calibres["part_atypique"].valeur_calibree < Decimal("0.15")
    assert calibres["taux_revue"].echantillons == 4


def test_un_realise_inferieur_durcit_les_coefficients() -> None:
    suivis = [suivi(f"P-{i}", "2027-T1", "1000", "700") for i in range(3)]
    calibres = {c.nom: c for c in calibrer(suivis)}
    assert calibres["taux_revue"].valeur_calibree > calibres["taux_revue"].valeur_par_defaut
    assert calibres["coefficient_fragmentation"].valeur_calibree < Decimal("0.70")


def test_un_ecart_faible_ne_change_rien() -> None:
    """Inside the calibration band, the defaults are left alone."""
    suivis = [suivi("P-1", "2027-T1", "1000", "1050")]
    calibres = {c.nom: c for c in calibrer(suivis)}
    for calibre in calibres.values():
        assert calibre.valeur_calibree == calibre.valeur_par_defaut
        assert "conserve" in calibre.commentaire


def test_un_seul_pas_de_dix_pour_cent_par_trimestre() -> None:
    """Bounded: a coefficient never jumps, whatever the history says."""
    suivis = [suivi("P-1", "2027-T1", "100", "10000")]
    calibres = {c.nom: c for c in calibrer(suivis)}
    assert calibres["taux_revue"].valeur_calibree == Decimal("0.1800")  # 0.20 * 0.9
    assert calibres["coefficient_fragmentation"].valeur_calibree == Decimal("0.7700")


def test_les_coefficients_restent_dans_leurs_bornes() -> None:
    suivis = [suivi("P-1", "2027-T1", "100", "100000")]
    for calibre in calibrer(suivis):
        basse, haute = BORNES[calibre.nom]
        assert basse <= calibre.valeur_calibree <= haute


def test_le_ratio_est_moyenne_par_projet_sur_les_trimestres() -> None:
    suivis = [
        suivi("P-1", "2027-T1", "1000", "1200"),
        suivi("P-1", "2027-T2", "1000", "1400"),
        suivi("P-2", "2027-T1", "500", "250"),
    ]
    ratios = ratio_par_projet(suivis)
    assert ratios["P-1"] == Decimal("1.3000")
    assert ratios["P-2"] == Decimal("0.5000")


def test_la_confiance_est_la_part_des_predictions_conformes() -> None:
    suivis = [
        suivi("P-1", "2027-T1", "1000", "1020"),  # conforme
        suivi("P-2", "2027-T1", "1000", "1600"),  # ecart modere
    ]
    calibres = calibrer(suivis)
    assert calibres[0].confiance == Decimal("0.5000")
