"""JSON helpers shared by every lot.

Two guarantees:
  - a `Decimal` never becomes a float on the way out (ENF-13);
  - the fingerprint of an object is stable across runs and processes
    (ENF-08 - reproducibility: same sample, same seed, same results).
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import hashlib
import json
import types as pytypes
import typing
from decimal import Decimal
from enum import Enum
from pathlib import Path

TYPES_SIMPLE = (str, int, float, bool, type(None))


def vers_json(valeur: object) -> object:
    """Convert any contract object into JSON safe primitives."""
    if isinstance(valeur, bool) or valeur is None:
        return valeur
    if isinstance(valeur, (str, int)):
        return valeur
    if isinstance(valeur, float):
        return str(valeur)
    if isinstance(valeur, Decimal):
        return str(valeur)
    if isinstance(valeur, Enum):
        return vers_json(valeur.value)
    if isinstance(valeur, (dt.datetime, dt.date)):
        return valeur.isoformat()
    if isinstance(valeur, dict):
        return {str(k): vers_json(v) for k, v in valeur.items()}
    if isinstance(valeur, (list, tuple, set)):
        return [vers_json(v) for v in valeur]
    if dataclasses.is_dataclass(valeur) and not isinstance(valeur, type):
        return {f.name: vers_json(getattr(valeur, f.name)) for f in dataclasses.fields(valeur)}
    return str(valeur)


def json_deterministe(valeur: object) -> str:
    """Canonical JSON: sorted keys, no spacing, stable across runs."""
    return json.dumps(vers_json(valeur), sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def empreinte(valeur: object) -> str:
    """SHA-256 of the canonical JSON. Used by the hash chained register."""
    return hashlib.sha256(json_deterministe(valeur).encode("utf-8")).hexdigest()


def _converter(annotation: object) -> object:
    """Build the converter matching a type annotation."""
    if annotation in (None, type(None)) or annotation is typing.Any:
        return lambda v: v
    if isinstance(annotation, type):
        if issubclass(annotation, Enum):
            return lambda v: annotation(v)
        if annotation is Decimal:
            return lambda v: Decimal(str(v))
        if annotation is dt.datetime:
            return lambda v: dt.datetime.fromisoformat(v) if isinstance(v, str) else v
        if annotation is dt.date:
            return lambda v: dt.date.fromisoformat(v) if isinstance(v, str) else v
        return lambda v: v
    origin = typing.get_origin(annotation)
    args = typing.get_args(annotation)
    if origin in (typing.Union, pytypes.UnionType):
        return _convertisseur_union(args)
    if origin in (list, tuple, set):
        inner = _converter(args[0]) if args else (lambda v: v)
        return lambda v: [inner(x) for x in v]
    if origin is dict:
        key_conv = _converter(args[0]) if args else (lambda v: v)
        val_conv = _converter(args[1]) if len(args) > 1 else (lambda v: v)
        return lambda v: {key_conv(k): val_conv(x) for k, x in v.items()}
    return lambda v: v


def _convertisseur_union(args: tuple) -> object:
    """Try each branch of a Union until one accepts the value."""
    convertisseurs = [_converter(a) for a in args if a is not type(None)]

    def converti(valeur: object) -> object:
        if valeur is None:
            return None
        for convertisseur in convertisseurs:
            try:
                return convertisseur(valeur)
            except (TypeError, ValueError):
                continue
        return valeur

    return converti


def depuis_dict(classe: type, donnees: dict) -> object:
    """Rebuild a frozen dataclass from its JSON form."""
    hints = typing.get_type_hints(classe)
    champs = [f.name for f in dataclasses.fields(classe)]
    valeurs: dict = {}
    for nom in champs:
        if nom not in donnees:
            continue
        convertisseur = _converter(hints.get(nom, str))
        brut = donnees[nom]
        if dataclasses.is_dataclass(hints.get(nom)) and isinstance(brut, dict):
            valeurs[nom] = depuis_dict(hints[nom], brut)
        elif isinstance(brut, list) and hints.get(nom) is not None:
            valeurs[nom] = convertisseur(brut)
        else:
            valeurs[nom] = convertisseur(brut)
    return classe(**valeurs)


def ecrire_json(chemin: str | Path, valeur: object) -> Path:
    """Write canonical JSON, creating the parent directories."""
    cible = Path(chemin)
    cible.parent.mkdir(parents=True, exist_ok=True)
    cible.write_text(json.dumps(vers_json(valeur), ensure_ascii=False, indent=2), encoding="utf-8")
    return cible


def lire_json(chemin: str | Path) -> object:
    return json.loads(Path(chemin).read_text(encoding="utf-8"))
