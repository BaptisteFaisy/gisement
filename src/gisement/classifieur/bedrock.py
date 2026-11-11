"""The real Bedrock + Knowledge Bases adapter (chapter 20.2).

Knowledge Bases carries the motif catalogue and the client procedures; Bedrock
labels a group and drafts the business cases. This adapter is deployed, and no
test ever instantiates it: development and CI run on `ModeleFictif` (26.4).
"""

from __future__ import annotations

import json
from decimal import Decimal
from typing import Any

from gisement.modeles.base import ReponseModele, estimer_jetons
from gisement.serialisation import lire_json
from gisement.types.communs import decimal

MODELE_CLASSIFICATION = "amazon.nova-lite-v1:0"
MODELE_REDACTION = "anthropic.claude-sonnet-4-20250514-v1:0"


class BedrockModele:
    """Bedrock Converse + Knowledge Bases retrieval, behind the `Modele` protocol."""

    nom = "bedrock"

    def __init__(
        self,
        client: Any,
        knowledge_base_id: str = "",
        modele_classification: str = MODELE_CLASSIFICATION,
        modele_redaction: str = MODELE_REDACTION,
    ) -> None:
        self._client = client
        self.knowledge_base_id = knowledge_base_id
        self.modele_classification = modele_classification
        self.modele_redaction = modele_redaction
        self.jetons_entree = 0
        self.jetons_sortie = 0

    def classer(self, invite: str, schema: dict[str, Any]) -> ReponseModele:
        contexte = self.recuperer(invite)
        prompt = f"{contexte}\n\n{invite}\n\nReponds en JSON strict conforme au schema."
        reponse = self._client.converse(
            modelId=self.modele_classification,
            messages=[{"role": "user", "content": [{"text": prompt}]}],
            inferenceConfig={"temperature": 0.0},
        )
        texte = self._texte(reponse)
        self._compter(reponse)
        return ReponseModele(
            donnees=_json(texte),
            confiance=decimal(_json(texte).get("confiance", 0)),
            citations=tuple(_json(texte).get("citations", ())),
            jetons_entree=estimer_jetons(prompt),
            jetons_sortie=estimer_jetons(texte),
            modele=self.modele_classification,
        )

    def rediger(self, invite: str) -> str:
        reponse = self._client.converse(
            modelId=self.modele_redaction,
            messages=[{"role": "user", "content": [{"text": invite}]}],
            inferenceConfig={"temperature": 0.2},
        )
        self._compter(reponse)
        return self._texte(reponse)

    def recuperer(self, invite: str, maximum: int = 5) -> str:
        """Retrieve the catalogue entries and procedures relevant to a group."""
        if not self.knowledge_base_id:
            return ""
        resultat = self._client.retrieve(
            knowledgeBaseId=self.knowledge_base_id,
            retrievalQuery={"text": invite[:1000]},
            retrievalConfiguration={"vectorSearchConfiguration": {"numberOfResults": maximum}},
        )
        return "\n".join(
            f"- {item.get('content', {}).get('text', '')}" for item in resultat.get("results", [])
        )

    @staticmethod
    def _texte(reponse: dict[str, Any]) -> str:
        return reponse["output"]["message"]["content"][0].get("text", "")

    def _compter(self, reponse: dict[str, Any]) -> None:
        usage = reponse.get("usage", {})
        self.jetons_entree += int(usage.get("inputTokens", 0))
        self.jetons_sortie += int(usage.get("outputTokens", 0))


def _json(texte: str) -> dict[str, Any]:
    try:
        return json.loads(texte)
    except json.JSONDecodeError:
        debut = texte.find("{")
        fin = texte.rfind("}")
        if debut >= 0 and fin > debut:
            try:
                return json.loads(texte[debut : fin + 1])
            except json.JSONDecodeError:
                return {}
        return {}


def reponse_depuis_fichier(chemin: str) -> ReponseModele:
    """Read a canned model answer - what the offline tests use."""
    brut = lire_json(chemin)
    return ReponseModele(
        donnees=brut.get("donnees", {}),
        confiance=decimal(brut.get("confiance", 0)),
        citations=tuple(brut.get("citations", ())),
        jetons_entree=int(brut.get("jetons_entree", 0)),
        jetons_sortie=int(brut.get("jetons_sortie", 0)),
        modele=str(brut.get("modele", "fictif")),
    )


def confiance(valeur: Any) -> Decimal:
    return decimal(valeur) if valeur is not None else Decimal(0)
