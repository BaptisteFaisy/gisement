"""A verifiable certificate that a published measure respected k >= 5.

The point is auditability without disclosure: a works council, a DPO or a judge
can check that a published figure covered enough people, **without** being shown
who they were, nor even how many exactly. The certificate carries the threshold,
the decision and a hash-chained fingerprint; the headcount itself is only
compared, never stored.

Chain: each certificate embeds the fingerprint of the previous one, so removing
or rewriting one breaks the chain - the same property the compliance register
has (chapter 22).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

from gisement.serialisation import empreinte as empreinte_sha
from gisement.types.communs import SEUIL_AGGREGATION_DEFAUT
from gisement.types.conformite import FILTRES_PERSONNE, GROUPEMENTS_INTERDITS, RequeteMesure


@dataclass(frozen=True)
class PreuveNonAttribution:
    """One certificate. It contains no personal data, by construction."""

    campagne_id: str
    mesure_id: str
    seuil: int
    conforme: bool
    regles_appliquees: tuple[str, ...]
    empreinte_requetes: str
    empreinte_precedente: str
    horodatage: str
    empreinte: str
    attestation: str


def empreinte_requetes(requetes: Sequence[RequeteMesure]) -> str:
    """A fingerprint of the requests, never their content."""
    return empreinte_sha([empreinte_sha(r) for r in requetes]) if requetes else ""


def regles_appliquees(requetes: Sequence[RequeteMesure]) -> tuple[str, ...]:
    """Which rules the gateway applied to produce this measure."""
    regles = {"regle_k5"}
    for requete in requetes:
        if any(g in GROUPEMENTS_INTERDITS for g in requete.groupements):
            regles.add("regle_individu")
        if any(c in FILTRES_PERSONNE for c in requete.filtres):
            regles.add("regle_filtre_personne")
    return tuple(sorted(regles))


def _corps(
    campagne_id: str,
    mesure_id: str,
    seuil: int,
    conforme: bool,
    empreinte_req: str,
    precedente: str,
    horodatage: str,
) -> dict:
    """The canonical dict that is hashed: every published field, nothing else."""
    return {
        "campagne": campagne_id,
        "mesure": mesure_id,
        "seuil": seuil,
        "conforme": conforme,
        "empreinte_requetes": empreinte_req,
        "precedente": precedente,
        "horodatage": horodatage,
    }


def _attestation(conforme: bool, seuil: int, empreinte_valeur: str) -> str:
    if conforme:
        return (
            f"Cette mesure porte sur un groupe d'au moins {seuil} individus (seuil verifie, "
            f"taille non publiee) ; aucune attribution individuelle n'est derivable. "
            f"Empreinte de preuve : {empreinte_valeur[:16]}."
        )
    return (
        f"Mesure refusee : le groupe porte sur moins de {seuil} individus. Aucune valeur n'a "
        f"ete publiee. Empreinte de preuve : {empreinte_valeur[:16]}."
    )


def certifier(
    campagne_id: str,
    mesure_id: str,
    taille_groupe: int,
    seuil: int = SEUIL_AGGREGATION_DEFAUT,
    requetes: Sequence[RequeteMesure] = (),
    precedente: str = "",
    horodatage: datetime | None = None,
) -> PreuveNonAttribution:
    """Issue one certificate. `taille_groupe` is compared, never stored."""
    seuil_retenu = max(seuil, SEUIL_AGGREGATION_DEFAUT)
    identifiant = any(g in GROUPEMENTS_INTERDITS for r in requetes for g in r.groupements) or any(
        f in FILTRES_PERSONNE for r in requetes for f in r.filtres
    )
    conforme = taille_groupe >= seuil_retenu and not identifiant
    empreinte_req = empreinte_requetes(requetes)
    instante = (horodatage or datetime.now(UTC)).isoformat()
    empreinte_valeur = empreinte_sha(
        _corps(campagne_id, mesure_id, seuil_retenu, conforme, empreinte_req, precedente, instante)
    )
    return PreuveNonAttribution(
        campagne_id=campagne_id,
        mesure_id=mesure_id,
        seuil=seuil_retenu,
        conforme=conforme,
        regles_appliquees=regles_appliquees(requetes),
        empreinte_requetes=empreinte_req,
        empreinte_precedente=precedente,
        horodatage=instante,
        empreinte=empreinte_valeur,
        attestation=_attestation(conforme, seuil_retenu, empreinte_valeur),
    )


def verifier(preuve: PreuveNonAttribution) -> bool:
    """Recompute the fingerprint from the published fields.

    A tampered certificate - a threshold lowered, a refusal turned into an
    approval, a date moved - does not verify.
    """
    attendu = empreinte_sha(
        _corps(
            preuve.campagne_id,
            preuve.mesure_id,
            preuve.seuil,
            preuve.conforme,
            preuve.empreinte_requetes,
            preuve.empreinte_precedente,
            preuve.horodatage,
        )
    )
    return attendu == preuve.empreinte and preuve.conforme


def verifier_chaine(preuves: Sequence[PreuveNonAttribution]) -> tuple[str, ...]:
    """Check the whole chain: every certificate links to the previous one."""
    erreurs: list[str] = []
    precedente = ""
    for preuve in preuves:
        if preuve.empreinte_precedente != precedente:
            erreurs.append(f"{preuve.mesure_id} : maillon casse")
        if not verifier(preuve):
            erreurs.append(f"{preuve.mesure_id} : empreinte invalide ou mesure non conforme")
        if preuve.seuil < SEUIL_AGGREGATION_DEFAUT:
            erreurs.append(f"{preuve.mesure_id} : seuil inferieur a cinq")
        precedente = preuve.empreinte
    return tuple(erreurs)


def attester_sans_taille(preuve: PreuveNonAttribution) -> str:
    """What a third party may be shown: the attestation, and nothing else."""
    return preuve.attestation
