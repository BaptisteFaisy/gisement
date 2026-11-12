"""Replay of the answers a **real** model gave, on a real corpus.

`ModeleFictif` invents an answer when its table has none: acceptable offline,
not acceptable on real data. `ModeleRejoue` reads a table of answers recorded
from a real model - Bedrock in production, the answers committed in
`reel/modele/reponses.json` for the public corpus - and invents nothing: a
prompt that is not in the table answers with a zero confidence, so the group
falls to human review (21.2) instead of being silently labelled.

Token counts follow the same rule: the real ones when the recording carries
them, the deterministic estimate (4 characters per token) otherwise.
"""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from typing import Any

from gisement.modeles.base import ReponseModele
from gisement.modeles.fictif import ModeleFictif

#: Published instead of an invented text when the recording has no answer.
TEXTE_ABSENT = "[texte non produit : aucun appel modele enregistre pour cette invite]"


class ModeleRejoue(ModeleFictif):
    """The recorded answers of a real model. Same table, no invention."""

    nom = "rejoue"

    def __init__(
        self,
        chemin: str | Path,
        modele_reel: str = "",
        graine: int = 0,
    ) -> None:
        super().__init__(chemin=chemin, graine=graine)
        self.modele_reel = modele_reel
        self.nom = f"{modele_reel} (rejoue)" if modele_reel else self.nom
        self.absents: list[str] = []

    def classer(self, invite: str, schema: dict[str, Any]) -> ReponseModele:
        reponse = super().classer(invite, schema)
        brut = self._reponse_pour(invite)
        if not isinstance(brut, dict):
            return reponse
        entree = brut.get("jetons_entree")
        sortie = brut.get("jetons_sortie")
        if entree is None and sortie is None:
            return reponse
        return replace(
            reponse,
            jetons_entree=int(entree if entree is not None else reponse.jetons_entree),
            jetons_sortie=int(sortie if sortie is not None else reponse.jetons_sortie),
        )

    def _confiance(self, invite: str, reponse: Any) -> Decimal:
        """A recorded confidence, or zero: never an invented one."""
        if isinstance(reponse, dict) and "confiance" in reponse:
            return Decimal(str(reponse["confiance"]))
        self.absents.append(self.cle(invite))
        return Decimal(0)

    def _texte_par_defaut(self, invite: str) -> str:
        self.absents.append(self.cle(invite))
        return TEXTE_ABSENT
