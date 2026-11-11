"""The gateway: one entry point, every measure passes through it (R5).

`evaluer()` is what the API calls before running a tool, what the AgentCore
Policy middleware calls in production, and what the 50 requests of R7 are
checked against. It answers with the violated rules, never with a partial
result: a request that would isolate a person is refused *before* the model
runs, not filtered after the fact.
"""

from __future__ import annotations

from decimal import Decimal

from gisement.politique.regles import ContextePolitique, messages, regles_violees, seuil_effectif
from gisement.serialisation import empreinte
from gisement.types.campagne import Campagne
from gisement.types.communs import SEUIL_AGGREGATION_DEFAUT, decimal
from gisement.types.conformite import Decision, RequeteMesure


def contexte(
    campagne: Campagne,
    seuil: int = SEUIL_AGGREGATION_DEFAUT,
    budget_restant: Decimal | None = None,
    requetes_utilisateur: int = 0,
    corpus_assainis: frozenset[str] | str = frozenset(),
) -> ContextePolitique:
    """Build the gateway context from a campaign. Nothing is trusted from text."""
    conformite = campagne.conformite
    if conformite is not None:
        seuil = conformite.seuil_agregation
    if budget_restant is None:
        budget_restant = campagne.cout.budget_restant()
    if isinstance(corpus_assainis, str):
        corpus_assainis = frozenset({corpus_assainis})
    return ContextePolitique(
        campagne_id=campagne.id,
        tenant_id=campagne.tenant_id,
        conforme=campagne.peut_ingerer(),
        suspendue=campagne.est_suspendue(),
        seuil=seuil,
        canaux_autorises=tuple(c.value for c in campagne.perimetre.canaux_autorises),
        budget_restant=decimal(budget_restant),
        requetes_utilisateur=requetes_utilisateur,
        corpus_assainis=frozenset(corpus_assainis),
    )


def evaluer(requete: RequeteMesure, contexte_politique: ContextePolitique) -> Decision:
    """Allow or refuse, naming every rule that was broken."""
    violees = regles_violees(requete, contexte_politique)
    motifs = messages(requete, contexte_politique)
    seuil = seuil_effectif(contexte_politique)
    if violees:
        return Decision(
            autorisee=False,
            regles_violees=violees,
            motif=" ; ".join(motifs),
            empreinte_requete=empreinte(requete),
            seuil_agregation=seuil,
        )
    return Decision(
        autorisee=True,
        regles_violees=(),
        motif="",
        empreinte_requete=empreinte(requete),
        seuil_agregation=seuil,
    )


def autoriser(
    requete: RequeteMesure, contexte_politique: ContextePolitique
) -> tuple[bool, tuple[RequeteMesure, Decision]]:
    """Convenience for the API: the decision and its log entry material."""
    decision = evaluer(requete, contexte_politique)
    return decision.autorisee, (requete, decision)


def exiger(requete: RequeteMesure, contexte_politique: ContextePolitique) -> Decision:
    """Raise on refusal - what a tool calls when it cannot proceed."""
    decision = evaluer(requete, contexte_politique)
    if decision.refusee:
        raise RefusPolitique(decision)
    return decision


class RefusPolitique(Exception):
    """A refusal of the gateway. It carries the rules, so the log is complete."""

    def __init__(self, decision: Decision) -> None:
        self.decision = decision
        regles = ", ".join(r.value for r in decision.regles_violees)
        super().__init__(f"Requete refusee par la passerelle ({regles}) : {decision.motif}")
