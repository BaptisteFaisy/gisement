# Le jeu de démonstration — « Démo Distribution SAS »

Client **entièrement synthétique** : 120 salariés, distribution spécialisée
B2B, quatre services observés sur six mois. Chaque fichier porte le filigrane
`SYNTHETIQUE - DEMONSTRATION` et ne contient **aucune donnée personnelle
réelle** (ENF-11) : les noms sont des combinaisons de listes fixes, les
adresses sont en `demo.example`.

## Régénérer

```bash
python3 demo/genere.py --sortie demo/donnees     # écrit le corpus
python3 demo/genere.py --verifier                # prouve la reproductibilité
python3 -m gisement.cli generer --verifier       # la même chose via la CLI
```

Graine unique : **20261111** (publiée dans `manifeste.json`). Deux exécutions
donnent des fichiers **identiques octet pour octet** (ENF-08) — c'est ce que
prouve `--verifier` et `tests/unit/demo/test_reproductibilite.py`.

## Ce qui pilote la génération

| Source | Rôle |
|---|---|
| `demo/spec-processus.json` | **La vérité terrain** : les 23 processus, leurs volumes mensuels, durées, coûts, types attendus, les trois pièges. Le générateur ne l'invente pas, il la sert. |
| `catalogue/motifs/*.json` | La phrase canonique de chaque geste (`modele_texte`) : c'est elle qui est écrite dans les enregistrements, ce qui rend la classification mesurable. |
| `demo/moteur.py` | Le plan d'allocation : chaque occurrence de chaque processus est affectée à un canal, dans la limite des volumes nominaux. |
| `demo/canaux_gen.py` | Les cinq schémas d'enregistrements (contrats gelés, `docs/CONTRACTS.md` §5). |
| `demo/procedures.py` | Les huit procédures écrites, volontairement décalées de la pratique. |
| `demo/listes.py` | Noms, sociétés, produits, libellés de bruit, formulations sensibles plantées. |

## Volumes produits (annexe F.2)

| Canal | Volume | Dont bruit hors périmètre |
|---|---|---|
| Tickets | 4 800 | 0 |
| Courriels (échantillon stratifié) | 2 000 | 84 |
| Journaux ERP | 12 400 | 84 |
| Documents | 200 (200 pages) | — |
| Appels | 7 enregistrements, 360 minutes | — |

Les transcriptions d'appels et les extractions de documents sont **figées dans
le dépôt** : aucun appel à Amazon Transcribe ni à Bedrock Data Automation
pendant le développement (règle 1 du §26.4 — ces deux services font 94 % du
coût d'une cartographie).

## Les trois pièges (annexe F.3)

| Piège | Ce qu'il teste | Où le voir |
|---|---|---|
| **P-16 pic saisonnier** | 41 occurrences par mois en médiane, 310 le mois du réassort de fin d'année. La moyenne annoncerait 85, soit un gain double. | `attendus/processus.json` → `occurrences_generees` de P-16 |
| **P-07 procédure divergente** | `procedures/PROC-04.md` décrit un portail EDI que personne n'utilise ; 78 % des commandes arrivent par courriel (fait métier publié), le reste est ressaisi. | `PROC-04.md` et `spec-processus.json` → `part_pratique_divergente` |
| **P-02 fort jugement** | 55 % de cas atypiques : doit tomber en D ou E, jamais en vague 1. | `spec-processus.json` → `part_atypique` |

## Vérités attendues (`attendus/`)

| Fichier | Contenu | Consommé par |
|---|---|---|
| `processus.json` | les 23 processus + les volumes réellement générés | lots 11, 22 (R10) |
| `motifs.json` | 26 motifs implantés avec leurs volumes | lot 22 (rappel des motifs) |
| `activites_etiquetees.json` | 200 activités étiquetées avec leur motif | lot 22 (précision de classification) |
| `sensibles.json` | 100 documents à catégorie sensible plantée | lot 9 (R8, bloquant) |
| `non_attribution.json` | 50 requêtes qui doivent toutes être refusées | lot 12 (R7, bloquant) — **appartient au lot 0, le générateur ne le réécrit pas** |

## Reproduction des coûts (annexe G.3)

360 minutes de transcription et 200 pages d'extraction : ce sont exactement les
volumes qui donnent 8,64 $ + 10,00 $ dans l'annexe G. Le reste du coût
d'une cartographie est l'inférence, mesurée par `gisement.observabilite`.
