"""R14 - the coverage is published, never implicit (10.3)."""

from __future__ import annotations

from decimal import Decimal

from gisement.couverture import (
    NON_COUVERT_DEFAUT,
    couverture_globale,
    heures_non_couvertes,
    heures_par_canal,
    ligne_publication,
    non_couvert,
    par_canal_publication,
)
from gisement.types import Canal


def test_la_couverture_du_jeu_de_demo_est_de_62_pour_cent() -> None:
    """The five channels attach 2 504 h to a declared 4 040 h over six months."""
    declare = Decimal("4040")
    couvert = Decimal("2504.1")
    couverture = heures_par_canal({Canal.TICKETS: couvert}, declare)
    assert couverture_globale(couverture) == Decimal("0.6198")
    assert "62 %" in ligne_publication(couverture)
    assert "62%" in ligne_publication(couverture, "en")


def test_la_liste_du_non_couvert_est_publiee() -> None:
    couverture = heures_par_canal({Canal.TICKETS: Decimal("100")}, Decimal("1000"))
    assert non_couvert(couverture) == NON_COUVERT_DEFAUT
    assert "travail de terrain" in ligne_publication(couverture)
    assert non_couvert(couverture, ("autre chose",)) == ("autre chose",)


def test_un_denominateur_nul_ne_divise_pas() -> None:
    couverture = heures_par_canal({Canal.TICKETS: Decimal("100")}, Decimal(0))
    assert couverture_globale(couverture) == Decimal(0)
    assert heures_non_couvertes(couverture) == Decimal(0)


def test_les_heures_non_couvertes_sont_le_complement() -> None:
    couverture = heures_par_canal({Canal.TICKETS: Decimal("620")}, Decimal("1000"))
    assert heures_non_couvertes(couverture) == Decimal("380.0")


def test_une_couverture_par_canal_est_publiee() -> None:
    couverture = heures_par_canal(
        {Canal.TICKETS: Decimal("300"), Canal.JOURNAUX: Decimal("700")}, Decimal("1000")
    )
    lignes = par_canal_publication(couverture)
    assert len(lignes) == 2
    assert lignes[0].startswith("journaux")  # alphabetical, deterministic
    assert lignes[1].startswith("tickets")
    assert couverture.par_canal[Canal.TICKETS] == Decimal("0.3")


def test_la_couverture_ne_depasse_pas_un() -> None:
    couverture = heures_par_canal({Canal.TICKETS: Decimal("2000")}, Decimal("1000"))
    assert couverture_globale(couverture) == Decimal("2")
    assert "200 %" in ligne_publication(couverture)
