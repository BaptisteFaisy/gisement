# Gisement — Devpost submission

**Track 2 — Deliver AI-Driven Outcomes for Customers.**

## Inspiration

A client says "we would like to automate". Nobody knows what. The MSP bills a
scoping study, produces a slide deck, and **80 % of it never happens**. The
reason is not a lack of opportunities - it is the lack of a **credible
measuring instrument** to find them, price them and order them.

A real case: a 120-person retailer automated its customer service on a promised
gain of 3 FTE. Six months and 68 000 € later, the real gain was 0.4 FTE. The
volume had been measured on a peak month, most of the work was actually email
order entry rather than calls, and the human review of the agent's answers had
been forgotten. The CEO never launched another automation project. The MSP lost
the account.

## What it does

Gisement does not read the procedure manual - **it reads the work**: the
tickets, the emails, the documents, the recorded calls, the application logs.
It measures what is manual and repetitive, and delivers a **sequenced portfolio
of automation projects**: for each, the measured volume, the net recoverable
time with its confidence interval, the recommended automation type, the cost,
the payback, the risk, and its place in the sequence. Plus a quarterly follow-up
of **realised against predicted** - which is what triggers the second sale.

Five things a generic submission will not do:

1. **It measures the real work, not the declared work.** The written procedure
   says the order is keyed into the ERP; in practice it arrives by email, is
   copied into a local spreadsheet, re-keyed, then checked by phone. Gisement
   reads the procedure *last*, to publish the gap - and the gap is often the
   most useful finding.
2. **It computes the net gain, not the gross one.** On the reference case the
   naive calculation promises a payback in 5.2 months; the real one is **13.7
   months** - a factor of **2.61**. Every process report prints both columns. A
   client who signs on 5.2 and discovers 13.7 never buys again, and says so.
3. **It sequences, it does not rank.** Ranking by gain sends the client at the
   biggest, riskiest, longest project first - and an initial failure kills the
   programme for years. The deliverable is a wave 1 that is fast, visible and
   safe.
4. **It says no.** Processes that must not be automated are published with the
   reason and the re-examination condition - 15 to 30 % of a healthy portfolio.
   Saying no is what makes the yes credible.
5. **Individual attribution is impossible by construction.** Every published
   measure covers at least five individuals; pseudonymisation happens at
   ingestion before any model sees anything; and the rules are enforced by
   AgentCore Policy at the gateway, **not by a sentence in a prompt**. A tool
   that ranks employees passes neither the works council, nor the DPO, nor the
   judge.

## How we built it

Seven distinct AI services, each irreplaceable: **Amazon Transcribe** makes the
invisible channel (calls) measurable, with diarisation and native PII
redaction; **Bedrock Data Automation** structures the hand-kept documents that
are the main deposit of an SMB; **Amazon Comprehend** applies the
sensitive-category filter at ingestion; **Bedrock Knowledge Bases** carries the
40-motif catalogue; **Bedrock** labels each group of activities; **AgentCore**
(Runtime, Gateway, Identity, Policy, Memory, Observability) isolates the
sessions, derives the tenant from the token, enforces k ≥ 5 at the gateway,
carries the longitudinal follow-up and measures the cost; **Strands** runs the
bounded collectors; **Amazon Quick** renders the portfolio.

The budget lever is a **deterministic fingerprint**: 19 900 activities collapse
into 42 groups, and the model is called once per group, not once per activity -
a factor of ~474, against the ~80 the spec planned. The economic engine is pure
`Decimal` with a 10 000-draw Monte-Carlo at a fixed seed; **a model never
computes a figure**. Everything runs offline against a committed synthetic
corpus, so CI never calls Transcribe or Data Automation (94 % of the cost).

## Challenges we ran into

- **Honesty of the interval.** Annex A publishes a narrow interval and wide
  input distributions that are arithmetically incompatible. We derived the
  Monte-Carlo spreads from the *quality of the measurement* (standard error over
  the window, σ/√n for a measured duration) so the published interval is both
  reproducible and defensible.
- **Non-attribution that cannot be bypassed.** A k ≥ 5 check in the prompt fails
  one time in a thousand. Enforced at the gateway on structured facts, with a
  fail-closed default (a measure whose group size is unknown is refused), the 50
  probing requests are all refused - including the 18 that combine filters.
- **The type A recommendation.** Removing a step is not automating it: it
  carries no transfer and no ineliminable share. Modelling that (annex A.7) is
  what lets Gisement recommend the 1 950 € EDI move that deletes 78 % of the
  volume, instead of the 40 000 € email-reading agent.

## Accomplishments

- 432 offline tests green; CI verdict in under 5 minutes.
- The engine reproduces annex A **to the cent** (18.4 h, 772.80 €, 13.7 months,
  factor 2.61) and the 23 processes of the ground truth with zero discrepancy.
- The 50 non-attribution requests are all refused (the blocking criterion).
- The 100 planted sensitive documents are all dropped before storage.
- The demo pipeline detects 22 of 23 processes from the corpus (the 23rd, a
  quarterly board reporting, is published as declared-by-interview, invisible to
  the logs - which is itself an honest result).
- One mapping measures at 18.82 $ against the 19.77 $ estimate (R24, < 25 %).

## What we learned

An instrument that always finds something to automate is a sales tool, not an
instrument. The credibility of Gisement rests on what it **refuses**: the
processes it advises against, the intervals it publishes instead of point
estimates, the coverage it does not hide, and the individual attribution it
makes technically impossible. Saying no is what makes the yes sell.

## What's next

The quarterly follow-up accumulates a base of realised-against-predicted that,
after eight quarters, becomes an asset nobody can copy - and the anonymised
cross-client comparison (from five clients of similar size) turns one mapping
into a benchmark. The mapping is sold at cost; the portfolio of projects it
produces is the real product.
