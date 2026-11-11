"""Amazon Transcribe: diarised transcripts with native PII redaction (EF-14).

`TranscriptionsFigees` reads the transcripts committed in the demo corpus and is
the only implementation any test uses (rule 1 of 26.4: Transcribe is 44 % of the
cost of a mapping). `Transcribe` is the real adapter, with an injected client.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class Transcripteur(Protocol):
    """Turns a recording into the frozen transcript shape."""

    def transcrire(self, media: dict[str, Any]) -> dict[str, Any]:
        """appel_id, langue, duree_minutes, piis_occultees, segments."""
        ...


class TranscriptionsFigees:
    """Reads the frozen transcripts of the demo corpus."""

    nom = "figee"

    def __init__(self, racine: str | Path) -> None:
        self.racine = Path(racine)

    def transcrire(self, media: dict[str, Any]) -> dict[str, Any]:
        chemin = self.racine / str(media.get("transcription", ""))
        if not chemin.exists():
            return {
                "appel_id": media.get("id", ""),
                "langue": "fr-FR",
                "duree_minutes": 0,
                "piis_occultees": 0,
                "segments": [],
            }
        return json.loads(chemin.read_text(encoding="utf-8"))


class Transcribe:
    """The real Amazon Transcribe adapter. Never instantiated by a test.

    Diarisation is on (`ShowSpeakerLabels`) and native PII redaction is asked
    for (`PiiRedactionType="ALL"`): a name must never reach a corpus (R3).
    """

    nom = "amazon-transcribe"

    def __init__(self, client: Any, langue: str = "fr-FR") -> None:
        self._client = client
        self.langue = langue
        self._cache: dict[str, dict[str, Any]] = {}

    def demarrer(self, media_uri: str, appel_id: str) -> str:
        tache = self._client.start_transcription_job(
            TranscriptionJobName=appel_id,
            LanguageCode=self.langue,
            Media={"MediaFileUri": media_uri},
            Settings={
                "ShowSpeakerLabels": True,
                "MaxSpeakerLabels": 5,
                "PiiRedactionType": "ALL",
                "ChannelIdentification": False,
            },
        )
        return tache["TranscriptionJob"]["TranscriptionJobName"]

    def attendre(self, tache_id: str) -> dict[str, Any]:
        if tache_id in self._cache:
            return self._cache[tache_id]
        etat = self._client.get_transcription_job(TranscriptionJobName=tache_id)
        url = etat["TranscriptionJob"]["Transcript"]["TranscriptFileUri"]
        brut = json.loads(self._client.get_transcript(url))
        resultat = self.normaliser(tache_id, brut)
        self._cache[tache_id] = resultat
        return resultat

    def transcrire(self, media: dict[str, Any]) -> dict[str, Any]:
        return self.attendre(self.demarrer(str(media.get("uri", "")), str(media.get("id", ""))))

    @staticmethod
    def normaliser(appel_id: str, brut: dict[str, Any]) -> dict[str, Any]:
        """Map a Transcribe answer onto the frozen transcript shape."""
        resultats = brut.get("results", {})
        segments = []
        for item in resultats.get("items", []):
            segments.append(
                {
                    "debut": float(item.get("start_time", 0.0)),
                    "fin": float(item.get("end_time", 0.0)),
                    "locuteur": str(item.get("speaker_label", "LOC-1")),
                    "texte": str(item.get("alternatives", [{}])[0].get("transcript", "")),
                }
            )
        duree = max((s["fin"] for s in segments), default=0.0) / 60.0
        return {
            "appel_id": appel_id,
            "langue": brut.get("LanguageCode", "fr-FR"),
            "duree_minutes": round(duree, 2),
            "piis_occultees": len(resultats.get("redactedItems", [])),
            "segments": segments,
        }
