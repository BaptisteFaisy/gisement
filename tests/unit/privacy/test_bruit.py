"""Idea #7 - differential privacy on the published aggregates."""

from __future__ import annotations

from decimal import Decimal

import pytest

from gisement.privacy import (
    ParametresDP,
    bruit_agregat,
    bruit_laplace,
    echelle,
    resume_garanties,
    seuil_revelation,
)

ACTIF = ParametresDP(epsilon=Decimal("1.0"), actif=True)
INACTIF = ParametresDP()


def test_sans_dp_l_agregat_reste_exact() -> None:
    """The DP is opt-in: a CFO-facing report keeps exact figures."""
    assert bruit_laplace(INACTIF, Decimal("1234.56"), Decimal(10), graine=1) == Decimal("1234.56")
    assert "Aucune perturbation" in resume_garanties(INACTIF, 10)


def test_avec_dp_la_valeur_bouge_mais_reste_proche() -> None:
    bruitee = bruit_laplace(ACTIF, Decimal("1000"), Decimal(10), graine=7)
    assert bruitee != Decimal("1000")
    assert abs(bruitee - Decimal("1000")) < Decimal("10") / ACTIF.epsilon * 20


def test_le_bruit_est_deterministe_a_graine_fixee() -> None:
    """ENF-08 - two runs give the same noised figure."""
    premier = bruit_laplace(ACTIF, Decimal("500"), Decimal(5), graine=42)
    second = bruit_laplace(ACTIF, Decimal("500"), Decimal(5), graine=42)
    assert premier == second
    assert bruit_laplace(ACTIF, Decimal("500"), Decimal(5), graine=43) != premier


def test_le_bruit_est_centre() -> None:
    """Over many draws the noise averages out: the estimate stays unbiased."""
    valeurs = [bruit_laplace(ACTIF, Decimal("1000"), Decimal(10), graine=graine) for graine in range(400)]
    moyenne = sum(valeurs, Decimal(0)) / Decimal(len(valeurs))
    assert abs(moyenne - Decimal("1000")) < Decimal("3")


def test_l_echelle_est_sensibilite_sur_epsilon() -> None:
    assert echelle(Decimal("10"), Decimal("2")) == Decimal("5")
    with pytest.raises(ValueError):
        echelle(Decimal("10"), Decimal(0))


def test_un_agregat_ne_tire_qu_un_seul_bruit() -> None:
    """One draw per published aggregate, not one per term."""
    valeurs = [Decimal(100), Decimal(200), Decimal(300)]
    premier = bruit_agregat(ACTIF, valeurs, Decimal(10), graine=3)
    second = bruit_agregat(ACTIF, valeurs, Decimal(10), graine=3)
    assert premier == second
    assert abs(premier - Decimal(600)) < Decimal(200)


def test_le_seuil_de_revelation_est_un_sur_n() -> None:
    assert seuil_revelation(200) == Decimal("0.005")
    assert seuil_revelation(0) == Decimal(0)
    assert "1/N" not in resume_garanties(ACTIF, 200)
    assert "epsilon = 1.0" in resume_garanties(ACTIF, 200)
