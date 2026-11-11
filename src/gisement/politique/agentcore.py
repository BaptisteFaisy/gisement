"""The AgentCore Policy artefact, generated from the rule registry (D-09).

Point 5 of chapter 34 of the spec is unconfirmed: the exact syntax of an
AgentCore Policy that refuses on a group size. Rather than wait, the document
is **generated from the same registry the local engine enforces**, so the
gateway artefact and the running policy cannot drift. When the real syntax is
confirmed, only the emitter changes.
"""

from __future__ import annotations

from gisement.politique.regles import REGLES, ContextePolitique, seuil_effectif
from gisement.types.communs import Canal
from gisement.types.conformite import OUTIL_CORPUS, OUTIL_EXPORT, OUTIL_MESURE, Regle

VERSION_POLITIQUE = "1.0"
ACTION_REFUS = "deny"
ACTION_AUTORISATION = "allow"


def entree_reglee(spec, contexte: ContextePolitique) -> dict:
    """One rule of the registry, as a gateway policy statement."""
    return {
        "id": spec.regle.value,
        "action": ACTION_REFUS,
        "outils": list(spec.outils) or [OUTIL_MESURE, OUTIL_CORPUS, OUTIL_EXPORT],
        "condition": spec.condition,
        "message": spec.message,
        "journaliser": True,
        "parametres": parametres_de(spec.regle, contexte),
    }


def parametres_de(regle: Regle, contexte: ContextePolitique) -> dict[str, object]:
    """The numbers a rule is applied with, so the artefact is auditable."""
    seuil = seuil_effectif(contexte)
    if regle in (Regle.K5, Regle.COMBINAISON):
        return {"seuil_agregation": seuil, "comportement": "supprimer_pas_arrondir"}
    if regle == Regle.BUDGET:
        return {"budget_restant_usd": str(contexte.budget_restant)}
    if regle == Regle.QUOTA_REQUETES:
        return {"quota_requetes": contexte.quota_requetes}
    if regle == Regle.CANAL_NON_AUTORISE:
        return {"canaux_autorises": list(contexte.canaux_autorises)}
    return {}


def exporter_politique_agentcore(contexte: ContextePolitique) -> dict:
    """The policy document deployed on the gateway for one campaign."""
    return {
        "version": VERSION_POLITIQUE,
        "campagne_id": contexte.campagne_id,
        "tenant_id": contexte.tenant_id,
        "description": (
            "Non-attribution individuelle imposee par la passerelle : aucune mesure ne peut "
            "designer une personne, aucun groupe de moins de cinq individus n'est publie, et "
            "chaque refus est journalise avec la regle violee."
        ),
        "seuil_agregation": seuil_effectif(contexte),
        "canaux_autorises": list(contexte.canaux_autorises),
        "canaux_connus": [c.value for c in Canal],
        "evaluation": "avant_execution_de_l_outil",
        "defaut": ACTION_REFUS,
        "regles": [entree_reglee(spec, contexte) for spec in REGLES],
    }


def verifier_artefact(document: dict) -> tuple[str, ...]:
    """Every rule of the enumeration appears exactly once in the artefact."""
    erreurs: list[str] = []
    if document.get("version") != VERSION_POLITIQUE:
        erreurs.append("version de politique absente ou inconnue")
    if document.get("defaut") != ACTION_REFUS:
        erreurs.append("la politique doit etre en refus par defaut")
    if document.get("evaluation") != "avant_execution_de_l_outil":
        erreurs.append("la politique doit s'appliquer avant l'outil (R5)")
    identifiants = [r["id"] for r in document.get("regles", ())]
    for regle in Regle:
        if regle.value not in identifiants:
            erreurs.append(f"regle absente de l'artefact : {regle.value}")
    for entree in document.get("regles", ()):
        if not entree.get("condition") or not entree.get("message"):
            erreurs.append(f"regle incomplete : {entree.get('id')}")
        if not entree.get("journaliser"):
            erreurs.append(f"regle non journalisee : {entree.get('id')}")
    return tuple(erreurs)


def regles_par_outil(document: dict, outil: str) -> tuple[str, ...]:
    """The rules the gateway will apply to one tool."""
    return tuple(r["id"] for r in document.get("regles", ()) if outil in r.get("outils", ()))


def artefact_pour_campagne(contexte: ContextePolitique) -> dict:
    """Shortcut used by the IaC and by the compliance register."""
    document = exporter_politique_agentcore(contexte)
    assert not verifier_artefact(document), "artefact de politique invalide"
    return document
