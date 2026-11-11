"""Model interface shared by the classifier (lot 10) and the writer (lot 16).

Two hard rules come from the spec:
  - a model **classifies facts**, it never computes a figure (EF-35);
  - every call is accounted for, in tokens and in dollars (ENF-09, KPI-8).

`ModeleFictif` is the offline implementation used by every test: it answers
deterministically from a table, so the whole pipeline runs in CI without
credentials and without spending a cent (§26.4).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True)
class ReponseModele:
    """What a model call returns: facts, a confidence, and its cost."""

    donnees: dict[str, Any] = field(default_factory=dict)
    confiance: Decimal = Decimal(0)
    citations: tuple[str, ...] = ()
    jetons_entree: int = 0
    jetons_sortie: int = 0
    modele: str = ""
    refus: str = ""
    """Non-empty when the gateway refused the call before the model ran (R5)."""

    @property
    def est_refusee(self) -> bool:
        return bool(self.refus)


@runtime_checkable
class Modele(Protocol):
    """The only way the project talks to a model."""

    nom: str

    def classer(self, invite: str, schema: dict[str, Any]) -> ReponseModele:
        """Return structured facts validated against `schema`."""
        ...

    def rediger(self, invite: str) -> str:
        """Return prose built from figures supplied in the prompt (§21.5)."""
        ...


def estimer_jetons(texte: str) -> int:
    """Deterministic token estimate: four characters per token."""
    return max(1, len(texte) // 4)
