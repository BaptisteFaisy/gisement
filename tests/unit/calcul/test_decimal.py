"""ENF-13 - every published figure is a Decimal, never a binary float."""

from __future__ import annotations

import dataclasses
from decimal import Decimal

from gisement.calcul import calculer
from gisement.types import DecompositionCout, EntreeGisement, Intervalle, decimal


def champs_numeriques(objet: dataclasses.dataclass) -> list[tuple[str, object]]:
    valeurs: list[tuple[str, object]] = []
    for champ in dataclasses.fields(objet):
        valeur = getattr(objet, champ.name)
        if isinstance(valeur, (Intervalle, DecompositionCout)):
            valeurs.extend(champs_numeriques(valeur))
        elif isinstance(valeur, tuple):
            for item in valeur:
                if isinstance(item, tuple) and len(item) == 2:
                    valeurs.append((f"{champ.name}[1]", item[1]))
        else:
            valeurs.append((champ.name, valeur))
    return valeurs


def test_aucun_flottant_dans_un_gisement(cas_reference: EntreeGisement) -> None:
    g = calculer(cas_reference)
    for nom, valeur in champs_numeriques(g):
        assert not isinstance(valeur, float), f"{nom} est un flottant"
        assert valeur is None or isinstance(valeur, (Decimal, int, str)), nom


def test_les_decimaux_sont_arrondis_avant_publication(cas_reference: EntreeGisement) -> None:
    g = calculer(cas_reference)
    for valeur in (g.temps_brut_heures, g.temps_net_heures, g.delai_retour_mois):
        assert -valeur.as_tuple().exponent == 1
    for valeur in (g.gain_mensuel, g.gain_annuel, g.cout.annee_1, g.gain_trois_ans):
        assert -valeur.as_tuple().exponent == 2


def test_decimal_ne_passe_jamais_par_un_flottant_binaire() -> None:
    assert decimal(0.1) == Decimal("0.1")
    assert decimal(42) == Decimal("42")
    assert decimal("2016.00") == Decimal("2016.00")
    assert Decimal(str(0.1)) * 3 == Decimal("0.3")


def test_le_modele_ne_calcule_rien(cas_reference: EntreeGisement) -> None:
    """EF-35 - the engine has no model in its imports, and needs none."""
    import gisement.calcul.moteur as moteur

    assert not any("bedrock" in n.lower() or "modele" in n.lower() for n in dir(moteur))
