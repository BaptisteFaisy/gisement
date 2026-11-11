"""The eight written procedures of the synthetic client (annex F.2).

They are deliberately out of step with the observed practice: the gap between
what is written and what is done is itself a finding (9.1), and PROC-04 is the
trap that R12 checks - it describes a process nobody follows.
"""

from __future__ import annotations

PROCEDURES: dict[str, dict[str, str]] = {
    "PROC-01": {
        "titre": "Traitement des commandes clients",
        "processus": "P-01",
        "declare": (
            "Le client saisit sa commande sur le portail B2B. La commande est reprise "
            "automatiquement dans l'ERP par l'interface EDI. L'administration des ventes "
            "n'intervient qu'en cas d'anomalie signalee par le systeme."
        ),
        "reel": (
            "Une large part des commandes arrive par courriel et est ressaisie dans l'ERP "
            "par l'administration des ventes, puis verifiee par telephone."
        ),
        "divergente": "non",
    },
    "PROC-02": {
        "titre": "Gestion des devis et relances commerciales",
        "processus": "P-02, P-11",
        "declare": (
            "Tout devis est etabli dans le CRM a partir d'un modele. Une relance automatique "
            "est programmee a J+7 puis J+21. Les devis complexes sont transmis au responsable "
            "de compte pour chiffrage."
        ),
        "reel": (
            "La relance automatique est peu utilisee : les devis sont relances manuellement, "
            "et les devis complexes representent une majorite des cas atypiques."
        ),
        "divergente": "oui",
    },
    "PROC-03": {
        "titre": "Rapprochements comptables",
        "processus": "P-03, P-04, P-08, P-09",
        "declare": (
            "Le rapprochement facture / bon de livraison est realise par l'ERP en trois voies. "
            "Les ecarts sont traites dans la file d'exception. Le rapprochement bancaire est "
            "importe chaque matin depuis le fichier de la banque."
        ),
        "reel": (
            "Le rapprochement automatique couvre la majorite des cas ; les ecarts et les avoirs "
            "sont traites a la main, et le releve bancaire est pointe ligne a ligne."
        ),
        "divergente": "non",
    },
    "PROC-04": {
        "titre": "Approvisionnement fournisseurs",
        "processus": "P-07, P-16, P-06, P-20",
        "declare": (
            "Le fournisseur transmet sa commande via le portail EDI, ou il la saisit directement. "
            "La commande est alors integree a l'ERP sans aucune ressaisie. Aucun tableur local "
            "n'est utilise pour le suivi des commandes fournisseurs."
        ),
        "reel": (
            "78 % des commandes arrivent par courriel, sont recopiees dans un tableur de suivi "
            "local, puis ressaisies dans l'ERP. Le portail EDI existe et n'est pas utilise."
        ),
        "divergente": "oui",
    },
    "PROC-05": {
        "titre": "Gestion documentaire et classement",
        "processus": "P-05",
        "declare": (
            "Tout document recu est depose dans la GED par le service destinataire, nomme selon "
            "la convention, et indexe avec ses metadonnees dans la journee."
        ),
        "reel": (
            "Le classement est fait par lots en fin de semaine, une part des documents reste "
            "dans les boites aux lettres individuelles, et l'indexation est partielle."
        ),
        "divergente": "oui",
    },
    "PROC-06": {
        "titre": "Support client et interventions",
        "processus": "P-10, P-12, P-13, P-17, P-21",
        "declare": (
            "Toute demande entre par le centre de services. L'affectation est automatique selon "
            "les competences et la charge. Le technicien prend rendez-vous depuis l'outil de "
            "planification. Un compte rendu est saisi a la cloture."
        ),
        "reel": (
            "Une part importante des demandes arrive par telephone et est ressaisie, "
            "l'affectation est corrigee a la main, et les comptes rendus sont rediges en fin "
            "de journee."
        ),
        "divergente": "oui",
    },
    "PROC-07": {
        "titre": "Reporting et clotures",
        "processus": "P-19, P-22, P-23",
        "declare": (
            "Le reporting mensuel est produit par l'outil decisionnel a partir des donnees de "
            "l'ERP. Le commentaire de gestion est saisi dans le meme outil. La diffusion est "
            "automatique le cinquieme jour ouvrable."
        ),
        "reel": (
            "Le reporting est consolide a la main dans un tableur a partir de plusieurs "
            "extractions, le commentaire est redige dans un traitement de texte, et la diffusion "
            "est faite par courriel."
        ),
        "divergente": "oui",
    },
    "PROC-08": {
        "titre": "Notes de frais, remises et recherche d'information",
        "processus": "P-14, P-15, P-18",
        "declare": (
            "Les notes de frais sont saisies par le salarie dans l'outil dedie, puis validees "
            "par le responsable. Les remises exceptionnelles sont accordees dans le CRM selon "
            "la grille tarifaire, avec signature du responsable de compte."
        ),
        "reel": (
            "Une large part des notes de frais est saisie par l'assistant du service sur papier "
            "puis ressaisie, l'outil dedie existe et n'est pas utilise par tous. La recherche "
            "d'un precedent se fait en interrogeant un collegue."
        ),
        "divergente": "oui",
    },
}

ENTETE = """# {titre}

> {filigrane}
>
> Procédure écrite du client fictif « Demo Distribution SAS ». Ce document fait
> partie du jeu de démonstration : il décrit le processus **déclaré**, que la
> mesure vient comparer au processus **réel** (chapitre 9.1 du cahier des
> charges). L'écart constaté est publié dans le rapport, jamais masqué.

**Référence** : {ref}
**Processus concernés** : {processus}
**Version** : 3.1 du 12 janvier 2024 (non révisée depuis)

## Objet

{declare}

## Modalités

1. Le déclencheur est la réception de la demande dans le système déclaré.
2. Le traitement est réalisé par le service concerné, sans délai maximal fixé.
3. La trace de l'opération est conservée dans l'outil de gestion.
4. Les exceptions sont remontées au responsable de service.

## Note de la mesure

L'observation des cinq canaux sur la fenêtre de six mois montre un fonctionnement
différent de celui décrit ci-dessus. Écart relevé par la mesure : **{divergente}**.

{reel}
"""


def rendre(ref: str, filigrane: str) -> str:
    """The markdown of one written procedure."""
    donnees = PROCEDURES[ref]
    return ENTETE.format(ref=ref, filigrane=filigrane, **donnees)


def refs() -> tuple[str, ...]:
    return tuple(sorted(PROCEDURES))
