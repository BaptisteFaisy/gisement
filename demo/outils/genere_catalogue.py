# Build tool, not product code: excluded from the linted product paths.
# Run from the repository root:  python3 demo/outils/genere_catalogue.py
# It rewrites catalogue/motifs/*.json - the 40 automation motifs of annex B.
"""Emit the motif catalogue as data (annex B). Adding a motif needs no code."""
import json
from pathlib import Path

FAMILLES = {
    "ressaisie": "RESS", "rapprochement": "RAPPR", "verification": "VERI", "relance": "RELAN",
    "classement": "CLASS", "reporting": "REPO", "coordination": "COORD", "recherche": "RECH",
}
VERBES = {
    "ressaisie": ["recopier", "saisir", "transcrire"], "rapprochement": ["rapprocher", "verifier"],
    "verification": ["verifier", "consulter"], "relance": ["relancer", "envoyer"],
    "classement": ["classer", "envoyer"], "reporting": ["extraire", "rediger", "envoyer"],
    "coordination": ["planifier", "envoyer", "rediger"], "recherche": ["rechercher", "consulter"],
}
DEFAUT = {"duree": "6", "statut": "inferree", "repartition": "semi_regroupee", "taux_revue": "0.20",
          "duree_revue": "1.5", "atyp": "0.15", "jours_min": "4", "jours_max": "12", "abo": "0"}

# ref, nom, nom_en, description, objets, systemes, modele_texte, canaux, overrides
M = [
 ("ressaisie", "RESS-01", "Courriel vers ERP", "Email into the ERP",
  "Recopier dans l'ERP une commande recue par courriel.", ["commande", "courriel", "fournisseur"],
  ["messagerie", "erp"], "Recopier la commande fournisseur du courriel dans l'ERP",
  ["courriels", "journaux"], {"duree": "9", "statut": "mesuree", "types": ["A", "B"], "jours_min": "3",
                              "jours_max": "15", "abo": "180"}),
 ("ressaisie", "RESS-02", "PDF vers tableur", "PDF into a spreadsheet",
  "Recopier dans un tableur les donnees d'un PDF recu.", ["pdf", "tableur", "facture"],
  ["pdf", "excel"], "Recopier les montants du PDF dans le tableur de suivi",
  ["documents", "courriels"], {"duree": "7", "types": ["B", "D"], "jours_min": "5", "abo": "120"}),
 ("ressaisie", "RESS-03", "Tableur vers application", "Spreadsheet into an application",
  "Saisir dans une application les lignes d'un tableur local.", ["tableur", "application", "ligne"],
  ["excel", "erp"], "Saisir les lignes du tableur dans l'application",
  ["journaux", "documents"], {"duree": "5", "types": ["B", "C"]}),
 ("ressaisie", "RESS-04", "Application vers application", "Application to application",
  "Recopier d'une application metier vers une autre.", ["application", "ecran", "donnees"],
  ["erp", "crm"], "Recopier les donnees d'une application vers l'autre",
  ["journaux"], {"duree": "6", "types": ["B", "C"], "jours_max": "18"}),
 ("ressaisie", "RESS-05", "Papier vers numerique", "Paper into digital",
  "Saisir un document papier recu par courrier.", ["papier", "formulaire", "saisie"],
  ["scanner", "ged"], "Saisir le formulaire papier recu par courrier",
  ["documents"], {"duree": "12", "types": ["B", "D"], "jours_min": "8", "jours_max": "20", "abo": "200"}),
 ("ressaisie", "RESS-06", "Formulaire vers systeme", "Form into the system",
  "Saisir dans le systeme un formulaire deja rempli.", ["formulaire", "note", "frais"],
  ["formulaire", "erp"], "Saisir le formulaire de note de frais dans le systeme",
  ["documents", "tickets"], {"duree": "4", "types": ["A", "B"], "jours_min": "0", "jours_max": "8"}),
 ("ressaisie", "RESS-07", "Copie de donnees entre onglets", "Copying data between tabs",
  "Copier des donnees d'un onglet de tableur a un autre.", ["onglet", "copie", "tableur"],
  ["excel"], "Copier les donnees entre les onglets du tableur",
  ["documents"], {"duree": "3", "repartition": "diffuse", "types": ["B"], "jours_min": "2", "jours_max": "6"}),
 ("rapprochement", "RAPPR-01", "Facture et bon de livraison", "Invoice against delivery note",
  "Rapprocher une facture du bon de livraison correspondant.", ["facture", "livraison", "bon"],
  ["erp", "ged"], "Rapprocher la facture du bon de livraison",
  ["documents", "journaux", "tickets"], {"duree": "7", "statut": "mesuree", "types": ["B"], "jours_min": "6", "jours_max": "15"}),
 ("rapprochement", "RAPPR-02", "Releve bancaire et facture", "Bank statement against invoice",
  "Rapprocher un releve bancaire des factures emises.", ["releve", "bancaire", "facture"],
  ["banque", "erp"], "Rapprocher le releve bancaire de la facture",
  ["documents", "journaux"], {"duree": "6", "repartition": "regroupee", "atyp": "0.08", "types": ["B"], "abo": "90"}),
 ("rapprochement", "RAPPR-03", "Commande et reception", "Order against receipt",
  "Rapprocher une commande de sa reception.", ["commande", "reception", "ecart"],
  ["erp"], "Rapprocher la commande de la reception", ["journaux"], {"duree": "8", "types": ["B"], "jours_max": "14"}),
 ("rapprochement", "RAPPR-04", "Devis et facture", "Quotation against invoice",
  "Rapprocher un devis accepte de la facture emise.", ["devis", "facture", "conformite"],
  ["crm", "erp"], "Rapprocher le devis de la facture", ["journaux", "documents"], {"duree": "5", "types": ["B"], "jours_max": "10"}),
 ("rapprochement", "RAPPR-05", "Planning et pointage", "Schedule against timesheet",
  "Rapprocher le planning prevu du pointage reel.", ["planning", "pointage", "heure"],
  ["rh", "planning"], "Rapprocher le planning du pointage", ["journaux"], {"duree": "10", "types": ["B"], "jours_max": "15"}),
 ("rapprochement", "RAPPR-06", "References croisees entre deux fichiers", "Cross references between two files",
  "Comparer les references croisees de deux fichiers.", ["reference", "fichier", "croisees"],
  ["excel", "erp"], "Verifier les references croisees entre deux fichiers", ["documents"], {"duree": "4", "types": ["B"]}),
 ("verification", "VERI-01", "Conformite d'un document", "Document compliance",
  "Verifier la conformite d'un document aux regles.", ["document", "conformite", "regle"],
  ["ged"], "Verifier la conformite du document", ["documents", "journaux"],
  {"duree": "12", "types": ["B", "D"], "jours_min": "8", "jours_max": "20", "abo": "150", "atyp": "0.18"}),
 ("verification", "VERI-02", "Exhaustivite d'un dossier", "File completeness",
  "Verifier qu'un dossier contient toutes les pieces.", ["dossier", "exhaustivite", "piece"],
  ["ged", "crm"], "Verifier l'exhaustivite du dossier", ["tickets", "documents"], {"duree": "10", "types": ["B", "D"], "jours_max": "18"}),
 ("verification", "VERI-03", "Coherence de montants", "Amount consistency",
  "Verifier la coherence des montants saisis.", ["montant", "coherence", "total"],
  ["erp", "compta"], "Verifier la coherence des montants", ["journaux", "documents", "tickets"],
  {"duree": "4", "types": ["B"], "jours_max": "10"}),
 ("verification", "VERI-04", "Validite d'un tiers", "Third party validity",
  "Verifier la validite d'un tiers avant traitement.", ["tiers", "fournisseur", "validite"],
  ["erp", "annuaire"], "Verifier la validite du tiers", ["tickets", "courriels"], {"duree": "6", "types": ["B"], "abo": "60"}),
 ("verification", "VERI-05", "Application d'une grille tarifaire", "Pricing grid application",
  "Verifier l'application de la grille tarifaire et des remises.", ["grille", "tarif", "remise"],
  ["crm", "erp"], "Verifier l'application de la grille tarifaire", ["tickets", "courriels"],
  {"duree": "12", "types": ["D", "E"], "jours_min": "10", "jours_max": "25", "atyp": "0.45"}),
 ("verification", "VERI-06", "Respect d'un seuil ou d'une regle", "Threshold or rule compliance",
  "Verifier le respect d'un seuil ou d'une regle metier.", ["seuil", "regle", "limite"],
  ["erp"], "Verifier le respect du seuil", ["journaux"], {"duree": "12", "types": ["B"], "jours_min": "3", "jours_max": "8", "atyp": "0.14"}),
 ("relance", "RELAN-01", "Devis sans reponse", "Unanswered quotation",
  "Relancer un client dont le devis est sans reponse.", ["devis", "relance", "reponse"],
  ["crm"], "Relancer le devis sans reponse", ["tickets", "journaux", "courriels"],
  {"duree": "8", "repartition": "regroupee", "atyp": "0.07", "types": ["B"], "abo": "70"}),
 ("relance", "RELAN-02", "Facture echue", "Overdue invoice",
  "Relancer une facture echue non reglee.", ["facture", "echue", "paiement"],
  ["compta"], "Relancer la facture echue", ["journaux", "courriels"],
  {"duree": "5", "repartition": "regroupee", "atyp": "0.10", "types": ["B"], "abo": "80"}),
 ("relance", "RELAN-03", "Dossier incomplet", "Incomplete file",
  "Relancer pour obtenir les pieces manquantes d'un dossier.", ["dossier", "incomplet", "piece"],
  ["ged"], "Relancer le dossier incomplet", ["tickets", "courriels"], {"duree": "6", "types": ["B"]}),
 ("relance", "RELAN-04", "Tache en attente", "Pending task",
  "Relancer une tache en attente chez un tiers.", ["tache", "attente", "suivi"],
  ["itsm"], "Relancer la tache en attente", ["tickets"], {"duree": "3", "types": ["B"], "jours_min": "3", "jours_max": "8"}),
 ("relance", "RELAN-05", "Engagement non tenu", "Unmet commitment",
  "Relancer un prestataire sur un engagement non tenu.", ["engagement", "retard", "prestataire"],
  ["crm"], "Relancer l'engagement non tenu", ["tickets", "appels"], {"duree": "9", "types": ["B", "D"]}),
 ("classement", "CLASS-01", "Nommage de fichiers", "File naming",
  "Renommer un fichier selon la convention.", ["fichier", "nommage", "titre"],
  ["ged"], "Classer et renommer le fichier", ["documents"], {"duree": "2", "repartition": "diffuse", "atyp": "0.05", "types": ["B"], "jours_min": "2", "jours_max": "6"}),
 ("classement", "CLASS-02", "Rangement par dossier", "Filing into folders",
  "Ranger un document dans le bon dossier.", ["dossier", "rangement", "classement"],
  ["ged"], "Ranger le document dans le dossier", ["documents"], {"duree": "2", "repartition": "diffuse", "atyp": "0.05", "types": ["B"], "jours_min": "2", "jours_max": "6"}),
 ("classement", "CLASS-03", "Indexation", "Indexing",
  "Indexer un document avec ses metadonnees.", ["indexation", "document", "metadonnee"],
  ["ged"], "Classer et indexer le document", ["documents", "journaux", "tickets"],
  {"duree": "3", "repartition": "diffuse", "atyp": "0.05", "types": ["B"], "jours_min": "5", "jours_max": "12", "abo": "150"}),
 ("classement", "CLASS-04", "Archivage selon la retention", "Archiving per retention",
  "Archiver un document selon la duree de retention.", ["archiver", "retention", "document"],
  ["ged"], "Archiver le document selon la retention", ["documents"], {"duree": "4", "types": ["B"], "jours_max": "10"}),
 ("reporting", "REPO-01", "Extraction periodique", "Periodic extraction",
  "Extraire les donnees d'une periode depuis les systemes.", ["extraction", "donnees", "periode"],
  ["erp", "bi"], "Extraire les donnees periodiques", ["journaux"], {"duree": "25", "repartition": "regroupee", "atyp": "0.10", "types": ["B"], "jours_min": "3", "jours_max": "8"}),
 ("reporting", "REPO-02", "Mise en forme de tableau de bord", "Dashboard formatting",
  "Mettre en forme le tableau de bord du mois.", ["tableau", "bord", "forme"],
  ["excel", "bi"], "Mettre en forme le tableau de bord", ["documents"], {"duree": "40", "repartition": "regroupee", "types": ["B"], "jours_max": "12", "abo": "300"}),
 ("reporting", "REPO-03", "Consolidation multi-sources", "Multi-source consolidation",
  "Consolider des donnees venant de plusieurs sources.", ["consolider", "sources"],
  ["excel", "erp"], "Consolider les donnees multi-sources", ["journaux", "documents"],
  {"duree": "90", "repartition": "regroupee", "atyp": "0.10", "types": ["B", "D"], "jours_min": "8", "jours_max": "20", "abo": "300"}),
 ("reporting", "REPO-04", "Redaction du commentaire", "Writing the commentary",
  "Rediger le commentaire de gestion du reporting.", ["commentaire", "redaction", "synthese"],
  ["word"], "Rediger le commentaire de gestion", ["documents"], {"duree": "30", "repartition": "regroupee", "types": ["D"], "jours_min": "8", "jours_max": "20", "abo": "200"}),
 ("reporting", "REPO-05", "Diffusion", "Distribution",
  "Envoyer le reporting aux destinataires.", ["diffusion", "envoi", "destinataire"],
  ["messagerie"], "Envoyer le reporting aux destinataires", ["courriels"], {"duree": "5", "repartition": "regroupee", "types": ["B"], "jours_min": "2", "jours_max": "5"}),
 ("coordination", "COORD-01", "Prise de rendez-vous", "Appointment booking",
  "Planifier le rendez-vous d'un technicien.", ["rendez", "agenda", "technicien"],
  ["agenda", "itsm"], "Planifier le rendez-vous du technicien", ["appels", "tickets"],
  {"duree": "6", "repartition": "interruptive", "atyp": "0.09", "types": ["B"], "abo": "110"}),
 ("coordination", "COORD-02", "Transmission d'information entre services", "Passing information between departments",
  "Transmettre une information d'un service a un autre.", ["transmission", "service", "information"],
  ["messagerie"], "Transmettre l'information au service", ["courriels", "tickets", "appels"],
  {"duree": "3", "repartition": "interruptive", "atyp": "0.06", "types": ["A", "B"], "jours_min": "1", "jours_max": "5"}),
 ("coordination", "COORD-03", "Affectation d'une demande", "Assigning a request",
  "Affecter une demande a la bonne equipe.", ["affectation", "demande", "equipe"],
  ["itsm"], "Affecter la demande a l'equipe", ["tickets", "journaux"],
  {"duree": "3", "repartition": "interruptive", "atyp": "0.11", "types": ["B"], "jours_min": "3", "jours_max": "8", "abo": "90"}),
 ("coordination", "COORD-04", "Compte rendu de reunion", "Meeting minutes",
  "Rediger et diffuser le compte rendu d'une reunion.", ["reunion", "compte", "rendu"],
  ["messagerie"], "Rediger le compte rendu de reunion", ["appels", "documents"],
  {"duree": "20", "repartition": "regroupee", "atyp": "0.12", "types": ["B", "D"], "jours_max": "15", "abo": "120"}),
 ("recherche", "RECH-01", "Recherche d'une reference", "Looking up a reference",
  "Rechercher la reference d'un produit ou d'un contrat.", ["reference", "produit", "recherche"],
  ["erp"], "Rechercher la reference produit", ["tickets", "appels"], {"duree": "4", "repartition": "diffuse", "types": ["B", "D"], "abo": "100"}),
 ("recherche", "RECH-02", "Recherche d'un precedent", "Looking up a precedent",
  "Rechercher un precedent dans l'historique des dossiers.", ["precedent", "dossier", "historique"],
  ["ged", "crm"], "Rechercher un precedent dans l'historique", ["tickets", "appels", "documents"],
  {"duree": "15", "repartition": "diffuse", "atyp": "0.25", "types": ["D"], "jours_min": "10", "jours_max": "25", "abo": "350"}),
 ("recherche", "RECH-03", "Recherche d'une procedure applicable", "Looking up the applicable procedure",
  "Rechercher la procedure applicable a un cas.", ["procedure", "regle", "applicable"],
  ["ged"], "Rechercher la procedure applicable", ["tickets", "documents"], {"duree": "10", "repartition": "diffuse", "atyp": "0.30", "types": ["D"], "jours_min": "8", "jours_max": "20", "abo": "200"}),
]

CANAUX_PAR_DEFAUT = {"ressaisie": ["tickets", "journaux"], "rapprochement": ["documents", "journaux"],
                     "verification": ["tickets", "documents"], "relance": ["tickets", "courriels"],
                     "classement": ["documents"], "reporting": ["journaux"],
                     "coordination": ["tickets", "appels"], "recherche": ["tickets"]}

sortie: dict[str, list] = {famille: [] for famille in FAMILLES}
for famille, ref, nom, nom_en, desc, objets, systemes, modele, canaux, sur in M:
    base = {**DEFAUT, **sur}
    sortie[famille].append({
        "ref": ref, "famille": famille, "nom": nom, "nom_en": nom_en, "description": desc,
        "canaux": canaux or CANAUX_PAR_DEFAUT[famille],
        "indices": {"verbes": VERBES[famille], "objets": objets, "systemes": systemes},
        "modele_texte": modele,
        "duree_unitaire_typique_minutes": base["duree"], "duree_statut_defaut": base["statut"],
        "repartition_defaut": base["repartition"], "taux_revue_defaut": base["taux_revue"],
        "duree_revue_minutes": base["duree_revue"], "part_atypique_defaut": base["atyp"],
        "types_envisageables": base.get("types", ["B"]),
        "cout_jours_min": base["jours_min"], "cout_jours_max": base["jours_max"],
        "abonnement_mensuel": base["abo"],
    })

# Typical durations aligned with the reference client (demo/spec-processus.json).
# When a channel carries no timestamp - an email, a document, a call segment -
# the measure falls back on the catalogue's typical duration (9.3), so the two
# must agree, or the published hours of that process would be invented.
DUREES_ALIGNEES = {
    "RESS-01": "9", "RESS-04": "5", "RAPPR-03": "25", "VERI-03": "18", "VERI-04": "25",
    "VERI-05": "22", "VERI-06": "12", "REPO-01": "210", "REPO-03": "960", "RECH-01": "12",
}
#: Same alignment for the typical spread: it is what the measure falls back on
#: when the clock cannot be read (a call, a document, a small sample).
REPARTITIONS_ALIGNEES = {
    "RECH-01": "semi_regroupee", "RECH-02": "semi_regroupee", "RESS-04": "regroupee",
    "VERI-03": "diffuse", "VERI-04": "diffuse", "RAPPR-03": "semi_regroupee",
}
for motifs in sortie.values():
    for motif in motifs:
        if motif["ref"] in DUREES_ALIGNEES:
            motif["duree_unitaire_typique_minutes"] = DUREES_ALIGNEES[motif["ref"]]
        if motif["ref"] in REPARTITIONS_ALIGNEES:
            motif["repartition_defaut"] = REPARTITIONS_ALIGNEES[motif["ref"]]

racine = Path("catalogue/motifs")
racine.mkdir(parents=True, exist_ok=True)
for famille, motifs in sortie.items():
    (racine / f"{famille}.json").write_text(
        json.dumps(motifs, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
total = sum(len(v) for v in sortie.values())
print("motifs ecrits:", total, {f: len(v) for f, v in sortie.items()})
