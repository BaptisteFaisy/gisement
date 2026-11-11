"""Lot 22 - the evaluation harness meets the chapter 27 targets."""

from __future__ import annotations

from decimal import Decimal

from eval.harnais import (
    precision_classification,
    precision_economique,
    rappel_motifs,
)


def test_la_precision_de_classification_depasse_88_pour_cent() -> None:
    taux, accords, total = precision_classification()
    assert total == 200
    assert taux >= Decimal("0.88"), f"{accords}/{total}"


def test_le_rappel_des_motifs_depasse_90_pour_cent() -> None:
    taux, reconnus, total = rappel_motifs()
    assert total >= 20
    assert taux >= Decimal("0.90"), f"{reconnus}/{total}"


def test_le_calcul_economique_est_exact_sur_les_23_cas() -> None:
    """100 % - the engine is deterministic, so the agreement is total."""
    taux, accords, total = precision_economique()
    assert total == 23
    assert accords == 23
    assert taux == Decimal(1)
