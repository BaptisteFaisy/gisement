"""Lot 7 - the calls collector: consent first, diarisation, PII redaction."""

from __future__ import annotations

from pathlib import Path

from gisement.canaux import appels
from gisement.types import Canal, StatutDuree


def test_les_appels_se_transcrivent_en_activites(corpus: Path) -> None:
    assert appels.mesurer_volume(appels.source_fichiers(corpus)) == 600


def test_les_appels_sont_mesures_et_consentis(corpus: Path, parametres) -> None:
    activites, rapport = appels.collecter(appels.source_fichiers(corpus), parametres)
    assert len(activites) == 600
    assert rapport["nb_appels"] == 34
    assert rapport["exclus_sans_consentement"] == 0
    assert rapport["minutes_transcrites"] == 360.0
    assert rapport["piis_occultees"] > 0
    assert all(a.canal == Canal.APPELS for a in activites)
    # a transcript segment is a fragment of a conversation, not the duration of
    # the task it mentions: the unit duration stays inferred (9.3)
    assert all(a.duree_statut == StatutDuree.INFERREE for a in activites)
    assert all(a.duree_mesuree_minutes is None for a in activites)


def test_les_locuteurs_ne_sont_jamais_des_noms(corpus: Path, parametres) -> None:
    """10.4 - diarisation labels speakers, it never names them."""
    import json

    activites, _ = appels.collecter(appels.source_fichiers(corpus), parametres)
    for activite in activites[:300]:
        assert "Marie" not in activite.texte
        assert "@demo.example" not in activite.texte
    for chemin in sorted((corpus / "appels" / "transcriptions").glob("*.json")):
        transcription = json.loads(chemin.read_text(encoding="utf-8"))
        for segment in transcription["segments"]:
            assert segment["locuteur"].startswith("LOC-")


def test_un_enregistrement_sans_consentement_est_refuse(corpus: Path, parametres, tmp_path: Path) -> None:
    """10.4 - no covert recording, ever."""
    import json

    racine = tmp_path / "appels" / "transcriptions"
    racine.mkdir(parents=True)
    (racine / "A-1.json").write_text(
        json.dumps(
            {
                "appel_id": "A-1",
                "langue": "fr-FR",
                "duree_minutes": 10,
                "piis_occultees": 0,
                "segments": [
                    {"debut": 0, "fin": 600, "locuteur": "LOC-1", "texte": "Planifier le rendez-vous"}
                ],
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "appels" / "appels.json").write_text(
        json.dumps(
            [
                {
                    "id": "A-1",
                    "duree_minutes": 10,
                    "horodatage": "2026-06-01T10:00:00",
                    "service": "support",
                    "consentement": False,
                    "type": "appel",
                    "transcription": "appels/transcriptions/A-1.json",
                },
            ]
        ),
        encoding="utf-8",
    )
    activites, rapport = appels.collecter(appels.source_fichiers(tmp_path), parametres)
    assert activites == ()
    assert rapport["exclus_sans_consentement"] == 1


def test_l_adapteur_transcribe_normalise_une_reponse() -> None:
    from gisement.canaux.appels.transcribe import Transcribe

    normalise = Transcribe.normaliser(
        "A-1",
        {
            "LanguageCode": "fr-FR",
            "results": {
                "items": [
                    {
                        "start_time": "0.0",
                        "end_time": "12.4",
                        "speaker_label": "spk_0",
                        "alternatives": [{"transcript": "Relancer le devis"}],
                    },
                ],
                "redactedItems": [{"type": "NAME"}],
            },
        },
    )
    assert normalise["appel_id"] == "A-1"
    assert normalise["segments"][0]["locuteur"] == "spk_0"
    assert normalise["piis_occultees"] == 1
