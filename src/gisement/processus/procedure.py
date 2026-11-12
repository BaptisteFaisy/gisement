"""The gap between the written procedure and the observed work (EF-25, R12).

Gisement never reads the procedure to describe the process: it reads it last,
to measure the gap - and that gap is often the most useful finding of the whole
mapping (9.1). PROC-04 of the demo says the supplier keys the order into the
EDI portal; the measure says 78 % arrive by email and are re-keyed by hand.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from gisement.types.communs import Canal, arrondi
from gisement.types.mesure import EcartProcedure

#: Share of the volume going through another channel than the declared one,
#: above which the gap is called major.
SEUIL_ECART_MAJEUR = Decimal("0.50")

MOTIF_PORTAIL = re.compile(r"portail|edi|saisit directement|automatiquement|sans aucune ressaisie", re.I)
MOTIF_COURRIEL = re.compile(r"courriel|email|tableur|ressais|manuel", re.I)


@dataclass(frozen=True)
class ProcedureLue:
    """One written procedure, as read by Bedrock Data Automation."""

    ref: str
    texte: str
    declare: str = ""
    reel: str = ""
    divergente: bool = False


def lire_procedure(chemin: str | Path) -> ProcedureLue:
    """Read one procedure file of the corpus."""
    texte = Path(chemin).read_text(encoding="utf-8")
    ref = Path(chemin).stem
    return ProcedureLue(
        ref=ref,
        texte=texte,
        declare=_section(texte, "Objet"),
        reel=_section(texte, "Note de la mesure"),
        divergente="**oui**" in texte.lower() or "mesure : **oui**" in texte.lower(),
    )


def _section(texte: str, titre: str) -> str:
    """The paragraph following a markdown heading."""
    motif = re.compile(rf"^##\s+{re.escape(titre)}\s*$(.*?)(?=^##\s|\Z)", re.M | re.S)
    trouve = motif.search(texte)
    return " ".join(trouve.group(1).split()) if trouve else ""


def comparer_procedure(
    procedure: ProcedureLue,
    canaux_observes: Sequence[Canal],
    part_pratique_divergente: Decimal | None = None,
    part_autre_canal: Decimal | None = None,
) -> EcartProcedure | None:
    """Compare what is written with what the channels show.

    `part_pratique_divergente` is the share of the volume that goes through
    another route than the declared one - published as such, because it is the
    figure a CFO remembers ("78 % of our orders never touch the portal").
    """
    if not procedure.texte:
        return None
    declare_un_canal = MOTIF_PORTAIL.search(procedure.declare) is not None
    observe_autre = bool(Canal.COURRIELS in canaux_observes and MOTIF_COURRIEL.search(procedure.reel))
    part = part_pratique_divergente if part_pratique_divergente is not None else part_autre_canal
    majeur = bool(part is not None and part >= SEUIL_ECART_MAJEUR) or (declare_un_canal and observe_autre)
    if not (majeur or procedure.divergente):
        return None
    return EcartProcedure(
        procedure_ref=procedure.ref,
        declare=procedure.declare or "procedure ecrite",
        observe=procedure.reel or _observe_depuis_canaux(canaux_observes),
        majeur=majeur,
        part_pratique_divergente=arrondi(part or Decimal(0), 2),
        preuve_canaux=tuple(canaux_observes),
    )


def _observe_depuis_canaux(canaux: Sequence[Canal]) -> str:
    return "pratique observee sur les canaux : " + ", ".join(c.value for c in canaux)


def ecarts(
    procedures: Sequence[ProcedureLue],
    par_ref: dict[str, tuple[Sequence[Canal], Decimal | None]],
) -> dict[str, EcartProcedure]:
    """Every gap of a campaign, keyed by procedure reference."""
    resultat: dict[str, EcartProcedure] = {}
    for procedure in procedures:
        canaux, part = par_ref.get(procedure.ref, ((), None))
        ecart = comparer_procedure(procedure, canaux, part)
        if ecart is not None:
            resultat[procedure.ref] = ecart
    return resultat
