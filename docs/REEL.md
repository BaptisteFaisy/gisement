# Le corpus réel — Apache Kafka (ASF)

Ce document décrit le second corpus du produit : **un vrai client**, lu par de
**vrais connecteurs**, sur de **vraies données publiques**. Tout ce qui suit est
mesuré sur ce corpus ; rien n'y est simulé, et ce qui n'a pas pu être mesuré est
dit comme tel.

| | |
|---|---|
| Client | Apache Kafka, projet de l'Apache Software Foundation |
| Tenant | `T-KAFKA` — campagne `CMP-REEL-0001` |
| Fenêtre réelle | 2025-05-01 → 2025-10-31 (6 mois) |
| Enregistrements réels | 3 707 (1 384 tickets, 2 206 courriels, 117 documents) |
| Périmètre déclaré | 12 processus réels, aucune vérité terrain |
| Mesure | 8 processus mesurés, 4 déclarés invisibles |
| Couverture publiée | 96,2 % du dénominateur publié |
| Licence des données | Apache License 2.0 (projet public ASF), archives publiques |

## 1. Les sources, et ce qu'elles sont vraiment

| Canal | Source réelle | URL | Ce que la mesure en tire |
|---|---|---|---|
| tickets | Jira de l'ASF (API v2 serveur) | `issues.apache.org/jira` | 194 tickets résolus **avec** composant |
| tickets | GitHub Issues du miroir `apache/kafka` | `api.github.com` | 1 190 tickets et pull requests |
| courriels | Archives Pony Mail de `dev@kafka.apache.org` | `lists.apache.org/api/mbox.lua` | 2 706 messages réels, 1 260 fils |
| documents | Confluence public ASF, espace KAFKA | `cwiki.apache.org/confluence` | 120 KIP (documents de conception) |

Deux canaux sont **déclarés absents**, pas simulés : les appels (aucun
enregistrement public ; Transcribe exige des identifiants AWS) et les journaux
d'exploitation (les journaux publics du projet sont des journaux de compilation :
ils décrivent la machine, pas le geste).

Le téléchargement brut est conservé dans `reel/brut/` — **jamais commité,
jamais servi par le portail**. Seuls les artefacts assainis sont publiés, avec
l'empreinte SHA-256 du brut dans `reel/brut/provenance.json`.

## 2. La vie privée, mesurée

| Mesure | Valeur réelle |
|---|---|
| Identités réelles retirées des champs structurés | 1 177 (Jira) + 204 (courriels) + 63 (auteurs de KIP) |
| Pseudonymes appliqués (HMAC-SHA256 tronqué, irréversible) | 11 114 |
| Enregistrements écartés par le détecteur de catégories sensibles | 23 tickets, 494 courriels, 3 documents |
| Adresses e-mail résiduelles dans les artefacts publiés | **0** |

Le pseudonymisation est appliquée **dans le collecteur**, avant tout traitement
(R3, ENF-02) : les identités réelles lues dans les champs structurés sont
retirées du texte libre avec le même pseudonyme. Un défaut a été trouvé et
corrigé en route : les `Message-ID` de la liste portaient une adresse gmail
dans 2 049 enregistrements — ils sont désormais remplacés par une empreinte
déterministe (le fil de discussion survit, l'identité non).

## 3. Ce que le corpus réel a appris au produit

Neuf résultats mesurés, tous reproductibles hors ligne :

1. **Le catalogue ne couvrait rien.** Les 40 motifs du catalogue sont des gestes
   de back-office (ressaisie, rapprochement, relance, reporting). Sur les 12
   périmètres réels d'un projet d'ingénierie logicielle, un modèle réel n'en a
   retenu **aucun**. Douze motifs ont alors été ajoutés au catalogue **comme
   données** (`catalogue/motifs/ingenierie.json`), à partir des groupes réels
   observés — la boucle de validation du catalogue (EF-21, R25) jouée pour de
   vrai.
2. **L'empreinte ne regroupe pas le texte libre.** Sur le corpus de démo
   (sujets gabarits), 3 700 activités donnaient 60 groupes. Sur le corpus réel,
   3 684 activités donnent **2 332 groupes** : 1,6 activité par groupe. Le
   nombre de mots-objets de la signature a été recalibré (2 au lieu de 6) et
   **63 % du volume reste en revue humaine** — c'est la règle du produit, elle
   n'a pas été contournée.
3. **Les en-têtes MIME rendaient le texte illisible.** Sans décodage, 100 % des
   sujets de la liste de diffusion étaient illisibles (`=?UTF-8?Q?...?=`), donc
   aucun geste reconnu. Après décodage : 67 % des groupes ont un verbe reconnu.
4. **Un vrai bug d'agrégation.** La mesure rattachait à chaque processus un
   seul groupe (motif, service) — invisible sur la démo, où il n'y en a qu'un.
   Sur le corpus réel, la médiane était donc zéro pour 10 processus sur 12. Les
   groupes d'un même (motif, service) sont désormais **sommés**
   (`src/gisement/processus/agregation.py`).
5. **Le détecteur de catégories sensibles se trompe.** 18 % des courriels réels
   ont été écartés, presque tous à cause du mot « vote », qui appartient au
   lexique de l'opinion politique — alors qu'un vote de gouvernance Apache est
   du travail réel. Le taux de faux positifs est publié tel quel ; le lexique
   n'a pas été arrangé pour faire joli.
6. **Personne ne mesure le temps de travail.** Ni Jira (`timespent` est vide)
   ni GitHub ne horodatent le travail. Les durées sont donc **inférées** du
   catalogue versionné et marquées comme telles ; le délai réel de résolution
   (médiane 5,17 jours sur les tickets) est publié comme un **délai**.
7. **Le gain du produit ne s'applique pas à ce client.** Le gain se calcule sur
   l'étape supprimée : or aucun geste d'ingénierie logicielle ne fait
   disparaître sa cause. Les 12 processus sont donc **déconseillés**, avec la
   raison. C'est la bonne réponse pour ce client, et la limite réelle du modèle
   économique du produit.
8. **L'empreinte des réalisateurs est plus grossière que prévu.** Les objets
   retenus sont les mots *alphabétiquement* premiers du sujet : ils sont peu
   discriminants sur du texte libre.
9. **Le coût d'une ingestion réelle est mesuré** : 3 707 enregistrements, six
   requêtes par minute au maximum, 0 € de modèle facturé (la classification
   réelle porte sur les 12 plus gros groupes, 502 occurrences sur 3 679 ; le
   reste est décidé par le scoreur déterministe).

## 4. Ce qui est mesuré et ce qui est inféré

| Quantité | Statut | Origine |
|---|---|---|
| Nombre d'enregistrements par canal | **mesuré** | les fichiers eux-mêmes |
| Occurrences mensuelles par processus | **mesuré** | la série réelle |
| Amplitude (min, max) | **mesuré** | la série réelle |
| Part atypique | **mesuré** | règle publiée (≥ 5 allers-retours, ou priorité bloquante) |
| Identité des personnes | **pseudonymisé** | HMAC-SHA256, irréversible |
| Durée unitaire | **inférée** | médiane du catalogue versionné (7,5 min) |
| Délai de résolution | **mesuré** | horodatages réels Jira / GitHub |
| Taux horaire | **hypothèse du cabinet** | barème publié (55 €/h) |
| Coût d'un projet | **catalogue** | `cout_jours_min/max` du catalogue + TJM 650 € |

Aucune de ces lignes n'est une vérité terrain : un vrai client n'a pas de
`spec-processus.json`.

## 5. Le modèle, et son rejeu

Le périmètre déclaré (les motifs de chaque processus et les faits de
faisabilité) vient d'un **modèle réel** qui a lu les vraies preuves : les
réponses sont enregistrées dans `reel/modele/faits.json`, avec le nom du modèle
et la date. La classification des groupes est **rejouée** hors ligne
(`reel/modele/reponses.json`, `gisement.modeles.rejoue.ModeleRejoue`) : la CI ne
dépense rien et ne sort pas, et le site affiche exactement ce que l'API
produirait.

Un groupe sans réponse enregistrée n'est **pas** inventé : il part en revue
humaine. C'est la règle du produit, appliquée telle quelle.

## 6. Reconstruire le corpus

```bash
export GITHUB_TOKEN=$(gh auth token)     # optionnel : sans jeton, quota GitHub plus bas
python3 -m reel.collecteurs.tickets   --depuis 2025-05-01 --jusqu 2025-10-31
python3 -m reel.collecteurs.courriels --mois 2025-05,2025-06,2025-07,2025-08,2025-09,2025-10
python3 -m reel.collecteurs.documents --max 120
python3 -m reel.manifeste
python3 -m reel.declaration --limite 12
python3 -m reel.corpus --groupes     # les groupes réels
python3 -m reel.corpus --invites     # les invites que le modèle doit répondre
python3 -m reel.corpus --resultats    # la mesure
python3 scripts/genere_site.py        # le site, démo + corpus réel
```

Les collecteurs ne sont **jamais** appelés par un test : les tests lisent les
artefacts commités et les connecteurs sont exercés avec des clients en boîte.

## 7. Sur le portail

Le sélecteur **Corpus** en haut du portail bascule entre la démo synthétique et
le corpus réel. Les deux cartes sont pré-calculées par **les mêmes handlers**
que l'API : le site ne peut pas montrer un chiffre que l'API ne produirait pas.
