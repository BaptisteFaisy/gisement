# High-Level Design — Gisement

## 1. What the system does

A client says "we would like to automate"; nobody knows what. Gisement observes
the **real** work - tickets, emails, documents, recorded calls, application
logs - measures what is manual and repetitive, and delivers a **sequenced
portfolio** of automation projects with honest figures, intervals, and an
explicit list of what *not* to automate.

Three failures of the classical scoping study drive the design:

1. It maps the **declared** process, not the real one. Gisement reads the work,
   and reads the written procedure only last, to measure the gap (9.1).
2. It computes the **gross** gain, which is wrong. On the reference case the
   naive calculation promises a payback in 5.2 months; the real one is 13.7 -
   a factor of **2.61** (annex A).
3. It ranks by gain, not by **sequence**. The biggest deposit is the riskiest;
   starting there kills the programme. The deliverable is a wave 1 that is fast,
   visible and safe.

Plus one constraint most tools ignore and that is **architectural** here: the
system observes employees, so it can never attribute work to a named person.
Every measure is aggregated above k ≥ 5, pseudonymised at ingestion before any
model sees it, and the rules are enforced by AgentCore Policy at the gateway -
not written in a prompt.

## 2. Components

```
canaux/         five collectors (tickets, courriels, documents, appels, journaux)
                + commun.py: one read/sanitise/fingerprint/measure behaviour
assainissement/ pseudonymisation (HMAC, non-reversible) + sensitive filter (7 categories)
classifieur/    deterministic fingerprint grouping, then one model call per group
motifs/         the 40-motif catalogue, as data (annex B)
processus/      aggregation of motifs into declared processes + procedure gap
calcul/         the economic engine: Decimal, four corrections, Monte-Carlo
faisabilite.py  the decision tree of the five automation types (A..E)
deconseil.py    category E: the six reasons not to automate, with re-examination
sequenceur.py   three waves, priority score, caps from config/priorite.json
rapports/       executive report, business cases, compliance register (FR + EN)
suivi.py        realised against predicted, per quarter (KPI-6)
politique/      the gateway policy: k >= 5, non-attribution, AgentCore artefact
observabilite.py measured cost per campaign (KPI-8)
pipeline.py     the end-to-end orchestration
api/, portal/   FastAPI + static portal (the deployed URL)
```

Each lot owns disjoint files (see `docs/CONTRACTS.md` §1); no lot edits another's.

## 3. The economic model (chapter 13)

The naive calculation is `occurrences × duration × hourly rate`. Four
corrections make it honest:

| Correction | What it removes | Source |
|---|---|---|
| **Fragmentation** | time too scattered to be reused (0.45 to 0.90 by spread) | measured from the hourly distribution |
| **Transfer** | the work moved to reviewing the automation | measured rate, or a prudent 20 % default |
| **Ineliminable** | the share needing judgement or a signature | measured share of atypical cases |
| **Variability** | a peak month taken for a monthly volume | the **median** of the window, amplitude published |

```
temps_brut         = occurrences_mediane × durée / 60        (× part_volume_traitee)
temps_fragmenté    = temps_brut × coefficient_fragmentation
temps_transféré    = Σ composantes (revue, rejets, supervision)   (0 if the step is removed)
temps_inéliminable = temps_brut × part_atypique                   (0 if the step is removed)
temps_net          = max(0, fragmenté − transféré − inéliminable)
gain_mensuel       = temps_net × taux_horaire_chargé
délai_retour       = coût_année_1 / gain_mensuel
écart_au_naïf      = gain_naif / gain_net                       (KPI-4)
```

All of it in `Decimal`, computed by code - **a model never computes a figure**
(EF-35). The interval is a Monte-Carlo of 10 000 draws at a fixed seed, with
spreads derived from the quality of the measurement (standard error over the
window for the volumes, σ/√n for a measured duration, ±40 % for an inferred
one). Two runs give strictly identical intervals (R4).

The factor is a **distribution, not a constant** (D-24): `eval/backtest.py`
measures it on 41 cases across four sectors - the demo retailer, a private
hospital, a B2B carrier, a multi-site service dealer - with a median of 1.74 and
a range of 1.11 to 21.4. The 2.61 of annex A is the reference case, labelled as
such. The harness fails if the global median drops under 1.5, i.e. if the thesis
stops holding on its own data.

A **type A action** - removing the step instead of automating it - carries
neither transfer nor ineliminable share, because there is no automated output
left to review (annex A.7, decision D-11). That is why recommending A first is
not a slogan: on P-07 it gives 1 102.50 €/month for 1 950 € invested, a 1.8-month
payback, against the 13.7 months of the automation it replaces.

## 4. Classification without blowing the budget (chapter 21.2)

Two passes:

1. **Deterministic fingerprint** - each activity is reduced to a signature
   (verb, objects, systems). Identical signatures group without a model. On the
   demo corpus, 19 900 activities collapse into 42 groups: a factor of 474.
2. **Model labelling** - Bedrock labels each *group* against the catalogue in
   Knowledge Bases, with a confidence and a citation. Below the threshold, the
   group goes to human review; a group that matches nothing becomes a proposed
   motif (EF-21).

This is the single most important cost decision (annex G.1): without it, 7 000
items would be classified individually, ~18× more expensive.

## 5. Privacy as architecture (chapter 18)

Five hard rules, enforced by the gateway before the tool runs:

| Rule | Enforcement |
|---|---|
| **R1** no individual attribution | groupings and filters naming a person are refused; no output carries an individual ranking, score or time |
| **R2** k ≥ 5 aggregation | a measure over fewer than five individuals is suppressed, not rounded; the threshold can be raised, never lowered |
| **R3** pseudonymisation at ingestion | HMAC-SHA256, non-reversible without the key; the mapping table is separate, encrypted, destroyed at the end |
| **R4** sensitive-category filter | health, union, political, religious, sexual life, ethnic origin, genetics - dropped before storage |
| **R5** enforced by the gateway | AgentCore Policy, on structured facts, never a sentence in a prompt |

Re-identification by combined filters is blocked too: filters are evaluated
*after* application, rare quasi-identifiers are withdrawn from the filter list,
and the number of requests per user is bounded and logged. The 50 requests of
R7 are all refused - it is the only blocking acceptance criterion.

## 6. Data model (chapter 22)

`tenants`, `campagnes`, `conformite`, `corpus`, `activites`, `motifs`,
`processus`, `gisements`, `faisabilite`, `projets`, `deconseilles`, `suivi`,
`registre`. Integrity rules: no activity carries a person identifier (the
column is `groupe_pseudonyme`); any query producing a group < 5 is refused at
execution; `gisements` and `projets` are written only by `calcul/`; `suivi` is
append-only; `registre` is hash-chained; every read goes through the tenant
derived from the token.

## 7. Multi-tenant

Tenants are strictly isolated (EF-70); the tenant is derived from the token,
never from a parameter or free text (EF-71); the cost is bounded per tenant and
exposed to the account manager (EF-72). No route accepts a tenant or a person
identifier.

## 8. Cost discipline (chapter 26)

One mapping costs ~20 $: Transcribe (360 min) and Data Automation (200 pages)
are 94 % of it; inference is 6 %. Consequences: development and CI run on
frozen transcripts and extractions (no Transcribe, no BDA); the four full
mappings are reserved for the demo; audio is capped at 6 h, documents at 200
pages; the token budget is capped per campaign with a clean stop (ENF-09); the
measured cost is exposed from the first run (KPI-8).

## 9. Key design decisions

See `docs/DECISIONS.md` (D-01 to D-20). The load-bearing ones:

- **D-01** the ineliminable share is on gross time (annex A wins over a formula line).
- **D-02/D-14/D-18** Monte-Carlo spreads derived from measurement quality, reproducing annex A.6.
- **D-09** the AgentCore Policy artefact is generated from the same registry the engine enforces.
- **D-11** a type A action carries no transfer and no ineliminable share.
- **D-16** projects that do not fit the wave caps are published in a ranked reserve.
- **D-19** the demo generator is Python: one language, no npm step in a 5-minute CI.

## 10. What is deliberately limited

Emails are sampled (1 500 to 3 000, stratified, seeded); calls are only those
already recorded and consented to; the catalogue is 40 motifs, not 300; five
channels, not more - each added channel raises the cost and the legal risk
faster than it improves the precision.
