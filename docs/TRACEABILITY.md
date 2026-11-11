# TRACEABILITY — requirement → lot → proof

Each lot updates its own rows when it delivers. A row without a test file is a
row that is not delivered. Blocking rows (R5 to R9) stop the submission: one
failure on the 50 non-attribution requests forbids it (§27).

## Functional acceptance (§33.2)

| # | Test | Expected | Lot | Proof |
|---|---|---|---|---|
| R1 | Launch a campaign without DPO validation | Explicit refusal, button greyed out, no ingestion | 18 | `tests/integration/test_conformite.py` |
| R2 | Compute the annex A reference case | 18.4 net hours, 772.80 €/month, 13.7 months, to the cent | 1 | `tests/unit/calcul/test_annexe_a.py` |
| R3 | Check the gap to the naive calculation | Factor 2.61 published | 1 | `tests/unit/calcul/test_annexe_a.py` |
| R4 | Two runs at the same seed | Strictly identical intervals | 1 | `tests/unit/calcul/test_monte_carlo.py` |
| R5 | Ask for a measure per employee | **Policy refusal, k ≥ 5 rule** | 12 | `tests/unit/politique/test_refus.py` |
| R6 | Isolate an individual by combining filters | Refusal, rare quasi-identifiers withdrawn | 12 | `tests/unit/politique/test_combinaisons.py` |
| R7 | 50 varied non-attribution requests | 50 refusals — **blocking** | 12, 22 | `eval/non_attribution.py`, `tests/unit/politique/test_50_requetes.py` |
| R8 | Ingest 100 documents with planted sensitive categories | 100 filtered before storage | 9, 22 | `tests/unit/assainissement/test_sensibles.py` |
| R9 | Check the pseudonymisation | No direct identifier in the sanitised corpora | 9 | `tests/unit/assainissement/test_pseudonymisation.py` |
| R10 | Detect the 23 processes of the demo | 23 detected, the 3 traps handled correctly | 11 | `tests/integration/test_jeu_demo.py` |
| R11 | Seasonal process measured on a peak month | Median used, amplitude published | 1, 11 | `tests/unit/calcul/test_saisonnalite.py` |
| R12 | Process whose written procedure diverges | Gap displayed explicitly | 11 | `tests/unit/processus/test_ecart_procedure.py` |
| R13 | High judgement process | Classified D or E with a reason | 13 | `tests/unit/test_faisabilite.py` |
| R14 | Check the published coverage | 62 %, with the list of what is not covered | 8 | `tests/unit/test_couverture.py` |
| R15 | 10 processes below the volume threshold | 10 in category E with a re-examination condition | 15 | `tests/unit/test_deconseil.py` |
| R16 | Share of category E | Between 15 and 30 % of the portfolio | 15 | `tests/unit/test_deconseil.py` |
| R17 | Check the sequence | Wave 1 does not contain the biggest gain; at least one project paying back in < 6 months | 14 | `tests/unit/test_sequenceur.py` |
| R18 | No wave 1 project possible | Recommendation to widen the scope, no fake wave 1 | 14 | `tests/unit/test_sequenceur.py` |
| R19 | Record a realised quarter | Gap published, faulty parameter identified if > 15 % | 17 | `tests/unit/suivi/test_realise_predite.py` |
| R20 | Suspend a running campaign | Stop < 5 s, state kept, resumption possible | 12, 18 | `tests/integration/test_suspension.py` |
| R21 | Client A tries to read the data of B | Refusal, logged | 12, 18 | `tests/unit/politique/test_tenant.py` |
| R22 | Export the report in English | Complete report, aggregated citations, no identifier | 16 | `tests/unit/rapports/test_anglais.py` |
| R23 | Generate the compliance register | Every element of §24.4 present | 16 | `tests/unit/rapports/test_registre.py` |
| R24 | Read the measured cost | Gap < 25 % with annex G | 20 | `tests/unit/observabilite/test_cout.py` |
| R25 | Add a motif to the catalogue as data | Recognised without a code change | 2 | `tests/unit/motifs/test_catalogue.py` |
| R26 | Purge a campaign | Corpora destroyed, proof, aggregates kept for the follow-up | 18 | `tests/integration/test_purge.py` |

## Functional requirements (§12)

| Group | Requirements | Lot |
|---|---|---|
| Scope and compliance | EF-01 … EF-05 | 18 (registry), 12 (enforcement) |
| Ingestion | EF-10 … EF-16 | 4, 5, 6, 7, 8, 9 |
| Detection and measure | EF-20 … EF-25 | 10, 11 |
| Economic model | EF-30 … EF-35 | 1 |
| Ranking and sequence | EF-40 … EF-44 | 13, 14, 15 |
| Privacy | EF-50 … EF-53 | 12 |
| Deliverables and follow-up | EF-60 … EF-65 | 16, 17 |
| Multi-client | EF-70 … EF-72 | 18, 20 |

## Non functional requirements (§19)

| Requirement | Lot | Proof |
|---|---|---|
| ENF-01 … ENF-05 (no ingestion without validation, pseudonymisation, k ≥ 5 at the gateway, no identifier in any output, sensitive filter) | 9, 12, 18 | R1, R5, R7, R8, R9 |
| ENF-06, ENF-07 (bounded retention with proven purge, full access log) | 18, 12 | R26, `tests/unit/politique/test_journal.py` |
| ENF-08 (reproducibility) | 0, 1, 3 | R4, `tests/unit/demo/test_reproductibilite.py` |
| ENF-09, ENF-10 (bounded budget, measured cost) | 20 | R24 |
| ENF-11 (no real personal data in the demo) | 3 | `tests/unit/demo/test_synthetic.py` |
| ENF-12 (suspension in < 5 s) | 12, 18 | R20 |
| ENF-13 (`Decimal`, never a float, never a model) | 1 | R2, `tests/unit/calcul/test_decimal.py` |
| ENF-14 (reports in French and English) | 16 | R22 |
| ENF-15 (< 500 lines, < 50 per function, CI ≤ 5 min) | 0 | `scripts/check_limits.py`, `.github/ci-budget/` |
| ENF-16 (reproducible IaC deployment) | 21 | `docs/RUNBOOK.md` |
| ENF-17 (stays online free until 22 January 2027) | 21 | `docs/RUNBOOK.md` |
| ENF-18 (one mapping in < 4 h of compute) | 18, 20 | `tests/perf/test_duree_campagne.py` |

## Indicators (§5.2)

| KPI | Where it is produced | Lot |
|---|---|---|
| KPI-1 manual hours identified | executive report, portfolio | 16 |
| KPI-2 net automatable euros, with interval | `calcul`, report | 1, 16 |
| KPI-3 coverage of the measure | `couverture`, report | 8, 16 |
| KPI-4 gap to the naive calculation (2.61) | `calcul.ecart_naif` | 1 |
| KPI-5 median payback delay | `sequenceur`, Quick | 14, 19 |
| KPI-6 prediction accuracy (< 25 %) | `suivi` | 17 |
| KPI-7 projects triggered | portal, account manager view | 18 |
| KPI-8 cost per mapping (≤ 20 $) | `observabilite` | 20 |
| KPI-9 processes advised against (≥ 15 %) | `deconseil` | 15 |
