"""Loading a request and a context from their JSON form.

The 50 requests of R7 live in `demo/donnees/attendus/non_attribution.json`,
the API receives the same shape over HTTP, and the evaluation harness reads the
same file: one loader, three consumers.
"""

from __future__ import annotations

import json
from pathlib import Path

from gisement.politique.regles import ContextePolitique
from gisement.types.communs import Canal, Role, decimal
from gisement.types.conformite import RequeteMesure

RACINE = Path(__file__).resolve().parents[3]
CHEMIN_NON_ATTRIBUTION = RACINE / "demo" / "donnees" / "attendus" / "non_attribution.json"


def requete_depuis_dict(brut: dict) -> RequeteMesure:
    canal = brut.get("canal")
    taille = brut.get("taille_groupe")
    apres_filtres = brut.get("taille_resultat_apres_filtres")
    return RequeteMesure(
        outil=brut["outil"],
        tenant_id=brut["tenant_id"],
        utilisateur=brut["utilisateur"],
        role=Role(brut["role"]),
        campagne_id=brut["campagne_id"],
        canal=Canal(canal) if canal else None,
        filtres=dict(brut.get("filtres", {})),
        groupements=tuple(brut.get("groupements", ())),
        sortie=tuple(brut.get("sortie", ())),
        citations=bool(brut.get("citations", False)),
        corpus_id=brut.get("corpus_id"),
        taille_groupe=int(taille) if taille is not None else None,
        taille_resultat_apres_filtres=int(apres_filtres) if apres_filtres is not None else None,
        requetes_precedentes=int(brut.get("requetes_precedentes", 0)),
    )


def contexte_depuis_dict(brut: dict) -> ContextePolitique:
    return ContextePolitique(
        campagne_id=brut.get("campagne_id", ""),
        tenant_id=brut["tenant_id"],
        conforme=bool(brut.get("conforme", True)),
        suspendue=bool(brut.get("suspendue", False)),
        seuil=int(brut.get("seuil", 5)),
        canaux_autorises=tuple(brut.get("canaux_autorises", tuple(c.value for c in Canal))),
        budget_restant=decimal(brut.get("budget_restant", "0")),
        requetes_utilisateur=int(brut.get("requetes_utilisateur", 0)),
        quota_requetes=int(brut.get("quota_requetes", 200)),
        corpus_assainis=frozenset(brut.get("corpus_assainis", ())),
    )


def cas_depuis_dict(brut: dict) -> tuple[str, str, RequeteMesure, tuple[str, ...], ContextePolitique]:
    """One case of the harness: id, name, request, expected rules, context."""
    return (
        brut["id"],
        brut["nom"],
        requete_depuis_dict(brut["requete"]),
        tuple(brut["regles_attendues"]),
        contexte_depuis_dict(brut["contexte"]),
    )


def charger_non_attribution(chemin: str | Path | None = None) -> list[dict]:
    """The 50 requests of R7 (blocking)."""
    cible = Path(chemin) if chemin else CHEMIN_NON_ATTRIBUTION
    return json.loads(cible.read_text(encoding="utf-8"))["requetes"]
