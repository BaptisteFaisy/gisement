"""Lot 0 - the model interface and the configuration files."""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

from gisement.modeles import ModeleFictif, ReponseModele, estimer_jetons
from gisement.types import decimal

RACINE = Path(__file__).resolve().parents[2]
CONFIG = RACINE / "config"

SCHEMA = {
    "type": "object",
    "properties": {
        "motif": {"type": "string"},
        "api_existe": {"type": "boolean"},
        "confiance": {"type": "number"},
    },
    "required": ["motif", "api_existe"],
}


def test_le_modele_fictif_repond_depuis_sa_table():
    modele = ModeleFictif(reponses={"classe cette activite": {"donnees": {}, "confiance": "0.91"}})
    reponse = modele.classer("classe cette activite", SCHEMA)
    assert isinstance(reponse, ReponseModele)
    assert reponse.modele == "fictif"
    assert reponse.jetons_entree > 0


def test_le_modele_fictif_conforme_au_schema():
    modele = ModeleFictif()
    reponse = modele.classer("une invite inconnue", SCHEMA)
    assert set(reponse.donnees) >= {"motif", "api_existe"}
    assert reponse.donnees["api_existe"] is False


def test_le_modele_fictif_est_deterministe_et_compte_ses_jetons():
    """ENF-08 / ENF-09 - same table, same answer, accounted tokens."""
    premier = ModeleFictif(graine=7).classer("meme invite", SCHEMA)
    second = ModeleFictif(graine=7).classer("meme invite", SCHEMA)
    assert premier.donnees == second.donnees
    assert premier.confiance == second.confiance
    modele = ModeleFictif(graine=7)
    modele.classer("meme invite", SCHEMA)
    modele.rediger("redige le cas business")
    entree, sortie = modele.total_jetons()
    assert entree > 0 and sortie > 0
    assert len(modele.appels) == 2


def test_estimer_jetons_est_stable():
    assert estimer_jetons("abcd") == 1
    assert estimer_jetons("a" * 40) == 10


def test_les_trois_fichiers_de_configuration_sont_valides():
    for nom in ("tarifs.json", "campagne.json", "priorite.json"):
        donnees = json.loads((CONFIG / nom).read_text(encoding="utf-8"))
        assert donnees["version"] == "1.0", nom


def test_les_tarifs_reproduisent_l_annexe_g():
    """Annex G.3 - 19.77 $ per mapping, 94 % of it in Transcribe and BDA."""
    tarifs = json.loads((CONFIG / "tarifs.json").read_text(encoding="utf-8"))
    transcribe = decimal(tarifs["transcribe_usd_par_minute"]) * 360
    bda = decimal(tarifs["data_automation_usd_par_page"]) * 200
    inference = (
        Decimal("1.400") * decimal(tarifs["nova_lite_usd_par_million_entree"])
        + Decimal("0.320") * decimal(tarifs["nova_lite_usd_par_million_sortie"])
        + Decimal("0.095") * decimal(tarifs["modele_fort_usd_par_million_entree"])
        + Decimal("0.045") * decimal(tarifs["modele_fort_usd_par_million_sortie"])
    )
    assert round(transcribe, 2) == Decimal("8.64")
    assert round(bda, 2) == Decimal("10.00")
    assert round(inference, 2) == Decimal("1.12")
    total = transcribe + bda + inference
    assert round(total, 2) == Decimal("19.76")
    assert (transcribe + bda) / total > Decimal("0.93")


def test_les_poids_de_priorite_somment_a_un():
    poids = json.loads((CONFIG / "priorite.json").read_text(encoding="utf-8"))["poids"]
    total = sum((decimal(v) for v in poids.values()), Decimal(0))
    assert total == Decimal("1.00")
    assert decimal(poids["gain"]) == Decimal("0.35")


def test_les_plafonds_de_budget_sont_ceux_du_chapitre_26():
    campagne = json.loads((CONFIG / "campagne.json").read_text(encoding="utf-8"))
    assert decimal(campagne["budget"]["cartographie_usd"]) == Decimal("20.00")
    assert campagne["budget"]["cartographies_completes_max"] == 4
    assert campagne["bornes"]["audio_heures_max"] == 6
    assert campagne["bornes"]["documents_pages_max"] == 200
    assert campagne["seuil_agregation"] == 5
