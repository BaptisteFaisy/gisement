# Build tool, not product code: excluded from the linted product paths.
# Run from the repository root:  python3 demo/outils/genere_retours.py
"""Reference cases from three other sectors, for the factor back-test (idea #6).

One reference case is an anecdote; a distribution across sectors is a measured
law. Each case is an engine input in the same shape as demo/spec-processus.json,
and its `attendu` block is computed by the engine itself - the back-test is a
regression net, not an independent audit (the honest reading is written in
demo/retours/lisez-moi.md).
"""
import json
import statistics
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

D = lambda v: Decimal(str(v))
def r2(x): return x.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
def r1(x): return x.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
def r4(x): return x.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
COEF = {"regroupee": D("0.90"), "semi_regroupee": D("0.70"), "diffuse": D("0.45"),
        "interruptive": D("0.85")}
TAUX = D("42")

TRANSFERTS = {
    "aucun": [],
    "leger": [("revue", "0.15", "1.0", None), ("rejets", "0.05", "6", None),
              ("supervision", None, None, "0.5")],
    "standard": [("revue", "0.20", "1.5", None), ("rejets", "0.05", "10", None),
                 ("supervision", None, None, "1.0")],
    "lourd": [("revue", "0.25", "2.0", None), ("rejets", "0.08", "15", None),
              ("supervision", None, None, "2.0")],
}

# secteur, id, nom, service, serie(6), duree, statut, ecart, nb_cas, repartition,
# atypique, nb_atyp, transfert, jours, tjm, abo, maintenance, faits, part_volume, suppression
CAS = [
 ("sante", "S-01", "Saisie des comptes rendus de consultation", "secretariat",
  [180, 190, 200, 205, 215, 195], "14", "mesuree", "3.0", 1180, "semi_regroupee", "0.12", 1180,
  "standard", "14", "620", "180", "0.08", {"api_ou_flux_natif": True, "travail_deterministe": True,
  "interface_stable": True}, "1", False),
 ("sante", "S-02", "Rapprochement des actes factures", "facturation",
  [320, 330, 340, 350, 360, 335], "5", "mesuree", "1.1", 2030, "regroupee", "0.07", 2030,
  "leger", "9", "620", "0", "0.08", {"api_ou_flux_natif": True, "travail_deterministe": True,
  "interface_stable": True}, "1", False),
 ("sante", "S-03", "Classement des dossiers patients", "archives",
  [240, 250, 260, 265, 275, 255], "3", "mesuree", "0.7", 1540, "diffuse", "0.05", 1540,
  "leger", "10", "620", "150", "0.08", {"api_ou_flux_natif": True, "travail_deterministe": True,
  "interface_stable": True}, "1", False),
 ("sante", "S-04", "Relance des impayes de mutuelle", "facturation",
  [85, 90, 95, 98, 102, 92], "9", "mesuree", "2.0", 560, "regroupee", "0.10", 560,
  "standard", "7", "620", "90", "0.08", {"api_ou_flux_natif": True, "travail_deterministe": True,
  "interface_stable": True}, "1", False),
 ("sante", "S-05", "Preparation du reporting d'activite", "direction",
  [4, 4, 4, 4, 4, 4], "240", "inferree", "60", 0, "regroupee", "0.20", 24,
  "leger", "12", "620", "250", "0.08", {"api_ou_flux_natif": True, "travail_deterministe": True,
  "interface_stable": True}, "1", False),
 ("sante", "S-06", "Passage des mutuelles au portail de teleservice", "facturation",
  [85, 88, 90, 92, 95, 89], "8", "mesuree", "1.8", 540, "regroupee", "0.06", 540,
  "aucun", "2", "620", "0", "0", {"etape_supprimable_amont": True, "api_ou_flux_natif": True,
  "interface_stable": True}, "0.85", True),
 ("sante", "S-07", "Verification des avoirs exceptionnels", "facturation",
  [3, 4, 4, 5, 4, 4], "20", "mesuree", "5", 140, "diffuse", "0.20", 140,
  "aucun", "6", "620", "60", "0.08", {"api_ou_flux_natif": True, "travail_deterministe": True,
  "interface_stable": True}, "1", False),
 ("logistique", "L-01", "Saisie des bons de transport", "exploitation",
  [410, 430, 450, 460, 480, 440], "6", "mesuree", "1.4", 2670, "semi_regroupee", "0.09", 2670,
  "standard", "12", "580", "200", "0.08", {"api_ou_flux_natif": True, "travail_deterministe": True,
  "interface_stable": True}, "1", False),
 ("logistique", "L-02", "Rapprochement BL et facture transporteur", "comptabilite",
  [260, 270, 280, 290, 300, 275], "7", "mesuree", "1.6", 1670, "semi_regroupee", "0.13", 1670,
  "standard", "10", "580", "0", "0.08", {"api_ou_flux_natif": True, "travail_deterministe": True,
  "interface_stable": True}, "1", False),
 ("logistique", "L-03", "Suivi des litiges de livraison", "service_client",
  [70, 75, 80, 82, 88, 78], "28", "inferree", "9", 0, "diffuse", "0.38", 190,
  "lourd", "18", "580", "0", "0.08", {"jugement_requis": True}, "1", False),
 ("logistique", "L-04", "Planification des tournees", "exploitation",
  [150, 155, 160, 165, 170, 158], "8", "mesuree", "2.2", 950, "interruptive", "0.11", 950,
  "leger", "9", "580", "120", "0.08", {"api_ou_flux_natif": True, "travail_deterministe": True,
  "interface_stable": True}, "1", False),
 ("logistique", "L-05", "Passage des transporteurs au portail EDI", "exploitation",
  [120, 125, 130, 135, 140, 128], "10", "mesuree", "2.5", 780, "regroupee", "0.06", 780,
  "aucun", "3", "580", "0", "0", {"etape_supprimable_amont": True, "api_ou_flux_natif": True,
  "interface_stable": True}, "0.80", True),
 ("industrie_services", "I-01", "Saisie des releves de compteur", "technique",
  [95, 100, 105, 108, 112, 102], "11", "mesuree", "2.8", 620, "regroupee", "0.08", 620,
  "leger", "8", "700", "0", "0.08", {"travail_deterministe": True, "interface_stable": True},
  "1", False),
 ("industrie_services", "I-02", "Rapprochement des consommations facturees", "facturation",
  [210, 220, 230, 235, 245, 225], "6", "mesuree", "1.5", 1360, "semi_regroupee", "0.10", 1360,
  "standard", "9", "700", "0", "0.08", {"api_ou_flux_natif": True, "travail_deterministe": True,
  "interface_stable": True}, "1", False),
 ("industrie_services", "I-03", "Verification de la conformite reglementaire", "qualite",
  [55, 58, 60, 62, 65, 59], "35", "mesuree", "9", 360, "regroupee", "0.22", 360,
  "lourd", "16", "700", "0", "0.08", {"travail_deterministe": True, "interface_stable": True},
  "1", False),
 ("industrie_services", "I-04", "Relance des devis de maintenance", "commercial",
  [130, 135, 140, 145, 150, 138], "5", "mesuree", "1.2", 840, "regroupee", "0.07", 840,
  "leger", "6", "700", "80", "0.08", {"api_ou_flux_natif": True, "travail_deterministe": True,
  "interface_stable": True}, "1", False),
 ("industrie_services", "I-06", "Passage des releves au teleservice du gestionnaire", "technique",
  [92, 95, 98, 100, 104, 96], "11", "mesuree", "2.6", 580, "regroupee", "0.07", 580,
  "aucun", "3", "700", "0", "0", {"etape_supprimable_amont": True, "travail_deterministe": True,
  "interface_stable": True}, "0.90", True),
 ("industrie_services", "I-07", "Verification des avoirs clients", "facturation",
  [3, 4, 4, 5, 4, 4], "18", "mesuree", "4", 130, "regroupee", "0.18", 130,
  "leger", "5", "700", "0", "0.08", {"api_ou_flux_natif": True, "travail_deterministe": True,
  "interface_stable": True}, "1", False),
 ("industrie_services", "I-05", "Consolidation du reporting mensuel", "direction",
  [2, 2, 2, 2, 2, 2], "600", "inferree", "150", 0, "regroupee", "0.15", 12,
  "leger", "15", "700", "300", "0.08", {"api_ou_flux_natif": True, "travail_deterministe": True,
  "interface_stable": True}, "1", False),
]


def attendu(serie, duree, repartition, atyp, transfert, jours, tjm, abo, maint, part, suppression):
    occ = D(statistics.median([float(x) for x in serie])) * D(part)
    brut = occ * D(duree) / 60
    coef = COEF[repartition]
    frag = brut * coef
    comps = TRANSFERTS[transfert]
    if suppression:
        transf = D(0); inel = D(0)
    else:
        transf = sum((r4(occ * D(t) * D(d) / 60) if t else r4(D(f)) for _, t, d, f in comps), D(0))
        inel = brut * D(atyp)
    net = max(D(0), frag - transf - inel)
    gain = r2(net * TAUX)
    gain_a = r2(gain * 12)
    dev = D(jours) * D(tjm); outil = D(abo) * 12; mt = dev * D(maint)
    annee1 = dev + outil + mt; rec = outil + mt
    delai = r1(annee1 / gain) if gain > 0 else None
    return {
        "temps_brut_heures": str(r1(brut)), "coefficient_fragmentation": str(coef),
        "temps_fragmente_heures": str(r1(frag)), "temps_transfere_heures": str(r1(transf)),
        "temps_ineliminable_heures": str(r1(inel)), "temps_net_heures": str(r1(net)),
        "gain_mensuel": str(gain), "gain_annuel": str(gain_a),
        "gain_naif_mensuel": str(r2(brut * TAUX)),
        "ecart_naif": str(r2(brut * TAUX / gain)) if gain > 0 else None,
        "cout": {"developpement": str(r2(dev)), "outil_annuel": str(r2(outil)),
                 "maintenance_annuelle": str(r2(mt)), "annee_1": str(r2(annee1)),
                 "recurrent": str(r2(rec))},
        "delai_retour_mois": str(delai) if delai is not None else None,
        "gain_trois_ans": str(r2(gain_a * 3 - (annee1 + rec * 2))),
    }


sortie = {}
for (secteur, pid, nom, service, serie, duree, statut, ecart, nb_cas, repart, atyp, nb_atyp,
     transfert, jours, tjm, abo, maint, faits, part, suppression) in CAS:
    entree = {
        "id": pid, "nom": nom, "service": service, "famille_poste": "administratif",
        "motifs": [], "canaux": ["tickets", "journaux"],
        "occurrences": {"serie": [str(x) for x in serie],
                        "mediane": str(statistics.median([float(x) for x in serie])),
                        "minimum": str(min(serie)), "maximum": str(max(serie)),
                        "ecart_type": str(round(statistics.stdev([float(x) for x in serie]), 2)),
                        "nb_mois": len(serie)},
        "duree_unitaire_minutes": duree, "duree_statut": statut,
        "duree_ecart_minutes": ecart, "duree_nb_cas": nb_cas, "repartition": repart,
        "part_atypique": atyp, "part_atypique_nb_cas": nb_atyp,
        "transfert": [{"nom": n, "taux": t, "duree_minutes": d, "forfait_heures": f}
                      for n, t, d, f in TRANSFERTS[transfert]],
        "cout": {"jours": jours, "tjm": tjm, "abonnement_mensuel": abo, "taux_maintenance": maint},
        "faits": faits, "part_volume_traitee": part, "suppression_etape": suppression,
        "attendu": attendu(serie, duree, repart, atyp, transfert, jours, tjm, abo, maint,
                           part, suppression),
    }
    sortie.setdefault(secteur, []).append(entree)

TITRES = {
    "sante": ("Sante - etablissement prive de 400 lits",
              "secretariat, facturation, archives, direction"),
    "logistique": ("Logistique - messagerie B2B de 260 salaries",
                   "exploitation, comptabilite, service client"),
    "industrie_services": ("Industrie de services - concession multi-sites, 180 salaries",
                           "technique, facturation, qualite, commercial, direction"),
}
racine = Path("demo/retours"); racine.mkdir(exist_ok=True)
for secteur, cas in sortie.items():
    titre, services = TITRES[secteur]
    doc = {
        "secteur": secteur, "client": titre, "services": services,
        "taux_horaire_charge": str(TAUX),
        "source": ("cas de reference construits a partir de l'experience MSP ; entierement "
                   "synthetiques, aucune donnee client reelle"),
        "note": ("Chaque cas est une entree du moteur au format de demo/spec-processus.json. "
                 "Le bloc `attendu` est calcule par le moteur lui-moi : ce fichier est un filet "
                 "de non-regression sur la distribution du facteur, pas un audit independant."),
        "nb_cas": len(cas), "cas": cas,
    }
    (racine / f"{secteur}.json").write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n",
                                           encoding="utf-8")
    print(f"{secteur}: {len(cas)} cas")
