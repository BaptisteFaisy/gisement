# Test instructions — how a judge reproduces Gisement

Everything below runs **offline**, with no AWS account, no credential and no
network. Python 3.12+ and the dev dependencies are the only requirements.

## 0. Install

```bash
git clone https://github.com/BaptisteFaisy/gisement && cd gisement
python3 -m pip install --user -e ".[dev]"
```

## 1. The one-command proof

```bash
make all      # ruff + size guard (<500 lines, <50 per function) + 432 offline tests
make smoke    # the whole pipeline on the frozen demo corpus
```

`make smoke` prints, in a few seconds:

- 19 900 activities collapsed into 42 fingerprint groups (the budget lever);
- the **published coverage: 62 %** of the estimated work volume, with the list
  of what is not covered (R14);
- the **net annual deposit** and the **six processes advised against (26 %)**,
  each with its reason and its re-examination condition (R16, KPI-9);
- the **three waves**, wave 1 leading with P-07 and P-14 - fast, safe, visible -
  and *not* with the biggest gain (R17);
- the **reference factor**: the naive calculation announces 2 016 €/month, the
  engine publishes ~779 €/month, a factor of ~2.6 (KPI-4, R2/R3).

## 2. The three moments that matter

### 2.1 The engine reproduces annex A to the cent (R2, R3)

```bash
python3 -m pytest tests/unit/calcul/test_annexe_a.py -v
```

48.0 gross hours → 18.4 net hours, 772.80 €/month, 13.7-month payback, factor
**2.61**, naive payback 5.2 months. Exact, in `Decimal`.

### 2.2 Non-attribution is enforced by the gateway (R5, R6, R7 — blocking)

```bash
PYTHONPATH=src python3 eval/non_attribution.py     # exit 0 = 50/50 refused
python3 -m pytest tests/unit/politique -v
```

The 50 requests of `demo/donnees/attendus/non_attribution.json` are **all
refused**, 18 of them attempts to isolate an individual by combining filters.
A single miss forbids the submission (spec 27).

### 2.3 The sensitive filter drops before storage (R8)

```bash
python3 -m pytest tests/unit/canaux/test_documents.py -v
```

200 documents in, **100 dropped** - the ones carrying a planted sensitive
category (health, union, political, religious, sexual life, ethnic origin,
genetics), using indirect wordings so a naive keyword filter would miss them.

### 2.4 The overstatement factor is a distribution, not an anecdote (D-24)

```bash
PYTHONPATH=src python3 eval/backtest.py
```

41 cases across 4 sectors: median factor 1.74, range 1.11 to 21.4, and every
case reproduces its expected figures to the cent. Exit code 1 if the global
median falls under 1.5 - the harness fails when the thesis stops holding.

`python3 -m gisement.cli eval` runs the three harnesses at once: classification
accuracy (100 % on 200 labelled activities), the 50 non-attribution refusals,
and this back-test.

## 3. Reproducibility (ENF-08)

```bash
python3 demo/genere.py --verifier    # regenerates and compares, byte for byte
```

The demo client is generated from one seed (20261111); two runs give identical
files. The Monte-Carlo intervals are identical at a fixed seed too (R4):

```bash
python3 -m pytest tests/unit/calcul/test_monte_carlo.py -v
```

## 4. The reports (EF-60, EF-62, EF-65)

```bash
python3 -m gisement.cli rapport --langue fr --sortie /tmp/rapports
python3 -m gisement.cli rapport --langue en --sortie /tmp/rapports
```

Executive report, business cases and compliance register, in French and
English. The writer computes nothing: it formats the figures the engine
produced (21.5).

## 5. The catalogue is data, not code (R25)

```bash
python3 -m pytest tests/unit/motifs/test_catalogue.py -v
```

One test drops a 41st motif into a temp directory: the loader picks it up,
matches it, and the validator reports the count drift - all without a line of
code.

## 6. What is *not* exercised offline

The real AWS adapters exist and are unit-tested with fakes, but no test calls
Amazon Transcribe, Bedrock Data Automation, Comprehend, Bedrock or AgentCore
(rule 1 of 26.4: they are 94 % of the cost). The frozen transcripts and
extractions in `demo/donnees/` stand in for them. The measured cost of a
mapping on the demo volumes is 18.82 $, against the annex G estimate of 19.77 $
- a 4.8 % gap, inside the 25 % of R24:

```bash
python3 -m pytest tests/unit -k observabilite -v
```

## 7. Traceability

`docs/TRACEABILITY.md` maps every EF/ENF/KPI and every acceptance test R1-R26
to the lot that delivers it and the test file that proves it.
