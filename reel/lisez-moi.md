# Le corpus réel

Ce dossier contient le **corpus réel** du produit : Apache Kafka (ASF), lu sur
des systèmes publics par de vrais connecteurs.

- `donnees/` — les artefacts **assainis** (pseudonymisés à l'ingestion) : ce
  sont eux que la mesure lit, que la CI vérifie et que le portail publie.
- `brut/` — les téléchargements bruts : **jamais commités, jamais publiés**
  (voir `.gitignore`). Leur empreinte SHA-256 est dans `brut/provenance.json`.
- `modele/` — les réponses **réellement produites par un modèle réel** sur les
  preuves réelles, et leur rejeu hors ligne.
- `resultats/` — la mesure sérialisée : régénérable, pas commitée.

Le détail (sources, licences, vie privée, les neuf résultats mesurés sur le
corpus réel) est dans `docs/REEL.md`.

```bash
python3 -m reel.manifeste       # lit les artefacts, écrit le manifeste
python3 -m reel.declaration     # le perimetre declare, depuis les artefacts
python3 -m reel.corpus          # la mesure, avec le rejeu des reponses
```
