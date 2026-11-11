"""Sanitisation at ingestion: pseudonymise, then drop the sensitive records.

Order matters (R3, R4, ENF-02, ENF-05): the sensitive categories are detected
**first** and the record is dropped, then the surviving record is pseudonymised
before anything else touches it. A collector never sees a raw identity.

    from gisement.assainissement import assainir_lot
    propres, rapport = assainir_lot(enregistrements, Canal.TICKETS, cle=cle)
"""

from __future__ import annotations

from gisement.assainissement.detecteurs import (
    COMPREHEND_PII,
    ComprehendDetecteur,
    DetecteurLexical,
    DetecteurPii,
)
from gisement.assainissement.pseudonymisation import (
    PREFIXE_PSEUDONYME,
    OccurrencePii,
    construire_motif_noms,
    est_pseudonymise,
    groupe_pseudonyme,
    pseudonyme,
    pseudonymiser_texte,
)
from gisement.assainissement.rapport import (
    RapportAssainissement,
    fusionner,
    lignes_registre,
)
from gisement.assainissement.sensibles import (
    CATEGORIES_SENSIBLES,
    detecter_categories,
    filtrer,
    occulter,
    texte_concatene,
)
from gisement.types.communs import Canal

#: Fields whose content is free text and must be pseudonymised.
CHAMPS_TEXTE: tuple[str, ...] = (
    "sujet",
    "description",
    "objet",
    "corps",
    "texte",
    "texte_libre",
    "titre",
    "contenu",
    "commentaire",
    "segments",
)

#: Fields holding a direct identifier. They are replaced, never kept.
CHAMPS_IDENTITE: tuple[str, ...] = (
    "agent",
    "expediteur",
    "destinataires",
    "destinataire",
    "auteur",
    "locuteur",
    "responsable",
    "emetteur",
    "nom_personne",
    "prenom_personne",
)

#: Fields used to build the group label (a collective, never a person).
CHAMPS_GROUPE: tuple[str, ...] = ("service", "site", "equipe", "groupe")

__all__ = [
    "CATEGORIES_SENSIBLES",
    "CHAMPS_GROUPE",
    "CHAMPS_IDENTITE",
    "CHAMPS_TEXTE",
    "COMPREHEND_PII",
    "PREFIXE_PSEUDONYME",
    "ComprehendDetecteur",
    "DetecteurLexical",
    "DetecteurPii",
    "OccurrencePii",
    "RapportAssainissement",
    "assainir",
    "assainir_lot",
    "construire_motif_noms",
    "detecter_categories",
    "est_pseudonymise",
    "filtrer",
    "fusionner",
    "groupe_pseudonyme",
    "lignes_registre",
    "occulter",
    "pseudonyme",
    "pseudonymiser_texte",
    "texte_concatene",
]


def assainir(
    enregistrement: dict,
    canal: Canal,
    *,
    cle: str | bytes,
    sel: str = "",
    noms: tuple[str, ...] = (),
    motif_noms: object | None = None,
) -> tuple[dict | None, tuple[OccurrencePii, ...], tuple[str, ...]]:
    """Sanitise one record.

    Returns `(None, (), categories)` when the record carries a sensitive
    category and must be dropped before storage (EF-12), otherwise the
    sanitised record, the pseudonymised occurrences and an empty tuple.
    """
    brut = _texte_a_inspecter(enregistrement)
    categories = detecter_categories(brut)
    if categories:
        return None, (), categories
    occurrences: list[OccurrencePii] = []
    propre = dict(enregistrement)
    for champ in CHAMPS_IDENTITE:
        if champ in propre:
            propre[champ], trouvees = _pseudonymiser_valeur(propre.pop(champ), cle, sel, noms, motif_noms)
            occurrences.extend(trouvees)
    for champ in CHAMPS_TEXTE:
        if isinstance(propre.get(champ), str):
            propre[champ], trouvees = pseudonymiser_texte(propre[champ], cle, sel, noms, motif_noms)
            occurrences.extend(trouvees)
    propre["groupe_pseudonyme"] = _groupe(propre)
    propre["canal"] = canal.value
    propre.pop("watermark", None)
    return propre, tuple(occurrences), ()


def assainir_lot(
    enregistrements: list[dict] | tuple[dict, ...],
    canal: Canal,
    *,
    cle: str | bytes,
    sel: str = "",
    graine: int = 0,
    noms: tuple[str, ...] = (),
    motif_noms: object | None = None,
) -> tuple[list[dict], RapportAssainissement]:
    """Sanitise a whole channel and produce its report (EF-16, ENF-05)."""
    propres: list[dict] = []
    motifs: dict[str, int] = {}
    categories: set[str] = set()
    pseudonymes = 0
    for enregistrement in enregistrements:
        resultat, occurrences, trouvees = assainir(
            enregistrement, canal, cle=cle, sel=sel, noms=noms, motif_noms=motif_noms
        )
        if resultat is None:
            for categorie in trouvees:
                motifs[categorie] = motifs.get(categorie, 0) + 1
                categories.add(categorie)
            continue
        pseudonymes += len(occurrences)
        propres.append(resultat)
    rapport = RapportAssainissement(
        canal=canal,
        volume_entree=len(enregistrements),
        volume_sortie=len(propres),
        pseudonymes_appliques=pseudonymes,
        categories_sensibles=tuple(sorted(categories)),
        exclus=len(enregistrements) - len(propres),
        motifs_exclusion=motifs,
        graine=graine,
    )
    return propres, rapport


def _texte_a_inspecter(enregistrement: dict) -> str:
    champs = CHAMPS_TEXTE + CHAMPS_IDENTITE
    return texte_concatene(enregistrement, champs)


def _pseudonymiser_valeur(
    valeur: object,
    cle: str | bytes,
    sel: str,
    noms: tuple[str, ...],
    motif_noms: object | None = None,
) -> tuple[object, tuple[OccurrencePii, ...]]:
    if isinstance(valeur, str):
        texte, occurrences = pseudonymiser_texte(valeur, cle, sel, noms, motif_noms)
        if not occurrences:
            return pseudonyme(valeur, cle, sel), (
                OccurrencePii("personne", pseudonyme(valeur, cle, sel), 0, len(valeur)),
            )
        return texte, occurrences
    if isinstance(valeur, (list, tuple)):
        pseudonymes: list[str] = []
        occurrences: list[OccurrencePii] = []
        for element in valeur:
            if isinstance(element, str):
                pseudonymes.append(pseudonyme(element, cle, sel))
                occurrences.append(OccurrencePii("personne", pseudonymes[-1], 0, len(element)))
        return pseudonymes, tuple(occurrences)
    return valeur, ()


def _groupe(enregistrement: dict) -> str:
    existant = enregistrement.get("groupe_pseudonyme") or enregistrement.get("groupe")
    if isinstance(existant, str) and existant:
        return existant
    return groupe_pseudonyme(
        str(enregistrement.get("service", "")),
        str(enregistrement.get("site", "")),
        str(enregistrement.get("equipe", "")),
    )
