"""Idea #4 - drift detection: a missed prediction is a signal."""

from __future__ import annotations

from decimal import Decimal

from gisement.suivi.alertes import (
    GRAVITE_CRITIQUE,
    GRAVITE_SURVEILLER,
    detecter,
    resume,
)
from gisement.suivi.base import comparer


def suivi(projet: str, trimestre: str, predit: str, mesure: str):
    return comparer(Decimal(predit), Decimal(mesure), projet, trimestre)


def test_une_prediction_invalide_est_critique() -> None:
    alertes = detecter([suivi("P-1", "2027-T1", "1000", "400")])
    assert alertes[0].gravite == GRAVITE_CRITIQUE
    assert alertes[0].code == "prediction_invalide"
    assert "revu" in alertes[0].message


def test_un_ecart_modere_nomme_le_parametre_fautif() -> None:
    alertes = detecter([suivi("P-2", "2027-T1", "1000", "1300")])
    assert alertes[0].gravite == GRAVITE_SURVEILLER
    assert "Parametre en cause" in alertes[0].message


def test_un_ecart_conforme_ne_produit_rien() -> None:
    assert detecter([suivi("P-3", "2027-T1", "1000", "1050")]) == ()


def test_une_derive_de_volume_est_signalee() -> None:
    alertes = detecter([], volumes_precedents={"P-4": Decimal(100)}, volumes_courants={"P-4": Decimal(145)})
    assert alertes[0].code == "derive_volume"
    assert "hausse de 45" in alertes[0].message


def test_un_gisement_qui_apparait_est_signale() -> None:
    alertes = detecter([], volumes_precedents={"P-5": Decimal(0)}, volumes_courants={"P-5": Decimal(80)})
    assert alertes[0].code == "gisement_apparu"
    assert alertes[0].gravite == GRAVITE_SURVEILLER


def test_les_alertes_sont_triees_par_gravite() -> None:
    alertes = detecter(
        [
            suivi("P-A", "2027-T1", "1000", "1100"),  # modere
            suivi("P-B", "2027-T1", "1000", "100"),  # critique
        ]
    )
    assert alertes[0].gravite == GRAVITE_CRITIQUE
    assert alertes[1].gravite == GRAVITE_SURVEILLER


def test_le_resume_est_lisible() -> None:
    assert "Aucune alerte" in resume(())
    alertes = detecter([suivi("P-B", "2027-T1", "1000", "100")])
    texte = resume(alertes)
    assert "1 alerte(s)" in texte and "critique" in texte and "P-B" in texte
