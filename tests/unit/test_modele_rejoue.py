"""`ModeleRejoue` replays recorded answers and invents nothing."""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

from gisement.classifieur.etiquetage import SCHEMA_ETIQUETAGE
from gisement.modeles.rejoue import TEXTE_ABSENT, ModeleRejoue


def _ecrire(table: dict, tmp_path: Path) -> Path:
    chemin = tmp_path / "reponses.json"
    chemin.write_text(json.dumps(table, ensure_ascii=False), encoding="utf-8")
    return chemin


def test_une_reponse_enregistree_est_rejouee_telle_quelle(tmp_path):
    invite = "Etiquette ce groupe :: correction :: jira"
    table = {
        ModeleRejoue.cle(invite): {
            "motif_ref": "VERI-03",
            "confiance": "0.88",
            "citations": ["KAFKA-101"],
            "faits": {"travail_deterministe": True},
            "jetons_entree": 412,
            "jetons_sortie": 37,
        }
    }
    modele = ModeleRejoue(_ecrire(table, tmp_path), modele_reel="amazon.nova-lite-v1:0")

    reponse = modele.classer(invite, SCHEMA_ETIQUETAGE)

    assert reponse.donnees["motif_ref"] == "VERI-03"
    assert reponse.confiance == Decimal("0.88")
    assert reponse.citations == ("KAFKA-101",)
    assert reponse.jetons_entree == 412
    assert reponse.jetons_sortie == 37
    assert reponse.modele == "amazon.nova-lite-v1:0 (rejoue)"
    assert modele.absents == []


def test_une_invite_absente_ne_s_invente_pas(tmp_path):
    modele = ModeleRejoue(_ecrire({}, tmp_path))

    reponse = modele.classer("groupe jamais vu", SCHEMA_ETIQUETAGE)

    assert reponse.confiance == Decimal(0)
    assert modele.absents == [ModeleRejoue.cle("groupe jamais vu")]


def test_un_texte_absent_est_dit_et_non_fabrique(tmp_path):
    modele = ModeleRejoue(_ecrire({}, tmp_path), modele_reel="bedrock")

    assert modele.rediger("Redige le business case") == TEXTE_ABSENT
    assert modele.nom == "bedrock (rejoue)"
