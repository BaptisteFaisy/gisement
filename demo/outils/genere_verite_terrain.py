# Build tool, not product code: excluded from ruff and from the CI lint paths.
# Run from the repository root:  python3 demo/outils/genere_verite_terrain.py
# It rewrites demo/spec-processus.json (the ground truth of the 23 processes).
"""Build demo/spec-processus.json: the ground truth of the 23 demo processes.

Inputs are declared per process; the expected outputs are computed here by an
independent implementation of annex A, so lot 1 has 23 cross-check cases on top
of the golden reference (spec 27: "30 economic cases computed by hand").
"""
import json, statistics
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

D = lambda v: Decimal(str(v))
def r2(x): return x.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
def r1(x): return x.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)

COEF = {"regroupee": D("0.90"), "semi_regroupee": D("0.70"), "diffuse": D("0.45"), "interruptive": D("0.85")}
TAUX_HORAIRE = D("42")

TRANSFERT = {
    "aucun": [],
    "leger": [("revue", "0.15", "1.0", None), ("rejets", "0.05", "6", None), ("supervision", None, None, "0.5")],
    "standard": [("revue", "0.20", "1.5", None), ("rejets", "0.05", "10", None), ("supervision", None, None, "1.0")],
    "reference": [("revue", "0.20", "1.5", None), ("rejets", "0.05", "12", None), ("supervision", None, None, "3.2")],
    "lourd": [("revue", "0.25", "2.0", None), ("rejets", "0.08", "15", None), ("supervision", None, None, "2.0")],
    "minime": [("revue", "0.05", "0.5", None), ("rejets", "0.02", "3", None), ("supervision", None, None, "0.25")],
}

# Recalibration so the demo portfolio is healthy: 6 advised-against processes
# (26 %, inside the 15-30 % band of KPI-9), the annex E figures reproduced for
# P-03 / P-07 / P-14, and the biggest gain out of wave 1 (R17).
OVERRIDES = {
    "P-02": dict(transfert="standard", repartition="semi_regroupee"),
    "P-03": dict(transfert_override=[("revue", "0.20", "1.5", None), ("rejets", "0.05", "12", None),
                                     ("supervision", None, None, "0.8")]),
    "P-05": dict(transfert="minime", jours="8", abo="120"),
    "P-06": dict(transfert="leger"),
    "P-07": dict(part_volume="0.78125"),
    "P-09": dict(transfert="aucun"),
    "P-10": dict(serie=[110, 115, 118, 120, 122, 128]),
    "P-11": dict(duree="8"),
    "P-14": dict(repartition="semi_regroupee", serie=[170, 175, 178, 180, 182, 185], transfert="aucun"),
    "P-15": dict(serie=[82, 86, 90, 93, 96, 88], repartition="semi_regroupee", atyp="0.25",
                 jours="12", abo="250", transfert="leger"),
    "P-16": dict(duree="25", jours="5", abo="0"),
    "P-17": dict(serie=[300, 310, 320, 325, 335, 315]),
    "P-18": dict(repartition="semi_regroupee"),
}

# id, nom, nom_en, service, motifs, serie mensuelle, duree min, statut duree, ecart duree,
# nb cas, repartition, part atypique, nb cas atyp, transfert, jours, tjm, abonnement,
# maintenance, faits, type arbre, vague, risque, piege, procedure, ecart proc, changements,
# visibilite, canaux, part volume, suppression
P = [
 dict(id="P-01", nom="Saisie des commandes clients recues par courriel", nom_en="Keying customer orders received by email",
      service="adv", motifs=["RESS-01","VERI-03"], serie=[230,245,260,265,280,250], duree="8", statut="mesuree",
      ecart="1.6", nb_cas=1480, repartition="semi_regroupee", atyp="0.12", nb_atyp=1480, transfert="standard",
      jours="10", abo="120", type_arbre="B", vague="vague_2", risque="moyen", procedure="PROC-01", ecart_proc=True,
      visibilite=True, canaux=["courriels","tickets","journaux"], faits=dict(api_ou_flux_natif=True, travail_deterministe=True, interface_stable=True)),
 dict(id="P-02", nom="Reponse aux demandes de devis clients", nom_en="Answering customer requests for quotation",
      service="adv", motifs=["VERI-05","RECH-02"], serie=[55,58,60,62,64,57], duree="22", statut="mesuree",
      ecart="6.5", nb_cas=356, repartition="diffuse", atyp="0.55", nb_atyp=356, transfert="lourd",
      jours="30", abo="450", type_arbre="D", vague="aucune", risque="eleve", procedure="PROC-02", ecart_proc=False,
      visibilite=True, canaux=["courriels","tickets","appels"], faits=dict(jugement_requis=True)),
 dict(id="P-03", nom="Rapprochement factures et bons de livraison", nom_en="Matching invoices with delivery notes",
      service="comptabilite", motifs=["RAPPR-01","VERI-03"], serie=[195,205,210,215,225,200], duree="7", statut="mesuree",
      ecart="1.4", nb_cas=1250, repartition="semi_regroupee", atyp="0.15", nb_atyp=1250, transfert="standard",
      jours="9", abo="0", type_arbre="B", vague="vague_1", risque="faible", procedure="PROC-03", ecart_proc=False,
      visibilite=True, canaux=["documents","journaux","tickets"],
      faits=dict(api_ou_flux_natif=True, travail_deterministe=True, interface_stable=True),
      transfert_override=[("revue","0.20","1.5",None),("rejets","0.05","12",None),("supervision",None,None,"0.9")]),
 dict(id="P-04", nom="Rapprochement releves bancaires et factures", nom_en="Matching bank statements with invoices",
      service="comptabilite", motifs=["RAPPR-02"], serie=[85,88,90,92,95,86], duree="6", statut="mesuree",
      ecart="1.2", nb_cas=540, repartition="regroupee", atyp="0.08", nb_atyp=540, transfert="leger",
      jours="8", abo="90", type_arbre="B", vague="vague_2", risque="faible", procedure="PROC-03", ecart_proc=False,
      visibilite=False, canaux=["documents","journaux"],
      faits=dict(api_ou_flux_natif=True, travail_deterministe=True, interface_stable=True)),
 dict(id="P-05", nom="Classement et indexation des documents", nom_en="Filing and indexing documents",
      service="adv", motifs=["CLASS-03","CLASS-01"], serie=[390,405,420,430,450,400], duree="3", statut="mesuree",
      ecart="0.8", nb_cas=2480, repartition="diffuse", atyp="0.05", nb_atyp=2480, transfert="leger",
      jours="11", abo="150", type_arbre="B", vague="vague_2", risque="faible", procedure="PROC-05", ecart_proc=True,
      visibilite=False, canaux=["documents","journaux","tickets"],
      faits=dict(api_ou_flux_natif=True, travail_deterministe=True, interface_stable=True)),
 dict(id="P-06", nom="Traitement des litiges fournisseurs", nom_en="Handling supplier disputes",
      service="approvisionnements", motifs=["VERI-04","RECH-02"], serie=[30,32,35,36,38,33], duree="25", statut="inferree",
      ecart="9", nb_cas=0, repartition="diffuse", atyp="0.35", nb_atyp=120, transfert="standard",
      jours="18", abo="200", type_arbre="D", vague="aucune", risque="eleve", procedure="PROC-06", ecart_proc=True,
      changements=3, visibilite=False, canaux=["courriels","tickets","appels"], faits=dict(jugement_requis=True)),
 dict(id="P-07", nom="Saisie des commandes fournisseurs recues par courriel", nom_en="Keying supplier orders received by email",
      service="approvisionnements", motifs=["RESS-01","VERI-03"], serie=[270,295,310,330,355,380], duree="9", statut="mesuree",
      ecart="1.8", nb_cas=1840, repartition="semi_regroupee", atyp="0.15", nb_atyp=1840, transfert="reference",
      jours="3", abo="0", maintenance="0", type_arbre="A", vague="vague_1", risque="faible", piege="procedure_divergente",
      procedure="PROC-04", ecart_proc=True, visibilite=True, canaux=["courriels","tickets","journaux"],
      faits=dict(etape_supprimable_amont=True, api_ou_flux_natif=True, travail_deterministe=True, interface_stable=True),
      part_volume="0.78", suppression=True, amplitude=[210,465], ecart_type="42",
      variante_b=dict(jours="12", abo="180", maintenance="0.08", part_volume="0.22", suppression=False, transfert="reference")),
 dict(id="P-08", nom="Relance des factures echues", nom_en="Chasing overdue invoices",
      service="comptabilite", motifs=["RELAN-02"], serie=[120,125,130,135,140,128], duree="5", statut="mesuree",
      ecart="1.1", nb_cas=770, repartition="regroupee", atyp="0.10", nb_atyp=770, transfert="leger",
      jours="7", abo="80", type_arbre="B", vague="vague_2", risque="faible", procedure="PROC-07", ecart_proc=False,
      visibilite=True, canaux=["journaux","courriels"],
      faits=dict(api_ou_flux_natif=True, travail_deterministe=True, interface_stable=True)),
 dict(id="P-09", nom="Verification des avoirs fournisseurs", nom_en="Checking supplier credit notes",
      service="comptabilite", motifs=["VERI-03"], serie=[3,4,4,5,4,4], duree="18", statut="mesuree",
      ecart="4", nb_cas=140, repartition="diffuse", atyp="0.20", nb_atyp=140, transfert="leger",
      jours="6", abo="60", type_arbre="B", vague="aucune", risque="faible", procedure="PROC-08", ecart_proc=False,
      visibilite=False, canaux=["documents","tickets"],
      faits=dict(api_ou_flux_natif=True, travail_deterministe=True, interface_stable=True)),
 dict(id="P-10", nom="Controle de conformite des fiches produits", nom_en="Compliance check of product sheets",
      service="adv", motifs=["VERI-01","VERI-06"], serie=[70,72,75,78,80,73], duree="12", statut="mesuree",
      ecart="3", nb_cas=440, repartition="semi_regroupee", atyp="0.18", nb_atyp=440, transfert="standard",
      jours="16", abo="0", type_arbre="C", vague="vague_2", risque="moyen", procedure="PROC-09", ecart_proc=False,
      visibilite=False, canaux=["documents","journaux"], faits=dict(travail_deterministe=True, interface_stable=True)),
 dict(id="P-11", nom="Relance des devis sans reponse", nom_en="Following up unanswered quotations",
      service="adv", motifs=["RELAN-01"], serie=[88,92,95,98,102,93], duree="4", statut="mesuree",
      ecart="0.9", nb_cas=560, repartition="regroupee", atyp="0.07", nb_atyp=560, transfert="leger",
      jours="6", abo="70", type_arbre="B", vague="vague_2", risque="faible", procedure="PROC-02", ecart_proc=True,
      visibilite=True, canaux=["tickets","journaux","courriels"],
      faits=dict(api_ou_flux_natif=True, travail_deterministe=True, interface_stable=True)),
 dict(id="P-12", nom="Prise de rendez-vous des techniciens", nom_en="Booking technician appointments",
      service="support", motifs=["COORD-01"], serie=[140,145,150,155,160,148], duree="6", statut="mesuree",
      ecart="1.5", nb_cas=890, repartition="interruptive", atyp="0.09", nb_atyp=890, transfert="leger",
      jours="8", abo="110", type_arbre="B", vague="vague_2", risque="faible", procedure="PROC-10", ecart_proc=False,
      visibilite=True, canaux=["appels","tickets"],
      faits=dict(api_ou_flux_natif=True, travail_deterministe=True, interface_stable=True)),
 dict(id="P-13", nom="Transmission des informations entre services", nom_en="Passing information between departments",
      service="support", motifs=["COORD-02"], serie=[350,365,380,390,400,370], duree="3", statut="inferree",
      ecart="1.2", nb_cas=0, repartition="interruptive", atyp="0.06", nb_atyp=1200, transfert="leger",
      jours="4", abo="0", type_arbre="A", vague="vague_2", risque="faible", procedure="PROC-11", ecart_proc=True,
      visibilite=False, canaux=["courriels","tickets","appels"], faits=dict(etape_supprimable_amont=True),
      part_volume="0.60", suppression=True),
 dict(id="P-14", nom="Saisie des notes de frais", nom_en="Keying expense claims",
      service="comptabilite", motifs=["RESS-06"], serie=[165,172,180,185,192,175], duree="4", statut="mesuree",
      ecart="1.0", nb_cas=1060, repartition="diffuse", atyp="0.10", nb_atyp=1060, transfert="aucun",
      jours="0", abo="0", maintenance="0", type_arbre="A", vague="vague_1", risque="faible", procedure="PROC-12",
      ecart_proc=True, visibilite=True, canaux=["documents","tickets"], faits=dict(etape_supprimable_amont=True),
      part_volume="0.73", suppression=True),
 dict(id="P-15", nom="Recherche de precedents et de procedures applicables", nom_en="Searching precedents and applicable procedures",
      service="support", motifs=["RECH-02","RECH-03"], serie=[55,58,60,62,65,59], duree="15", statut="inferree",
      ecart="5", nb_cas=0, repartition="diffuse", atyp="0.30", nb_atyp=200, transfert="leger",
      jours="20", abo="350", type_arbre="D", vague="vague_3", risque="moyen", procedure="PROC-13", ecart_proc=False,
      visibilite=False, canaux=["tickets","appels","documents"], faits=dict(jugement_requis=True)),
 dict(id="P-16", nom="Traitement du reassort de fin d annee", nom_en="Handling the year-end replenishment",
      service="approvisionnements", motifs=["RESS-01","VERI-06"], serie=[35,38,40,42,310,45], duree="10", statut="mesuree",
      ecart="2.2", nb_cas=480, repartition="semi_regroupee", atyp="0.14", nb_atyp=480, transfert="standard",
      jours="9", abo="100", type_arbre="B", vague="vague_2", risque="moyen", piege="pic_saisonnier",
      procedure="PROC-04", ecart_proc=False, visibilite=True, canaux=["courriels","journaux"],
      faits=dict(api_ou_flux_natif=True, travail_deterministe=True, interface_stable=True)),
 dict(id="P-17", nom="Affectation des demandes d intervention", nom_en="Assigning intervention requests",
      service="support", motifs=["COORD-03"], serie=[195,205,210,215,225,200], duree="3", statut="mesuree",
      ecart="0.7", nb_cas=1230, repartition="interruptive", atyp="0.11", nb_atyp=1230, transfert="leger",
      jours="7", abo="90", type_arbre="B", vague="vague_2", risque="faible", procedure="PROC-10", ecart_proc=False,
      visibilite=True, canaux=["tickets","journaux"],
      faits=dict(api_ou_flux_natif=True, travail_deterministe=True, interface_stable=True)),
 dict(id="P-18", nom="Validation des remises exceptionnelles", nom_en="Approving exceptional discounts",
      service="adv", motifs=["VERI-05","VERI-06"], serie=[22,24,25,26,28,23], duree="12", statut="mesuree",
      ecart="3", nb_cas=290, repartition="diffuse", atyp="0.45", nb_atyp=290, transfert="aucun",
      jours="12", abo="0", type_arbre="D", vague="aucune", risque="eleve", procedure="PROC-14", ecart_proc=False,
      visibilite=False, canaux=["courriels","tickets"],
      faits=dict(jugement_requis=True, obligation_legale_humaine=True)),
 dict(id="P-19", nom="Preparation du reporting mensuel de gestion", nom_en="Preparing the monthly management reporting",
      service="comptabilite", motifs=["REPO-01","REPO-03","REPO-04"], serie=[12,12,12,12,12,12], duree="210",
      statut="mesuree", ecart="35", nb_cas=72, repartition="regroupee", atyp="0.10", nb_atyp=72, transfert="leger",
      jours="20", abo="300", type_arbre="B", vague="vague_2", risque="moyen", procedure="PROC-15", ecart_proc=True,
      visibilite=True, canaux=["journaux","documents","tickets"],
      faits=dict(api_ou_flux_natif=True, travail_deterministe=True, interface_stable=True)),
 dict(id="P-20", nom="Saisie des releves de temperature", nom_en="Keying temperature readings",
      service="approvisionnements", motifs=["RESS-04","RESS-05"], serie=[58,60,62,64,66,61], duree="5", statut="mesuree",
      ecart="1.0", nb_cas=370, repartition="regroupee", atyp="0.05", nb_atyp=370, transfert="leger",
      jours="14", abo="0", type_arbre="E", vague="aucune", risque="moyen", procedure="PROC-16", ecart_proc=False,
      visibilite=False, canaux=["documents"],
      faits=dict(travail_deterministe=True, interface_stable=False, dependance_externe_non_contractuelle=True)),
 dict(id="P-21", nom="Analyse des appels entrants du support", nom_en="Analysing inbound support calls",
      service="support", motifs=["COORD-04","RECH-01"], serie=[225,232,240,248,255,235], duree="12", statut="mesuree",
      ecart="3.5", nb_cas=1430, repartition="semi_regroupee", atyp="0.20", nb_atyp=1430, transfert="standard",
      jours="25", abo="400", type_arbre="D", vague="vague_3", risque="eleve", procedure="PROC-17", ecart_proc=False,
      visibilite=True, canaux=["appels","tickets"], faits=dict(jugement_requis=True)),
 dict(id="P-22", nom="Preparation du reporting du conseil d administration", nom_en="Preparing the board reporting",
      service="comptabilite", motifs=["REPO-03","REPO-04"], serie=[0.33,0.33,0.34,0.33,0.33,0.34], duree="960",
      statut="inferree", ecart="200", nb_cas=0, repartition="regroupee", atyp="0.50", nb_atyp=2, transfert="aucun",
      jours="10", abo="0", type_arbre="D", vague="aucune", risque="eleve", piege="volume_faible",
      procedure="PROC-15", ecart_proc=False, visibilite=True, canaux=["documents"],
      faits=dict(jugement_requis=True)),
 dict(id="P-23", nom="Comptes rendus de reunions et diffusion", nom_en="Meeting minutes and distribution",
      service="support", motifs=["COORD-04","REPO-05"], serie=[36,38,40,42,44,39], duree="20", statut="mesuree",
      ecart="5", nb_cas=236, repartition="regroupee", atyp="0.12", nb_atyp=236, transfert="leger",
      jours="8", abo="120", type_arbre="B", vague="vague_2", risque="faible", procedure="PROC-11", ecart_proc=False,
      visibilite=False, canaux=["appels","documents"],
      faits=dict(api_ou_flux_natif=True, travail_deterministe=True, interface_stable=True)),
]

DEFAUT = dict(statut="mesuree", ecart="1.0", transfert="standard", tjm="650", maintenance="0.08",
              risque="moyen", changements=0, visibilite=False, part_volume="1", suppression=False,
              piege=None, ecart_proc=False, abo="0", jours="8")

def composantes(nom_preset, p):
    preset = p.get("transfert_override") or TRANSFERT[nom_preset]
    return [dict(nom=n, taux=t, duree_minutes=d, forfait_heures=f) for n, t, d, f in preset]

def calculer(p):
    serie = [D(x) for x in p["serie"]]
    mediane = D(statistics.median([float(x) for x in serie]))
    if "amplitude" in p:
        mini, maxi = D(p["amplitude"][0]), D(p["amplitude"][1])
    else:
        mini, maxi = min(serie), max(serie)
    ecart_type = D(p.get("ecart_type") or round(statistics.stdev([float(x) for x in serie]), 2))
    part_vol = D(p["part_volume"])
    occ = mediane * part_vol
    duree = D(p["duree"])
    coef = COEF[p["repartition"]]
    brut = occ * duree / 60
    frag = brut * coef
    comps = composantes(p["transfert"], p)
    if p["suppression"]:
        transf = D(0); inel = D(0)
    else:
        transf = sum((occ * D(c["taux"]) * D(c["duree_minutes"]) / 60 if c["taux"] else D(c["forfait_heures"]) for c in comps), D(0))
        inel = brut * D(p["atyp"])
    net = max(D(0), frag - transf - inel)
    gain_m = net * TAUX_HORAIRE
    naif_m = brut * TAUX_HORAIRE
    jours, tjm = D(p["jours"]), D(p["tjm"])
    dev = jours * tjm
    outil = D(p["abo"]) * 12
    maint = dev * D(p["maintenance"])
    annee1 = dev + outil + maint
    recurrent = outil + maint
    delai = (annee1 / gain_m) if gain_m > 0 else None
    return dict(
        occurrences=dict(serie=[str(x) for x in serie], mediane=str(mediane), minimum=str(mini),
                         maximum=str(maxi), ecart_type=str(ecart_type), nb_mois=len(serie)),
        transfert=comps,
        attendu=dict(
            temps_brut_heures=str(r1(brut)), coefficient_fragmentation=str(coef),
            temps_fragmente_heures=str(r1(frag)), temps_transfere_heures=str(r1(transf)),
            temps_ineliminable_heures=str(r1(inel)), temps_net_heures=str(r1(net)),
            gain_mensuel=str(r2(gain_m)), gain_annuel=str(r2(gain_m * 12)),
            gain_naif_mensuel=str(r2(naif_m)),
            ecart_naif=str(r2(naif_m / gain_m)) if gain_m > 0 else None,
            cout=dict(developpement=str(r2(dev)), outil_annuel=str(r2(outil)),
                      maintenance_annuelle=str(r2(maint)), annee_1=str(r2(annee1)),
                      recurrent=str(r2(recurrent))),
            delai_retour_mois=str(r1(delai)) if delai is not None else None,
            gain_trois_ans=str(r2(gain_m * 36 - (annee1 + recurrent * 2))),
        ),
    )

def deconseil(p, calc):
    a = calc["attendu"]
    gain_annuel = D(a["gain_annuel"]); delai = a["delai_retour_mois"]
    motifs = []
    if p["faits"].get("obligation_legale_humaine"):
        motifs.append(("obligation_legale", "obligation legale de traitement humain (signature)", "reexamen si le texte change"))
    if D(p["atyp"]) > D("0.40"):
        motifs.append(("jugement_non_formalisable", f"part atypique {D(p['atyp'])*100:.0f} % > 40 %", "reexamen si la part atypique passe sous 30 %"))
    if p["changements"] >= 3:
        motifs.append(("instabilite", f"{p['changements']} changements en 12 mois", "reexamen apres 6 mois de stabilite"))
    if p["faits"].get("dependance_externe_non_contractuelle"):
        motifs.append(("dependance_externe", "portail tiers sans API ni engagement de stabilite", "reexamen si une API contractuelle est disponible"))
    if gain_annuel < D(3000):
        motifs.append(("volume_insuffisant", f"gain annuel net {gain_annuel} EUR < 3 000 EUR", "reexamen si le volume depasse 15 occurrences/mois"))
    if delai is not None and D(delai) > D(36):
        motifs.append(("retour_trop_long", f"delai de retour {delai} mois > 36 mois", "reexamen si le cout baisse sous 12 mois de gain"))
    return motifs

def type_final(p, decons):
    f = p["faits"]
    if f.get("etape_supprimable_amont"): arbre = "A"
    elif f.get("api_ou_flux_natif"): arbre = "B"
    elif f.get("travail_deterministe") and f.get("interface_stable"): arbre = "C"
    elif f.get("jugement_requis"): arbre = "D"
    else: arbre = "E"
    return arbre, ("E" if decons else arbre)

sortie = []
for brut in P:
    p = {**DEFAUT, **brut, **OVERRIDES.get(brut["id"], {})}
    calc = calculer(p)
    decons = deconseil(p, calc)
    arbre, final = type_final(p, decons)
    assert arbre == p["type_arbre"], f"{p['id']}: arbre {arbre} != attendu {p['type_arbre']}"
    sortie.append(dict(
        id=p["id"], nom=p["nom"], nom_en=p["nom_en"], service=p["service"],
        famille_poste="administratif", motifs=p["motifs"], canaux=p["canaux"],
        duree_unitaire_minutes=p["duree"], duree_statut=p["statut"],
        duree_ecart_minutes=p["ecart"], duree_nb_cas=p["nb_cas"],
        repartition=p["repartition"], part_atypique=p["atyp"], part_atypique_nb_cas=p["nb_atyp"],
        cout=dict(jours=p["jours"], tjm=p["tjm"], abonnement_mensuel=p["abo"], taux_maintenance=p["maintenance"]),
        faits=p["faits"], part_volume_traitee=p["part_volume"], suppression_etape=p["suppression"],
        procedure_ref=p["procedure"], ecart_procedure=p["ecart_proc"],
        changements_douze_mois=p["changements"], visibilite_dirigeant=p["visibilite"],
        piege=p["piege"], risque_attendu=p["risque"], type_arbre_attendu=arbre, type_final_attendu=final,
        vague_attendue=p["vague"],
        deconseil_attendu=[dict(motif=m, seuil=s, condition=c) for m, s, c in decons],
        **calc,
        variante_b=p.get("variante_b"),
    ))

doc = dict(
    version="1.0",
    note="Ground truth of the 23 demo processes, owned by lot 0. The generator (lot 3) produces raw channel records whose measured aggregates match this table; the classification and sequencing lots are evaluated against it. Expected outputs are computed by an independent implementation of annex A - a cross-check for lot 1, not a copy of it.",
    client=dict(id="T-DEMO", nom="Demo Distribution SAS", nom_en="Demo Distribution SAS",
                effectif=120, secteur="distribution specialisee B2B",
                services=["approvisionnements", "adv", "comptabilite", "support"],
                sites=["lyon", "villeurbanne"], effectif_par_service={"approvisionnements": 22, "adv": 34, "comptabilite": 18, "support": 46},
                taux_horaires=dict(fournis=True, devise="EUR", par_famille={"administratif": "42"}),
                fenetre=dict(debut="2026-05-01", fin="2026-11-01", nb_mois=6),
                filigrane="SYNTHETIQUE - DEMONSTRATION"),
    graine=20261111,
    couverture=dict(volume_travail_estime_heures="26000", non_couvert=[
        "travail de terrain (entrepot, livraisons)", "reunions non enregistrees",
        "echanges oraux informels", "messagerie instantanee hors perimetre"]),
    processus=sortie,
)
Path("demo/spec-processus.json").write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

total = sum(D(x["attendu"]["gain_annuel"]) for x in sortie if x["type_final_attendu"] != "E")
decons = [x["id"] for x in sortie if x["type_final_attendu"] == "E"]
print("processus:", len(sortie))
print("deconseilles:", len(decons), decons, f"{len(decons)/len(sortie)*100:.0f} %")
print("gain annuel net total (hors E):", total)
for x in sortie:
    a = x["attendu"]
    print(f'{x["id"]} {x["type_arbre_attendu"]}->{x["type_final_attendu"]} {x["vague_attendue"]:9s} net {a["temps_net_heures"]:>6} h  {a["gain_mensuel"]:>9} EUR/mois  naif {a["gain_naif_mensuel"]:>9}  x{a["ecart_naif"]}  cout1 {a["cout"]["annee_1"]:>9}  retour {a["delai_retour_mois"]} mois')
