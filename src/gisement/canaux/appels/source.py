"""Call source: recordings joined with their transcripts, consent checked.

10.4 and 24.1: only recordings that already exist **and** were consented to are
ingested. A recording without consent is refused at ingestion and counted - it
is never silently dropped, because the count goes into the compliance register.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from gisement.canaux.appels.transcribe import Transcripteur
from gisement.canaux.base import Source
from gisement.types.communs import Canal

SEPARATEUR_GESTE = ";"


def _decaler(horodatage: str, secondes: float) -> str:
    """Timestamp of one exchange: the call start shifted by the segment offset.

    Without it every exchange of a call shares one timestamp and the hourly
    spread of the channel collapses, which is what the fragmentation
    coefficient is read from (13.1).
    """
    from datetime import datetime, timedelta

    try:
        base = datetime.fromisoformat(horodatage)
    except ValueError:
        return horodatage
    return (base + timedelta(seconds=float(secondes))).isoformat()


class SourceAppels(Source):
    """One activity per exchange (segment) of a consented recording."""

    canal = Canal.APPELS

    def __init__(self, racine: str | Path, transcripteur: Transcripteur) -> None:
        self.chemin = Path(racine) / "appels" / "appels.json"
        self.transcripteur = transcripteur
        self.sans_consentement = 0
        self.pii_occultees = 0
        self.minutes = 0.0
        self.nb_appels = 0

    def lire(self) -> Iterator[dict[str, Any]]:
        for appel in self._appels():
            if not appel.get("consentement"):
                self.sans_consentement += 1
                continue
            transcription = self.transcripteur.transcrire(appel)
            self.pii_occultees += int(transcription.get("piis_occultees", 0))
            self.minutes += float(appel.get("duree_minutes", 0))
            self.nb_appels += 1
            yield from self._segments(appel, transcription)

    def _appels(self) -> list[dict[str, Any]]:
        if not self.chemin.exists():
            return []
        return json.loads(self.chemin.read_text(encoding="utf-8"))

    def _segments(self, appel: dict, transcription: dict) -> Iterator[dict[str, Any]]:
        for index, segment in enumerate(transcription.get("segments", []), start=1):
            texte = str(segment.get("texte", ""))
            yield {
                "id": f"{appel['id']}#{index:04d}",
                "horodatage": appel.get("horodatage", ""),
                "service": appel.get("service", ""),
                "site": "",
                "consentement": True,
                "type": appel.get("type", "appel"),
                "sujet": texte.split(SEPARATEUR_GESTE)[0].strip(),
                "description": texte,
                "locuteur": segment.get("locuteur", "LOC-1"),
                "systeme": appel.get("systeme", "appels"),
                "duree_minutes": round(float(segment.get("fin", 0)) - float(segment.get("debut", 0)), 2),
                "atypique": bool(segment.get("atypique", False)),
            }

    def volume(self) -> int:
        return sum(
            len(self.transcripteur.transcrire(a).get("segments", []))
            for a in self._appels()
            if a.get("consentement")
        )
