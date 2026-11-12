# Les dix idées « aller plus loin » — où elles ont atterri

Demandées le 12 novembre 2026, livrées le même jour, toutes hors-ligne et
testées. Chaque ligne pointe le code qui la réalise.

| # | Idée | Livrée dans | Preuve |
|---|---|---|---|
| 1 | Déployer la stack CDK + URL live | `iac/` (50 ressources, synthétise sans warning), `scripts/deploy.sh`, `src/gisement/lambdas/` | `cdk synth` ; le déploiement réel demande un compte AWS |
| 2 | Vraie syntaxe AgentCore Policy | `politique/cedar.py` (Cedar), `lambdas/intercepteur.py` (intercepteur REQUEST), `iac` (PolicyEngine + Policy + Gateway + Memory) | `tests/unit/politique/test_cedar.py`, `tests/unit/intercepteur/` |
| 3 | Vidéo de 3 min | `media/demo-refus-k5.gif`, `media/refus-k5.png`, portail rejouable `#demo=N`, `docs/VIDEO.md` | captures reproductibles en headless |
| 4 | Suivi longitudinal comme produit | `suivi/calibration.py` (auto-calibration bornée), `suivi/alertes.py` (dérive), `suivi/base.py` | `tests/unit/suivi/` |
| 5 | Banque de motifs vivante | `motif_banque.py`, `commands/motif.py` | `tests/unit/motif_banque/` ; `gisement motif propositions` |
| 6 | Back-test du facteur multi-secteurs | `demo/retours/*.json` (19 cas), `eval/backtest.py` | 41 cas, 4 secteurs, médiane 1,74 ; exit 1 si < 1,5 |
| 7 | Preuve zero-knowledge / DP | `privacy/bruit.py` (Laplace opt-in), `privacy/preuve.py` (certificat chaîné vérifiable) | `tests/unit/privacy/` |
| 8 | Connecteurs ERP/ITSM réels | `connecteurs/{jira,servicenow,sage}.py` | `tests/unit/connecteurs/`, sans réseau |
| 9 | Séquenceur sous contrainte de capacité | `planification.py` (capacité, dépendances, chemin critique, Gantt) | `tests/unit/planification/` |
| 10 | Rapport PDF + proposition commerciale | `rapports/pdf.py` (writer PDF stdlib), `commands/proposition.py` | `tests/unit/rapports/` ; `gisement proposition --pdf` |

## Ce que chaque idée change pour le jugement

- **1 et 2** transforment l'argument « la non-attribution est imposée par la
  passerelle » d'une promesse en un artefact déployable : la politique Cedar est
  générée par le même registre que le moteur testé hors-ligne, et l'intercepteur
  REQUEST refuse avant que l'outil ne tourne. C'est le critère *Technological
  Implementation*.
- **6** répond à l'objection « votre facteur 2,61 est arrangé » : c'est une
  distribution sur 41 cas et 4 secteurs, avec un harnais qui casse si la thèse ne
  tient plus.
- **4 et 5** construisent le fossé défensif : la base réalisé-contre-prédit qui
  calibre le moteur, et le catalogue qui grandit sans code.
- **7** pousse le différenciateur juridique au niveau que aucun concurrent
  n'atteindra : une preuve vérifiable sans divulgation.
- **9 et 10** font passer l'outil du rapport au pilotage : un plan daté sous
  contrainte de consultants, et le document que le MSP envoie pour signer.

## Ce qui reste humain

La vidéo narrée (une voix, un micro) et le déploiement AWS (un compte, des
crédits). Tout le reste est dans le dépôt, vert, hors-ligne.
