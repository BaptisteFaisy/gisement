"""Non-attribution policy: the rules are enforced by the gateway, not by a prompt.

    from gisement.politique import evaluer, contexte, JournalAcces

`evaluer()` returns a `Decision` naming every rule the request breaks. A
refusal happens before the tool runs (R5), and it is logged (EF-53).
"""

from __future__ import annotations

from gisement.politique.agentcore import (
    exporter_politique_agentcore,
    regles_par_outil,
    verifier_artefact,
)
from gisement.politique.chargement import (
    cas_depuis_dict,
    charger_non_attribution,
    contexte_depuis_dict,
    requete_depuis_dict,
)
from gisement.politique.journal import (
    CompteurRequetes,
    JournalAcces,
    PreuvePurge,
    contexte_avec_quota,
)
from gisement.politique.passerelle import RefusPolitique, contexte, evaluer, exiger
from gisement.politique.regles import REGLES, ContextePolitique, RegleSpec, regles_violees

__all__ = [
    "REGLES",
    "CompteurRequetes",
    "ContextePolitique",
    "JournalAcces",
    "PreuvePurge",
    "RefusPolitique",
    "RegleSpec",
    "cas_depuis_dict",
    "charger_non_attribution",
    "contexte",
    "contexte_avec_quota",
    "contexte_depuis_dict",
    "evaluer",
    "exiger",
    "exporter_politique_agentcore",
    "regles_par_outil",
    "regles_violees",
    "requete_depuis_dict",
    "verifier_artefact",
]
