# CONTRACTS — Gisement (frozen at S0, lot 0)

This file is the **contract** between the lots. It is frozen: a lot implements
against it, it does not redesign it. If a contract is wrong, open an issue in
`docs/DECISIONS.md` with a new decision number, change the contract, and tell
the orchestrator — never silently diverge.

Source of truth for behaviour: `docs/fr/CAHIER-DES-CHARGES.md` (chapters and annexes are
quoted below as `§13.2`, `annex A`).

---

## 0. Rules every lot obeys

1. **Files < 500 lines, functions < 50 lines** (`python3 scripts/check_limits.py`).
2. **`ruff check` and `ruff format --check` clean** on `src tests eval infra scripts`.
3. **Offline by default.** No test may need AWS credentials, network, Transcribe
   or Bedrock Data Automation (§26.4). Every AWS service is reached through an
   adapter that has an in-memory fake.
4. **`Decimal` everywhere** for money and hours (ENF-13). Never a float in a
   returned value. **A model never computes a figure** (EF-35): models classify
   facts, `gisement.calcul` does the arithmetic.
5. **Deterministic.** Same seed → same output (ENF-08). Use
   `random.Random(graine)` / `numpy`-free code; no `time()` in a computed value.
6. **No person identifier** anywhere in a returned structure (R1). The only
   individual-related field is `groupe_pseudonyme`.
7. **Do not edit a file owned by another lot.** Ownership map in §1.
8. **Tests live in `tests/unit/<lot>/`** (or `tests/integration/`), one test file
   per behaviour, `pytest` only, no new dependency without saying so.
9. **A lot delivers**: code + tests + its row in `docs/TRACEABILITY.md` + a PR
   whose body has a `## Scope` section listing its files as bullets.
10. Three failures on the same point → stop, leave the code as is, answer `KO`
    with the reason. Do not delegate to another agent.

Standard verification before answering:

```bash
cd ~/projets/gisement && export PYTHONPATH=src
python3 -m ruff check src tests eval infra scripts
python3 -m ruff format --check src tests eval infra scripts
python3 scripts/check_limits.py
python3 -m pytest -q                      # full suite, must stay green
```

---

## 1. Ownership map

| Lot | Paths it owns | Depends on |
|---|---|---|
| 0 | `src/gisement/types/`, `serialisation.py`, `empreinte.py`, `cli.py`, `commands/__init__.py`, `modeles/`, `config/`, `docs/CONTRACTS.md`, `.github/`, `scripts/`, `pyproject.toml`, `Makefile`, `.mergify.yml`, `tests/conftest.py` | — |
| 1 | `src/gisement/calcul/`, `tests/unit/calcul/` | 0 |
| 2 | `catalogue/`, `src/gisement/motifs/` (package allowed), `tests/unit/motifs/` | 0 |
| 3 | `demo/genere.mjs`, `demo/donnees/**`, `demo/lisez-moi.md`, `src/gisement/commands/generer.py`, `tests/unit/demo/` | 0 |
| 4 | `src/gisement/canaux/tickets/`, `tests/unit/canaux/test_tickets*.py` | 0, 3 |
| 5 | `src/gisement/canaux/courriels/` | 0, 3 |
| 6 | `src/gisement/canaux/documents/` | 0, 3 |
| 7 | `src/gisement/canaux/appels/` | 0, 3 |
| 8 | `src/gisement/canaux/journaux/`, `src/gisement/couverture.py` | 0, 3 |
| 9 | `src/gisement/assainissement/` | 0 |
| 10 | `src/gisement/classifieur/`, `src/gisement/modeles/bedrock.py` | 2, 4-8 |
| 11 | `src/gisement/processus/` | 10 |
| 12 | `src/gisement/politique/`, `tests/unit/politique/`, `eval/non_attribution.py` | 0 |
| 13 | `src/gisement/faisabilite.py` | 11 |
| 14 | `src/gisement/sequenceur.py` | 1, 13 |
| 15 | `src/gisement/deconseil.py` | 1, 11 |
| 16 | `src/gisement/rapports/`, `src/gisement/commands/rapport.py` | 11, 14, 15 |
| 17 | `src/gisement/suivi/`, `src/gisement/commands/suivi.py` | 14 |
| 18 | `src/gisement/api/`, `src/gisement/stockage/`, `src/gisement/pipeline.py`, `portal/`, `src/gisement/commands/{smoke,mesurer,portefeuille,serve}.py`, `src/gisement/lambdas/` | 11, 14, 16 |
| 19 | `infra/quick/`, `src/gisement/commands/assets.py` | 18 |
| 20 | `src/gisement/observabilite/` | 4-8 |
| 21 | `iac/`, `docs/RUNBOOK.md` | 12, 18 |
| 22 | `eval/` (except `non_attribution.py`), `src/gisement/commands/eval.py` | 10, 12 |
| 23 | `docs/*.md` (EN), `README.md` | everything |
| 24 | `media/`, `docs/VIDEO.md` | 18, 23 |

Two lots never write the same file. `tests/conftest.py` is owned by lot 0: ask
for a new shared fixture instead of editing it.

---

## 2. Lot 0 deliverables (already in the repository)

### 2.1 `gisement.types` — the frozen vocabulary

Import from `gisement.types` only. Submodules exist to stay under 500 lines.

Constants (`types/communs.py`) — changing one is a decision, not a tweak:

| Constant | Value | Spec |
|---|---|---|
| `SEUIL_AGGREGATION_DEFAUT` | 5 | R2 |
| `TAUX_REVUE_DEFAUT` | 0.20 | §13.1 |
| `DUREE_INFEREE_MARGE` | 0.40 | §17.2 |
| `INCERTITUDE_FRAGMENTATION` | 0.05 | §17.2 |
| `INCERTITUDE_TAUX_RELATIVE` | 0.25 | §17.2 |
| `TIRAGES_MONTE_CARLO` | 10 000 | §17.2 |
| `NIVEAU_CONFIANCE` / `QUANTILES_90` | 0.90 / (0.05, 0.95) | §17.2 |
| `GAIN_ANNUEL_MINIMAL` | 3 000 | §16.1 |
| `DELAI_RETOUR_MAXIMAL_MOIS` | 36 | §16.1 |
| `PART_ATYPIQUE_MAXIMALE` | 0.40 | §16.1 |
| `CHANGEMENTS_INSTABILITE` | 3 | §16.1 |
| `VAGUE1_DELAI_MAX_MOIS` / `VAGUE1_BUDGET_MAX` / `VAGUE2_DELAI_MAX_MOIS` | 6 / 15 000 / 18 | §15.3 |
| `SEUIL_CONFIANCE_CLASSIFICATION` | 0.70 | §21.2 |
| `COHORTE_CLIENTS_MINIMALE` | 5 | §25 |
| `GRILLE_TJM_DEFAUT` / `TAUX_MAINTENANCE_DEFAUT` | 650 / 0.08 | annex A.4 |
| `COEFFICIENTS_FRAGMENTATION` | 0.90 / 0.70 / 0.45 / 0.85 | §13.1 |

Enumerations: `Canal`, `StatutDuree`, `Repartition`, `TypeAutomatisation`,
`MotifDeconseil`, `Risque`, `Vague`, `StatutCampagne`, `StatutValidation`,
`StatutSuivi`, `FormeIncertitude`, `Langue`, `Role`, `Regle`.

Money helpers: `decimal`, `arrondi`, `euros`, `heures`, `mois`, `facteur`,
`pourcentage`. Rounding is `ROUND_HALF_UP`; hours and months publish one
decimal, euros and factors two.

Dataclasses (all `frozen=True`): `Tenant`, `TauxHoraires`, `Perimetre`,
`Conformite`, `CoutCampagne`, `Couverture`, `Corpus`, `Campagne`,
`EntreeRegistre` (`types/campagne.py`); `Activite`, `GroupeEmpreinte`,
`OccurrencesMensuelles`, `Motif`, `EcartProcedure`, `Processus`, `RevueHumaine`
(`types/mesure.py`); `Incertitude`, `ComposanteTransfert`, `CoutAutomatisation`,
`FaitsFaisabilite`, `EntreeGisement`, `Intervalle`, `DecompositionCout`,
`Gisement`, `Faisabilite`, `Deconseille`, `CriterePriorite`, `Projet`,
`Portefeuille`, `SuiviTrimestriel`, `PrecisionCumulee` (`types/economie.py`);
`RequeteMesure`, `Decision`, `AccesJournalise`, `ExclusionOpposition`
(`types/conformite.py`).

### 2.2 Helpers

- `gisement.serialisation`: `vers_json`, `json_deterministe`, `empreinte`
  (SHA-256 of canonical JSON — used to chain the register), `depuis_dict`,
  `ecrire_json`, `lire_json`. A `Decimal` is serialised as a **string**.
- `gisement.empreinte`: `normaliser`, `mots_pertinents`, `verbe`, `objets`,
  `systemes`, `signature(texte, systemes) -> str`, `empreinte(signature) -> str`
  (16 hex chars), `empreinte_complete(texte, systemes) -> (signature, hash)`.
- `gisement.modeles`: `Modele` protocol, `ModeleFictif`, `ReponseModele`
  (§2.6 below).

### 2.3 Shared fixtures (`tests/conftest.py`)

`cas_reference` → the `EntreeGisement` of annex A (process `P-07`): 320
occurrences per month (median), 9 minutes measured on 1 840 cases, semi-grouped
spread, 15 % atypical, three transfer components (review 20 % × 1.5 min,
rejects 5 % × 12 min, supervision 3.2 h flat), 42 €/h, 12 days at 650 €,
180 €/month subscription, 8 % maintenance, seed `20261111`.

`CAS_REFERENCE_ID == "P-07"`.

### 2.4 Configuration files (`config/`, read-only data, JSON)

- `config/tarifs.json` — unit prices used to measure the cost of a campaign
  (KPI-8). Keys: `transcribe_usd_par_minute`, `data_automation_usd_par_page`,
  `nova_lite_usd_par_million_entree`, `nova_lite_usd_par_million_sortie`,
  `modele_fort_usd_par_million_entree`, `modele_fort_usd_par_million_sortie`.
- `config/campagne.json` — defaults for a campaign: seed, budget caps
  (`budget_usd`, `appels_modele_max`, `jetons_entree_max`), audio cap in hours,
  document cap in pages, window in months, sampling sizes.
- `config/priorite.json` — the weights of §15.2 (`gain` .35, `faisabilite` .25,
  `rapidite` .20, `visibilite` .15, `securite_juridique` .05) plus the wave
  thresholds. Versioned: a MSP may prefer gain over speed without code change.

Load them with `json.loads(Path(...).read_text())` and convert with
`gisement.types.decimal`. Never hardcode a price in a module.

### 2.5 CLI

`python3 -m gisement.cli <commande>` dispatches to
`gisement.commands.<commande>:main(argv) -> int`. Commands: `smoke`, `demo`,
`generer`, `mesurer`, `portefeuille`, `rapport`, `suivi`, `eval`, `assets`,
`serve`. A missing command prints a clear message and returns 2.

### 2.6 Model interface (`src/gisement/modeles/`)

```python
class Modele(Protocol):
    nom: str
    def classer(self, invite: str, schema: dict) -> ReponseModele: ...
    def rediger(self, invite: str) -> str: ...

@dataclass(frozen=True)
class ReponseModele:
    donnees: dict          # validated against `schema`
    confiance: Decimal     # 0..1
    citations: tuple[str, ...]
    jetons_entree: int
    jetons_sortie: int
    modele: str
```

`ModeleFictif(reponses=None, chemin=None)` answers deterministically from a
table (or from a JSON file of the demo dataset). `BedrockModele` (lot 10) is the
real adapter; it is never instantiated in a test.

---

## 3. Economic engine — lot 1 (`src/gisement/calcul/`)

Modules: `__init__.py` (re-exports), `corrections.py`, `monte_carlo.py`,
`moteur.py`, `incertitudes.py`.

```python
def coefficient_fragmentation(repartition: Repartition) -> Decimal
def temps_brut(entree: EntreeGisement) -> Decimal                      # hours
def temps_transfere(entree: EntreeGisement) -> tuple[Decimal, tuple[tuple[str, Decimal], ...]]
def temps_ineliminable(entree: EntreeGisement) -> Decimal
def decomposer_cout(cout: CoutAutomatisation) -> DecompositionCout
def calculer(entree: EntreeGisement) -> Gisement                       # the whole engine
def incertitudes(entree: EntreeGisement) -> dict[str, Incertitude]
def simuler(entree: EntreeGisement, tirages: int = TIRAGES_MONTE_CARLO) -> tuple[Intervalle, Intervalle | None]
```

`EntreeGisement` also carries `part_volume_traitee` (share of the volume the
project addresses) and `suppression_etape` (a type A action removes the step:
no transfer, no ineliminable share on that part). `occurrences_effectives =
occurrences.mediane * part_volume_traitee`.

**Formulas (§13.2 + annex A, authoritative order):**

```
occurrences_eff    = occurrences.mediane * part_volume_traitee
temps_brut         = occurrences_eff * duree_unitaire_minutes / 60
temps_fragmente    = temps_brut * COEFFICIENTS_FRAGMENTATION[repartition]
temps_transfere    = 0 if suppression_etape else sum(c.heures(occurrences_eff) for c in transfert)
temps_ineliminable = 0 if suppression_etape else temps_brut * part_atypique   # decision D-01
temps_net          = max(0, temps_fragmente - temps_transfere - temps_ineliminable)

gain_mensuel       = temps_net * taux_horaire            # None if taux_horaire is None
gain_annuel        = gain_mensuel * 12
gain_naif_mensuel  = temps_brut * taux_horaire
ecart_naif         = gain_naif_mensuel / gain_mensuel    # KPI-4, 2 decimals

cout.developpement = jours * tjm
cout.outil_annuel  = abonnement_mensuel * 12
cout.maintenance   = cout.developpement * taux_maintenance
cout.annee_1       = developpement + outil_annuel + maintenance
cout.recurrent     = outil_annuel + maintenance

delai_retour_mois      = cout.annee_1 / gain_mensuel     # 1 decimal
delai_retour_naif_mois = cout.annee_1 / gain_naif_mensuel
gain_trois_ans         = gain_annuel * 3 - (cout.annee_1 + cout.recurrent * 2)
```

**Golden test (R2, R3) — the fixture `cas_reference` must give exactly:**

| Field | Value |
|---|---|
| `temps_brut_heures` | `48.0` |
| `coefficient_fragmentation` | `0.70` |
| `temps_fragmente_heures` | `33.6` |
| `temps_transfere_heures` | `8.0` |
| `temps_ineliminable_heures` | `7.2` |
| `temps_net_heures` | `18.4` |
| `gain_mensuel` | `772.80` |
| `gain_annuel` | `9273.60` |
| `gain_naif_mensuel` | `2016.00` |
| `ecart_naif` | `2.61` |
| `cout.annee_1` | `10584.00` |
| `cout.recurrent` | `2784.00` |
| `delai_retour_mois` | `13.7` |
| `delai_retour_naif_mois` | `5.2` |
| `gain_trois_ans` | `11668.80` |

**Second golden test (annex A.7 - the type A action on P-07):** the same entry
with `part_volume_traitee = 0.78`, `suppression_etape = True`,
`cout = CoutAutomatisation(jours=3, tjm=650, abonnement_mensuel=0,
taux_maintenance=0)` must give `temps_net_heures = 26.3`, `gain_mensuel =
1102.50`, `cout.annee_1 = 1950.00`, `delai_retour_mois = 1.8`.

**Monte-Carlo (§17.2, R4).** `incertitudes()` derives one `Incertitude` per
parameter, from measurement quality — not from a guess:

| Parameter | Shape | Centre | Spread |
|---|---|---|---|
| occurrences | `NORMALE` | `occurrences.mediane` | `occurrences.ecart_type / sqrt(nb_mois)` |
| durée unitaire, `MESUREE` | `NORMALE` | `duree_unitaire_minutes` | `duree_ecart_minutes / sqrt(max(1, duree_nb_cas))` |
| durée unitaire, `INFERREE` | `UNIFORME` | `duree_unitaire_minutes` | `duree * DUREE_INFEREE_MARGE` |
| coefficient de fragmentation | `UNIFORME` | coefficient of the `repartition` | `INCERTITUDE_FRAGMENTATION` |
| part atypique | `NORMALE` | `part_atypique` | `0.02` if `part_atypique_nb_cas >= 100` else `0.05` |
| each transfer rate | `UNIFORME` | `composante.taux` | `composante.taux * INCERTITUDE_TAUX_RELATIVE` |

`simuler()` draws `tirages` samples with `random.Random(entree.graine)`, applies
the formulas above to each draw (clamping `temps_net` at 0), sorts, and returns
the 5 %/95 % quantiles as `Intervalle` for the net hours and, when a rate is
given, for the monthly gain. Two runs with the same seed give **strictly
identical** intervals (R4). With `cas_reference` the hours interval must be
`[14.8, 22.1] ± 0.4` and the gain interval `[622, 928] ± 20` (annex A.6).

No `numpy`, no `statistics.gaussian`: use `random.Random.gauss` and
`random.Random.uniform` (both deterministic at a fixed seed).

---

## 4. Motif catalogue — lot 2 (`catalogue/`, `src/gisement/motifs/` (package allowed))

`catalogue/motifs/<famille>.json`, one file per family of annex B (8 families,
40 motifs). A motif is data, adding one needs no code (R25):

```json
{
  "ref": "RESS-01",
  "famille": "ressaisie",
  "nom": "Courriel vers ERP",
  "nom_en": "Email into the ERP",
  "description": "Recopier une commande reçue par courriel dans l'ERP.",
  "canaux": ["courriels", "journaux"],
  "indices": {"verbes": ["recopier", "saisir"], "objets": ["commande", "courriel", "erp"], "systemes": ["erp", "messagerie"]},
  "duree_unitaire_typique_minutes": "9",
  "duree_statut_defaut": "inferree",
  "repartition_defaut": "semi_regroupee",
  "taux_revue_defaut": "0.20",
  "duree_revue_minutes": "1.5",
  "part_atypique_defaut": "0.15",
  "types_envisageables": ["A", "B"],
  "cout_jours_min": "3", "cout_jours_max": "15",
  "abonnement_mensuel": "180"
}
```

Public API:

```python
@dataclass(frozen=True)
class MotifCatalogue: ...        # one motif, fields above (Decimal for numbers)
@dataclass(frozen=True)
class Catalogue:
    motifs: tuple[MotifCatalogue, ...]
    def par_ref(self, ref: str) -> MotifCatalogue
    def famille(self, nom: str) -> tuple[MotifCatalogue, ...]
    def candidats(self, signature: str, systemes: tuple[str, ...]) -> tuple[CandidatMotif, ...]
def charger_catalogue(racine: str | Path | None = None) -> Catalogue   # default: catalogue/
def valider_catalogue(catalogue: Catalogue) -> tuple[str, ...]         # error messages, () if valid
```

`CandidatMotif(ref, nom, score: Decimal)`. The score is a lexical overlap
between the fingerprint indices and the motif indices — deterministic, no model.
Validator rules: unique `ref`, `famille` in the 8 of annex B, counts per family
match annex B (7/6/6/5/4/5/4/3), `types_envisageables` non-empty, prices as
strings parseable by `decimal()`.

---

## 5. Demo dataset — lot 3 (`demo/genere.mjs`, `demo/donnees/`)

Node 22, **no dependency**, fixed seed, reproducible byte for byte
(`node demo/genere.mjs --verifier` compares the regenerated files with the
committed ones and exits non-zero on drift).

The **ground truth of the 23 processes is `demo/spec-processus.json`, owned by
lot 0** (already committed): volumes, durations, spreads, transfer components,
costs, feasibility facts, expected type, expected wave and the three traps. The
generator produces raw channel records whose measured aggregates match that
table; it never invents a process. `demo/donnees/attendus/processus.json` is a
copy of it enriched with what the generator actually produced.

`demo/genere.mjs --sortie demo/donnees` writes the tree below. Every file
carries the watermark `SYNTHETIQUE — DEMONSTRATION` (in `manifeste.json` and in
a header comment field of each record set). **No real personal data** (ENF-11):
all names, companies and products are generated from the fixed lists in
`demo/genere.mjs`.

```
demo/donnees/
  manifeste.json            seed, window, tenant, hourly rates, channel volumes, coverage denominator
  tickets/tickets.jsonl     4 800 records
  courriels/courriels.jsonl 2 000 records (already the stratified sample, strata published)
  documents/documents.json  200 metadata records
  documents/extractions/<document_id>.json   frozen Bedrock Data Automation output
  appels/appels.json        metadata of the recorded calls (6 h total, consent flag)
  appels/transcriptions/<appel_id>.json      frozen Amazon Transcribe output
  journaux/journaux.csv     12 400 lines
  procedures/<ref>.md       8 written procedures, deliberately out of step with practice
  attendus/processus.json   ground truth: the 23 processes, volumes, traps, expected type
  attendus/motifs.json      the 15 implanted motifs with known volumes
  attendus/economique.json  30 hand-computed economic cases (input + expected output)
  attendus/non_attribution.json  50 requests that must be refused (18 by filter combination)
  attendus/sensibles.json   100 documents with planted sensitive categories
  attendus/activites_etiquetees.json  200 hand-labelled activities
```

Record schemas (frozen — a collector reads exactly this):

```jsonc
// tickets.jsonl
{"id":"T-000123","horodatage":"2026-06-14T09:12:00","service":"adv","site":"lyon",
 "agent":"Marie Dupont","sujet":"Saisie commande fournisseur","description":"...",
 "systeme":"erp","duree_traitement_minutes":9.4,"statut":"clos","allers_retours":2,
 "groupe":"ADV-JOUR"}

// courriels.jsonl
{"id":"M-000456","horodatage":"2026-06-14T09:12:00","expediteur":"fournisseur@demo.example",
 "destinataires":["marie.dupont@demo.example"],"objet":"Commande 45892","corps":"...",
 "service":"adv","stratum":"adv_semaine_24","piece_jointe":"bon_commande.pdf"}

// documents.json
{"id":"D-000031","type":"bon_de_commande","titre":"...","chemin":"documents/D-000031.pdf",
 "pages":2,"service":"approvisionnements","horodatage":"2026-06-14"}

// documents/extractions/D-000031.json  (frozen BDA output)
{"document_id":"D-000031","confiance":0.93,
 "champs":{"numero":"45892","fournisseur":"DEMO-FR-12","montant_ht":"1284.50","date":"2026-06-14"},
 "tableaux":[{"nom":"lignes","colonnes":["ref","qte","pu"],"lignes":[["R-12",4,"321.13"]]}],
 "categories_sensibles_detectees":[]}

// appels.json
{"id":"A-0007","duree_minutes":42.5,"horodatage":"2026-06-14T14:00:00","service":"support",
 "consentement":true,"type":"reunion","transcription":"appels/transcriptions/A-0007.json"}

// appels/transcriptions/A-0007.json  (frozen Transcribe output, diarised + redacted)
{"appel_id":"A-0007","langue":"fr-FR","duree_minutes":42.5,"piis_occultees":7,
 "segments":[{"debut":0.0,"fin":12.4,"locuteur":"LOC-1","texte":"..."}]}

// journaux.csv  (header line)
horodatage,service,action,entite,systeme,groupe,duree_secondes
```

`attendus/processus.json` — the 23 processes, each:

```jsonc
{"id":"P-07","nom":"Saisie des commandes fournisseurs reçues par courriel","service":"approvisionnements",
 "motifs":["RESS-01","VERI-03"],"occurrences_medianes":"320","amplitude":{"min":"210","max":"465"},
 "duree_unitaire_minutes":"9","duree_statut":"mesuree","repartition":"semi_regroupee",
 "part_atypique":"0.15","type_attendu":"B","piège":null,
 "canaux":["courriels","tickets","journaux"],"famille_poste":"administratif",
 "procedure_ref":"PROC-04","ecart_procedure":true,"changements_douze_mois":0,
 "visibilite_dirigeant":true}
```

The three traps (§28.1) must be present: `P-16` seasonal peak (40/month average,
310 in December), `P-07` divergent written procedure, `P-02` high judgement
(60/month, 55 % atypical → type D or E, **never** wave 1).

Coverage denominator: `manifeste.json.volume_travail_estime_heures` such that the
published coverage is **62 %** (R14), with the uncovered list.

---

## 6. Collectors — lots 4 to 8 (`src/gisement/canaux/<canal>/`)

Each channel package exposes the same three functions (a collector is
independent and idempotent, EF-10):

```python
def collecter(source: Source, campagne: Campagne, graine: int) -> tuple[Activite, ...]
def mesurer_volume(source: Source) -> int
def couverture(source: Source, declare_heures: Decimal) -> Decimal
```

`Source` is a lot-0-free protocol declared in each package (`source.py`):
`SourceFichiers(racine: Path)` reads the demo dataset, `SourceAws(...)` is the
real adapter (never used in tests). A collector **never** returns a person
identifier: it calls `gisement.assainissement.pseudonymiser` (lot 9) before
building an `Activite`, and `gisement.empreinte.signature` for the fingerprint.

Lot 7 (calls) and lot 6 (documents) read the **frozen** transcripts and
extractions of `demo/donnees/`; the Transcribe / Data Automation adapters exist
and are unit-tested with a fake, but no test calls AWS (§26.4).

Lot 8 also owns `src/gisement/couverture.py`:

```python
def couverture_par_canal(volumes: dict[Canal, Decimal], declare_heures: Decimal) -> Couverture
def non_couvert(couverture: Couverture) -> tuple[str, ...]
```

---

### 6.1 Sanitisation — lot 9 (`src/gisement/assainissement/`)

Frozen here because lots 4 to 8 call it. Modules: `__init__.py`,
`pseudonymisation.py`, `sensibles.py`, `detecteurs.py`, `rapport.py`.

```python
CATEGORIES_SENSIBLES: tuple[str, ...]   # sante, opinion_syndicale, opinion_politique,
                                        # religion, vie_sexuelle, origine_ethnie, genetique

@dataclass(frozen=True)
class OccurrencePii:
    categorie: str        # "personne", "email", "telephone", "adresse", "numero_securite_sociale", ...
    valeur_pseudonymisee: str
    debut: int
    fin: int

@dataclass(frozen=True)
class RapportAssainissement:
    canal: Canal
    volume_entree: int
    volume_sortie: int
    pseudonymes_appliques: int
    categories_sensibles: tuple[str, ...]
    exclus: int            # records dropped because a sensitive category was detected
    graine: int

def pseudonyme(identifiant: str, cle: str | bytes, sel: str = "") -> str
    # HMAC-SHA256, not reversible without the key, returned as "PSD-" + 16 hex chars
def pseudonymiser_texte(texte: str, cle: str | bytes, sel: str = "") -> tuple[str, tuple[OccurrencePii, ...]]
def groupe_pseudonyme(service: str, site: str = "", equipe: str = "") -> str
    # e.g. "ADV-JOUR": a group label, never a person
def detecter_categories(texte: str) -> tuple[str, ...]
def filtrer(texte: str) -> tuple[str, tuple[str, ...]]      # redacted text + categories found
def assainir(enregistrement: dict, canal: Canal, *, cle: str | bytes, sel: str = "",
             graine: int = 0) -> tuple[dict | None, tuple[OccurrencePii, ...], tuple[str, ...]]
    # None when the record must be dropped (a sensitive category was detected, EF-12)

class DetecteurPii(Protocol):
    def detecter(self, texte: str) -> tuple[OccurrencePii, ...]: ...
class DetecteurLexical: ...      # offline default: regexes + the demo name lists
class ComprehendDetecteur: ...   # the real Amazon Comprehend adapter, never used in a test
```

Rules: pseudonymisation happens **before** any other processing (R3, ENF-02); a
record carrying a sensitive category is **dropped**, not redacted-and-kept
(EF-12, R8); the mapping table (pseudonym -> real identity) is kept apart,
encrypted, and destroyed at the end of the campaign (R3, ENF-06). The lexical
detector is the offline reference implementation: `ComprehendDetecteur` must
produce the same shape, and its unit test uses a fake.

## 7. Non-attribution policy — lot 12 (`src/gisement/politique/`)

Modules: `regles.py`, `passerelle.py`, `journal.py`, `agentcore.py`, `quotas.py`.

```python
def evaluer(requete: RequeteMesure, contexte: ContextePolitique) -> Decision
def context(campagne: Campagne, seuil: int = SEUIL_AGGREGATION_DEFAUT,
            budget_restant: Decimal = Decimal(0), requetes_utilisateur: int = 0) -> ContextePolitique
def exporter_politique_agentcore(contexte: ContextePolitique) -> dict   # the gateway artefact
```

`ContextePolitique(campagne_id, tenant_id, conforme: bool, suspendue: bool,
seuil: int, canaux_autorises, budget_restant: Decimal, requetes_utilisateur: int,
quota_requetes: int = 200)`.

`evaluer` applies, in this order, and returns **every** violated rule (the
refusal names them, annex C):

1. `Regle.TENANT` — `requete.tenant_id != contexte.tenant_id` (EF-71).
2. `Regle.CONFORMITE` — not `contexte.conforme` (EF-04).
3. `Regle.SUSPENSION` — `contexte.suspendue` (ENF-12).
4. `Regle.BUDGET` — `contexte.budget_restant <= 0` (ENF-09).
5. `Regle.CANAL_NON_AUTORISE` — channel not in `canaux_autorises`.
6. `Regle.INDIVIDU` — a grouping in `GROUPEMENTS_INTERDITS` (R1).
7. `Regle.FILTRE_PERSONNE` — a filter key in `FILTRES_PERSONNE` (R1).
8. `Regle.ATTRIBUT_RARE` — a filter key in `ATTRIBUTS_QUASI_IDENTIFIANTS_RARES` (§18.4).
9. `Regle.K5` — `requete.taille_groupe < contexte.seuil` (R2, suppressed not rounded).
10. `Regle.COMBINAISON` — `len(filtres) >= 3` and
    `taille_resultat_apres_filtres < seuil` (§18.4).
11. `Regle.CITATION` — `requete.citations` or a forbidden output field (R1).
12. `Regle.CORPUS_BRUT` — `outil == OUTIL_CORPUS` and the corpus is not sanitised.
13. `Regle.EXPORT` — `outil == OUTIL_EXPORT` with a non-aggregated citation.
14. `Regle.QUOTA_REQUETES` — `requetes_utilisateur > quota_requetes` (§18.4).

`journal.py` appends an `AccesJournalise` to an append-only list/file for every
decision, allowed or refused (EF-53). `agentcore.py` emits the AgentCore Policy
document that expresses the same rules at the gateway (R5) — the local engine is
the reference implementation and the artefact is generated from it, so the two
cannot drift.

**Blocking test (R7):** the 50 requests of `demo/donnees/attendus/non_attribution.json`
are all refused, 100 %, in `eval/` and in `tests/unit/politique/`.

---

## 8. Classification, processes, feasibility, sequence, advice against

```python
# lot 10 - src/gisement/classifieur/
def grouper(activites: Sequence[Activite]) -> tuple[GroupeEmpreinte, ...]
def etiqueter(groupes, catalogue: Catalogue, modele: Modele) -> tuple[Motif, ...]
def proposer_nouveau_motif(groupe: GroupeEmpreinte) -> Motif          # EF-21
def a_revoir(motifs: Sequence[Motif]) -> tuple[RevueHumaine, ...]      # below SEUIL_CONFIANCE_CLASSIFICATION

# lot 11 - src/gisement/processus/
def agreger(motifs, catalogue) -> tuple[Processus, ...]
def valider(processus, decision: StatutValidation, commentaire: str, par: str) -> Processus
def comparer_procedure(processus, procedure: str, observations: str) -> EcartProcedure | None   # EF-25

# lot 13 - src/gisement/faisabilite.py
def type_automatisation(faits: FaitsFaisabilite) -> tuple[TypeAutomatisation, tuple[str, ...]]  # §14.3 tree
def evaluer_faisabilite(processus: Processus, faits: FaitsFaisabilite) -> Faisabilite
def evaluer_risque(faits: FaitsFaisabilite, gisement: Gisement) -> Risque

# lot 14 - src/gisement/sequenceur.py
def normaliser(gisements: Sequence[Gisement]) -> dict[str, Decimal]
def score(criteres: CriterePriorite, poids: PoidsPriorite) -> Decimal
def sequencer(projets: Sequence[Projet], poids=None) -> Portefeuille   # three waves, EF-42, EF-43

# lot 15 - src/gisement/deconseil.py
def motif_deconseil(processus, gisement, faisabilite) -> Deconseille | None   # six reasons, §16.1
def formuler(deconseille: Deconseille, langue: Langue) -> str                 # §16.2, with the re-examination condition
```

`PoidsPriorite` is read from `config/priorite.json` (weights in configuration,
versioned — §15.2). Wave 1 must never contain the biggest gain of the portfolio
when that gain is also the riskiest (R17); if no wave 1 project is possible,
`Portefeuille.recommandation_elargissement` says so instead of inventing one
(EF-43, R18).

---

## 9. Reports, follow-up, API, portal, Quick, IaC

```python
# lot 16 - src/gisement/rapports/
def rapport_dirigeant(portefeuille, campagne, langue: Langue = Langue.FR) -> str    # two pages, EF-60
def cas_business(projet: Projet, campagne, langue: Langue = Langue.FR) -> str      # EF-61
def registre_conformite(campagne, entrees: Sequence[EntreeRegistre], langue=Langue.FR) -> str  # EF-62
def fiche_processus(processus, gisement, projet, langue=Langue.FR) -> str          # annex D layout
```

The writer **computes nothing** (§21.5): it receives the figures and formats
them. Every report prints the naive/real table of §13.3, the coverage (§17.4),
the interval, and the five prohibitions of §18.5.

```python
# lot 17 - src/gisement/suivi/
def comparer(gain_predit: Decimal, gain_mesure: Decimal) -> SuiviTrimestriel   # EF-63, §17.3
def precision_cumulee(suivis: Sequence[SuiviTrimestriel]) -> PrecisionCumulee  # KPI-6
def parametre_fautif(prediction: Gisement, realise: Decimal) -> str

# lot 18 - src/gisement/api/, stockage/, pipeline.py
def executer(campagne: Campagne, racine: Path = Path("demo/donnees"), *, modele: Modele | None = None,
             graine: int | None = None) -> ResultatCampagne
```

`ResultatCampagne` holds every stage output (corpora, groups, motifs, processes,
gisements, feasibilities, projects, portfolio, advised-against, reviews,
coverage, measured cost, register). The API is FastAPI, routes exactly as §23,
**no route accepts a tenant or a person identifier as a parameter**; the tenant
comes from the token (EF-71) and every measure route goes through
`politique.evaluer` first (R5).

The portal is static (`portal/index.html`, `app.js`, `styles.css`), served by
the API, and shows: the greyed-out Launch button before DPO validation (R1), the
policy refusal (video 1:20), the factor 2.61 table, the three waves, the
"do not automate" list, the measured cost.

---

## 10. Acceptance

`docs/TRACEABILITY.md` maps every EF/ENF/KPI and every R1-R26 test to the lot
that delivers it and the test file that proves it. A lot updates its own rows.
The blocking rows are R5 to R9 (non-attribution and sensitive filtering): one
failure forbids the submission (§27).
