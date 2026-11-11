# Video — 3-minute submission script

English, YouTube public, 3 minutes. The video **starts on the ingestion**, not
on the report: the risk is that a judge reads this as "consulting", and the
answer is to show the machine measuring first (risk table, spec 32).

The three moments that win are at 1:20 (the Policy refusal), 1:32 (the factor
2.61) and 2:05 (the "do not automate"). They are marked **[KEY]**.

| Time | Screen | What happens | Command / cue |
|---|---|---|---|
| 0:00 | Terminal | "The client wants to automate. Nobody knows what." The perimeter is declared: 4 services, 6 months. | `gisement smoke` header |
| 0:12 | Portal | The DPO validation is recorded. Without it the **Launch** button is greyed out - shown on screen. | portal, R1 |
| 0:22 | Terminal | The five channels scroll; pseudonymisation is shown; the sensitive filter counts the exclusions (100 documents dropped). | collectors + R8 |
| 0:40 | Report | "**62 %** of the estimated work volume" - published, not hidden, with the list of what is not covered. | `ligne_publication`, R14 |
| 0:50 | Terminal | 42 groups from 19 900 activities; 40 catalogue motifs recognised; new motifs proposed. | classifier, annex G.1 |
| 1:05 | Portal | 23 processes aggregated, one where **the written procedure and the practice diverge** - the gap is displayed (PROC-04, 78 %). | EF-25, R12 |
| 1:20 | Portal | **[KEY]** A "per employee" request is attempted → **Policy refusal, rule k ≥ 5**, shown on screen with the logged rule. | `eval/non_attribution.py`, R5 |
| 1:32 | Report | **[KEY]** Supplier order entry: the naive calculation announces 2 016 €/month, Gisement publishes **772.80 €**. Factor **2.61**. The four-correction table is displayed. | annex A, KPI-4 |
| 1:50 | Portal | The wave 1 is **not** the biggest deposit: 2 projects with a payback < 6 months, one of them a type A at 0 € of build. | sequencer, R17 |
| 2:05 | Report | **[KEY]** 6 processes in category E, with reason and re-examination condition. "Do not automate" is printed in clear. | `deconseil`, R16 |
| 2:20 | Report | Two pages for the executive, the exportable business case, the compliance register. | `gisement rapport` |
| 2:35 | Portal | Jump 3 months: realised against predicted, 11 % gap, cumulative accuracy published. | `suivi`, KPI-6 |
| 2:50 | Quick | Portfolio view: 23 processes, 3 waves, 78 000-104 000 € net deposit, the measured cost of the campaign. | Amazon Quick |

## Recording notes

- Capture the terminal at 1080p, the portal in Chromium. English subtitles
  burned in (the submission is in English).
- The **[KEY]** moments get a 2-second freeze and a caption, because they are
  the three things a generic submission will not show.
- At 1:20, show the actual refusal object: `regle_k5`, the French message, and
  the log line. This is the proof the protection is technical, not declarative.
- At 1:32, show the four corrections one by one (fragmentation 0.70, transfer
  8.0 h, ineliminable 7.2 h) so the factor 2.61 is seen as a computation, not a
  claim.
- Keep the whole thing under 3:00; the script above is timed to ~2:55.

## Reproduce every screen offline

```bash
make smoke                                  # 0:00, 0:22, 0:50
python3 -m gisement.cli rapport --langue en # 0:40, 1:32, 2:05, 2:20
PYTHONPATH=src python3 eval/non_attribution.py   # 1:20
python3 -m pytest tests/unit/canaux/test_documents.py -v  # 0:22 (100 dropped)
```

The portal screens (0:12, 1:05, 1:50, 2:35, 2:50) are the static portal served
by the API; see `docs/RUNBOOK.md` to run it locally.
