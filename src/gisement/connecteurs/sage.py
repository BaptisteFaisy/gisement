"""ERP export connector: Sage, Cegid, SAP - a CSV is a channel too.

Most French SMEs will not open an API; they will export a CSV. This connector
reads that export, tolerates the header variants each editor invents, and
normalises it into the journal schema. It is the cheapest way to give a client
a real measurement without a single integration project.
"""

from __future__ import annotations

import csv
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from gisement.connecteurs.base import normaliser_journal
from gisement.types.communs import Canal

#: Header variants seen in the wild, mapped onto the frozen schema.
ALIAS = {
    "date": ("date", "Date", "dateoperation", "DateOperation", "horodatage"),
    "operation": ("operation", "Operation", "libelle", "Libelle", "action"),
    "compte": ("compte", "Compte", "account", "entite"),
    "montant": ("montant", "Montant", "amount", "Amount"),
    "utilisateur": ("utilisateur", "Utilisateur", "user", "User"),
    "duree_secondes": ("duree_secondes", "Duration", "duree", "Duree"),
    "service": ("service", "Service", "centre", "Centre"),
}


class SourceSage:
    """Reads one ERP export file."""

    canal = Canal.JOURNAUX

    def __init__(self, chemin: str | Path, delimiteur: str | None = None):
        self.chemin = Path(chemin)
        self.delimiteur = delimiteur

    def lire(self) -> Iterator[dict[str, Any]]:
        if not self.chemin.exists():
            return iter(())
        for ligne in self._lignes():
            yield normaliser_journal(self._renommer(ligne), "sage")

    def _lignes(self) -> Iterator[dict[str, str]]:
        with self.chemin.open(encoding="utf-8-sig", newline="") as fichier:
            lecteur = csv.DictReader(fichier, delimiter=self._delimiteur(fichier))
            for ligne in lecteur:
                yield {cle or "": valeur for cle, valeur in ligne.items() if cle}

    def _delimiteur(self, fichier) -> str:
        if self.delimiteur:
            return self.delimiteur
        fichier.seek(0)
        premiere = fichier.readline()
        fichier.seek(0)
        return ";" if premiere.count(";") > premiere.count(",") else ","

    @staticmethod
    def _renommer(ligne: dict[str, str]) -> dict[str, Any]:
        renomme: dict[str, Any] = {}
        for cible, variantes in ALIAS.items():
            for variante in variantes:
                if variante in ligne and ligne[variante] not in (None, ""):
                    renomme[cible] = ligne[variante]
                    break
        return renomme

    def volume(self) -> int:
        return sum(1 for _ in self.lire())
