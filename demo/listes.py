"""Fixed lists of the synthetic client (ENF-11: no real personal data).

Everything here is invented. Every generated file carries the watermark, every
email address is in `demo.example`, and no name in these lists belongs to a
real person: they are the product of a deterministic draw over common French
first and last names, combined so that no real individual is designated.
"""

from __future__ import annotations

FILIGRANE = "SYNTHETIQUE - DEMONSTRATION"
DOMAINE = "demo.example"

CLIENT = {
    "nom": "Demo Distribution SAS",
    "secteur": "distribution specialisee B2B",
    "effectif": 120,
    "sites": ["lyon", "villeurbanne"],
    "services": ["approvisionnements", "adv", "comptabilite", "support"],
}

#: Headcount per service: it drives the k >= 5 rule of the demo (chapter 18).
EFFECTIFS_PAR_SERVICE = {"approvisionnements": 22, "adv": 34, "comptabilite": 18, "support": 46}

EQUIPES = ["jour", "soir", "matin"]

PRENOMS = (
    "Marie",
    "Julien",
    "Sofia",
    "Thomas",
    "Nadia",
    "Pierre",
    "Camille",
    "Karim",
    "Elodie",
    "Laurent",
    "Aicha",
    "Nicolas",
    "Sarah",
    "Bruno",
    "Leila",
    "Antoine",
    "Ines",
    "Marc",
    "Chloe",
    "Yanis",
    "Helene",
    "Paul",
    "Fatou",
    "Gregoire",
    "Sandrine",
    "Ali",
    "Manon",
    "Vincent",
    "Nathalie",
    "Olivier",
)

NOMS = (
    "Dupont",
    "Marchand",
    "Benali",
    "Roux",
    "Faure",
    "Lambert",
    "Nguyen",
    "Perrot",
    "Da Silva",
    "Chevalier",
    "Meyer",
    "Barbier",
    "Lemoine",
    "Fontaine",
    "Renaud",
    "Girard",
    "Lopez",
    "Perrin",
    "Moreau",
    "Blanchard",
    "Gauthier",
    "Roche",
    "Colin",
    "Vidal",
    "Lemaire",
    "Noel",
    "Riviere",
    "Aubert",
    "Poirier",
    "Leclerc",
)

#: Supplier and customer companies, all fictitious.
SOCIETES = (
    "DEMO-FR-01",
    "DEMO-FR-02",
    "DEMO-FR-03",
    "DEMO-FR-04",
    "DEMO-FR-05",
    "DEMO-FR-06",
    "DEMO-FR-07",
    "DEMO-FR-08",
    "DEMO-FR-09",
    "DEMO-FR-10",
    "DEMO-FR-11",
    "DEMO-FR-12",
    "DEMO-FR-13",
    "DEMO-FR-14",
    "DEMO-FR-15",
    "DEMO-FR-16",
    "DEMO-FR-17",
    "DEMO-FR-18",
)

PRODUITS = tuple(f"R-{n:03d}" for n in range(1, 61))

SYSTEMES = {
    "erp": "ERP",
    "crm": "CRM",
    "ged": "GED",
    "itsm": "ITSM",
    "messagerie": "Messagerie",
    "excel": "Tableur",
    "compta": "Compta",
    "banque": "Banque",
    "agenda": "Agenda",
    "scanner": "Scanner",
    "formulaire": "Formulaire",
    "word": "Traitement de texte",
    "bi": "BI",
    "rh": "SIRH",
    "planning": "Planning",
    "annuaire": "Annuaire tiers",
    "pdf": "Lecteur PDF",
    "portail": "Portail tiers",
}

DOCUMENTS = (
    ("bon_de_commande", "Bon de commande"),
    ("facture", "Facture fournisseur"),
    ("bon_livraison", "Bon de livraison"),
    ("note_de_frais", "Note de frais"),
    ("releve_bancaire", "Releve bancaire"),
    ("devis", "Devis client"),
    ("avoir", "Avoir fournisseur"),
    ("releve_temperature", "Releve de temperature"),
    ("contrat", "Contrat cadre"),
    ("procedure", "Procedure interne"),
)

#: Out-of-scope subjects: the noise that makes the measurement non trivial.
BRUIT_TICKETS = (
    "Mot de passe oublie",
    "Poste de travail en panne",
    "Ajout d'un utilisateur",
    "Demande de materiel",
    "Acces au reseau",
    "Imprimante en defaut",
    "Question sur la messagerie",
    "Mise a jour logicielle",
    "Telephonie mobile",
    "Droit d'acces au dossier partage",
)

BRUIT_COURRIELS = (
    "Disponibilite reunion de service",
    "Note d'information interne",
    "Menu de la semaine",
    "Travaux dans le batiment",
    "Commande de fournitures",
    "Invitation webinar editeur",
    "Rappel des consignes de securite",
    "Resultats du mois",
    "Conges d'ete",
    "Changement d'horaires",
)

#: Sensitive wordings planted in 100 documents (R8). They use indirect
#: phrasings on purpose: a filter that only catches obvious words leaks.
PLANTES_SENSIBLES = {
    "sante": (
        "suite a mon arret de travail",
        "prolongation de l'arret maladie",
        "hospitalisation prevue",
        "suivi medical en cours",
        "demande d'amenagement pour raison de sante",
        "conge de maternite a venir",
        "traitement medical en cours",
    ),
    "opinion_syndicale": (
        "reunion de section syndicale",
        "cotisation syndicale prelevee",
        "mandat de delegue syndical",
        "tract syndical diffuse",
        "adhesion syndicale renouvelee",
        "permanence syndicale du jeudi",
    ),
    "opinion_politique": (
        "engagement politique du salarie",
        "militant d'un parti politique",
        "campagne electorale interne",
        "opinion politique exprimee",
        "sympathisant d'un mouvement",
    ),
    "religion": (
        "demande d'absence pour fete religieuse",
        "pratique religieuse du salarie",
        "absence pour le careme",
        "demande liee au ramadan",
        "conviction religieuse mentionnee",
    ),
    "vie_sexuelle": (
        "orientation sexuelle mentionnee",
        "situation de vie sexuelle",
        "identite de genre indiquee",
    ),
    "origine_ethnie": (
        "origine presumee du candidat",
        "origine ethnique indiquee",
        "appartenance ethnique",
    ),
    "donnee_genetique": (
        "test genetique realise",
        "analyse genetique demandee",
        "predisposition genetique",
    ),
}

#: The seven sensitive categories, in the canonical order of the filter.
CATEGORIES_SENSIBLES = tuple(PLANTES_SENSIBLES)

#: Texts of the labelled activities of the evaluation harness (spec 27).
TEXTES_PIEGES = (
    "Negocier un contrat cadre avec un fournisseur",
    "Decider d'un investissement en comite",
    "Accueillir un nouveau collegue",
    "Rediger une offre d'emploi",
    "Repondre a un appel d'offres public",
)


def personne(rng) -> str:
    """A fictitious full name."""
    return f"{rng.choice(PRENOMS)} {rng.choice(NOMS)}"


def courriel(nom: str) -> str:
    """A fictitious address in the demo domain."""
    prenom, _, famille = nom.partition(" ")
    accent = str.maketrans("aeiouu", "aeiouu")
    return f"{prenom.lower().translate(accent)}.{famille.lower().replace(' ', '').replace("'", '')}@{DOMAINE}"


def societe(rng) -> str:
    return rng.choice(SOCIETES)


def groupe(service: str, rng) -> str:
    """A collective label such as ADV-JOUR: never a person."""
    abreviations = {
        "approvisionnements": "APPRO",
        "adv": "ADV",
        "comptabilite": "COMPTA",
        "support": "SUPPORT",
    }
    return f"{abreviations.get(service, service.upper()[:5])}-{rng.choice(EQUIPES).upper()}"
