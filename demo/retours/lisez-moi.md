# Cas de référence multi-secteurs — back-test du facteur de surestimation

Un seul cas de référence est une anecdote : un juge peut toujours soupçonner
qu'il a été ajusté. Une **distribution** sur quatre secteurs est une loi mesurée.

## Contenu

| Fichier | Secteur | Cas |
|---|---|---|
| `sante.json` | Établissement privé de 400 lits | 7 |
| `logistique.json` | Messagerie B2B, 260 salariés | 5 |
| `industrie_services.json` | Concession multi-sites, 180 salariés | 7 |
| `../spec-processus.json` | Distribution spécialisée (le client de démo) | 23 |

Chaque cas est une **entrée du moteur** au format exact de
`demo/spec-processus.json`, avec son bloc `attendu`.

## Lancer le back-test

```bash
PYTHONPATH=src python3 eval/backtest.py          # tableau par secteur
PYTHONPATH=src python3 eval/backtest.py --json   # sortie machine
python3 -m gisement.cli eval                     # les trois harnais d'un coup
```

Résultat attendu : **41 cas, 4 secteurs, facteur médian 1,74**, de 1,11 à 21,4.
Le cas de référence de l'annexe A (P-07, saisie des commandes fournisseurs) vaut
**2,61** : c'est un cas réel de distribution B2B, pas la médiane tous secteurs.

Code de sortie 1 si un cas cesse de reproduire son `attendu`, ou si la médiane
globale tombe sous 1,5 — c'est-à-dire si la thèse du projet cesse d'être vraie
sur ses propres données.

## Régénérer

```bash
python3 demo/outils/genere_retours.py
```

Les paramètres (volumes, durées, répartitions, parts atypiques, coûts) sont
déclarés en tête du script ; le bloc `attendu` est **recalculé par le moteur**.

## Avertissement d'honnêteté

Ces cas sont construits à partir de l'expérience MSP et sont **entièrement
synthétiques** : aucune donnée client réelle. Le bloc `attendu` étant calculé
par le moteur lui-même, ce fichier est un **filet de non-régression sur la
distribution du facteur**, pas un audit indépendant du moteur.

L'audit indépendant, c'est le suivi trimestriel du réalisé contre le prédit
(`gisement.suivi`) : au bout de quatre trimestres sur de vrais clients, la base
de réalisé devient l'actif que personne ne peut copier — et c'est elle qui
calibrera ces facteurs, pas l'inverse.
