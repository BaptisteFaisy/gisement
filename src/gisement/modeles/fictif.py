"""Deterministic offline model, used by every test and by the demo smoke run.

It never calls a network. Answers come from a table keyed by the prompt (exact
match first, then a stable hash of the prompt), and a missing answer is built
from the expected schema so a lot under development still gets a usable shape.
Two runs on the same table give the same answer, token counts included.
"""

from __future__ import annotations

import hashlib
import json
from decimal import Decimal
from pathlib import Path
from typing import Any

from gisement.modeles.base import ReponseModele, estimer_jetons
from gisement.serialisation import lire_json

VALEURS_PAR_TYPE: dict[str, Any] = {
    "string": "",
    "boolean": False,
    "integer": 0,
    "number": "0",
    "array": [],
    "object": {},
}


class ModeleFictif:
    """A model that answers from a table. Same table, same answer, same cost."""

    nom = "fictif"

    def __init__(
        self,
        reponses: dict[str, Any] | None = None,
        chemin: str | Path | None = None,
        graine: int = 0,
    ) -> None:
        self.graine = graine
        self._table: dict[str, Any] = dict(reponses or {})
        self.appels: list[dict[str, Any]] = []
        if chemin is not None:
            self.charger(chemin)

    def charger(self, chemin: str | Path) -> None:
        """Load a table of answers from a JSON file of the demo dataset."""
        brut = lire_json(chemin)
        if isinstance(brut, dict):
            self._table.update(brut)

    def classer(self, invite: str, schema: dict[str, Any]) -> ReponseModele:
        reponse = self._reponse_pour(invite)
        donnees = self._conformer(reponse if isinstance(reponse, dict) else {}, schema)
        sortie = json.dumps(donnees, ensure_ascii=False, sort_keys=True)
        confiance = self._confiance(invite, reponse)
        jetons_entree, jetons_sortie = estimer_jetons(invite), estimer_jetons(sortie)
        self._journaliser(invite, sortie, jetons_entree, jetons_sortie)
        citations = tuple(reponse.get("citations", ())) if isinstance(reponse, dict) else ()
        return ReponseModele(
            donnees=donnees,
            confiance=confiance,
            citations=citations,
            jetons_entree=jetons_entree,
            jetons_sortie=jetons_sortie,
            modele=self.nom,
        )

    def rediger(self, invite: str) -> str:
        reponse = self._reponse_pour(invite)
        texte = reponse if isinstance(reponse, str) else str(reponse.get("texte", ""))
        if not texte:
            texte = self._texte_par_defaut(invite)
        self._journaliser(invite, texte, estimer_jetons(invite), estimer_jetons(texte))
        return texte

    # ------------------------------------------------------------------ interne

    def _reponse_pour(self, invite: str) -> Any:
        if invite in self._table:
            return self._table[invite]
        cle = self.cle(invite)
        return self._table.get(cle, {})

    @staticmethod
    def cle(invite: str) -> str:
        """Stable key of a prompt: its SHA-256 truncated to 16 characters."""
        return hashlib.sha256(invite.encode("utf-8")).hexdigest()[:16]

    def _confiance(self, invite: str, reponse: Any) -> Decimal:
        if isinstance(reponse, dict) and "confiance" in reponse:
            return Decimal(str(reponse["confiance"]))
        empreinte = int(hashlib.sha256(f"{self.graine}{invite}".encode()).hexdigest()[:8], 16)
        return Decimal("0.60") + Decimal(empreinte % 40) / Decimal(100)

    @staticmethod
    def _conformer(donnees: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
        """Fill every required field of the schema with the answer or a default."""
        proprietes = schema.get("properties", {})
        requis = schema.get("required", list(proprietes))
        resultat: dict[str, Any] = {}
        for nom in requis:
            attendu = proprietes.get(nom, {})
            if nom in donnees:
                resultat[nom] = donnees[nom]
            else:
                resultat[nom] = VALEURS_PAR_TYPE.get(attendu.get("type", "string"), "")
        for nom, valeur in donnees.items():
            resultat.setdefault(nom, valeur)
        return resultat

    @staticmethod
    def _texte_par_defaut(invite: str) -> str:
        premiere = invite.strip().splitlines()[0] if invite.strip() else ""
        return f"[texte fictif] {premiere[:120]}"

    def _journaliser(self, invite: str, sortie: str, entree: int, sortie_jetons: int) -> None:
        self.appels.append(
            {
                "cle": self.cle(invite),
                "jetons_entree": entree,
                "jetons_sortie": sortie_jetons,
                "longueur_sortie": len(sortie),
            }
        )

    def total_jetons(self) -> tuple[int, int]:
        entree = sum(a["jetons_entree"] for a in self.appels)
        sortie = sum(a["jetons_sortie"] for a in self.appels)
        return entree, sortie
