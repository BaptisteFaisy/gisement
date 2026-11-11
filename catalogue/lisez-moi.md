# Catalogue des motifs d'automatisation

40 motifs, 8 familles (annexe B du cahier des charges). **Ce sont des données,
pas du code** : ajouter un motif ne demande aucune modification de programme
(exigence R25).

## Ajouter un motif

1. Ouvrir `motifs/<famille>.json` (ou créer un nouveau fichier `.json` dans ce
   répertoire : tous les fichiers sont chargés).
2. Ajouter un objet avec les champs ci-dessous.
3. Mettre à jour le compte attendu dans `COMPTES_PAR_FAMILLE`
   (`src/gisement/motifs/catalogue.py`) **uniquement** si l'on veut que le
   validateur exige le nouveau total — sinon le validateur signalera l'écart à
   l'annexe B, ce qui est le comportement voulu.
4. `python3 -m pytest tests/unit/motifs -q` doit rester vert.

## Champs

| Champ | Rôle |
|---|---|
| `ref` | Identifiant unique, `<FAMILLE>-<nn>` |
| `famille` | Une des huit familles de l'annexe B |
| `nom` / `nom_en` | Libellé français et anglais (EF-65) |
| `description` | Une phrase, lisible par un responsable de service |
| `canaux` | Canaux où le motif s'observe (`tickets`, `courriels`, `documents`, `appels`, `journaux`) |
| `indices.verbes` | Verbes canoniques de `src/gisement/empreinte.py` |
| `indices.objets` | 2 à 4 mots **distinctifs** du geste, repris dans `modele_texte` |
| `indices.systemes` | Systèmes touchés |
| `modele_texte` | La phrase canonique du geste : le générateur du jeu de démo écrit les activités avec, ce qui rend la classification mesurable |
| `duree_unitaire_typique_minutes` | Défaut quand la durée n'est pas mesurée |
| `duree_statut_defaut` | `mesuree` ou `inferree` (§9.3) |
| `repartition_defaut` | `regroupee`, `semi_regroupee`, `diffuse`, `interruptive` (§13.1) |
| `taux_revue_defaut`, `duree_revue_minutes` | Correction 2 du §13.1 |
| `part_atypique_defaut` | Correction 3 du §13.1 |
| `types_envisageables` | A à E (§14.1) |
| `cout_jours_min`, `cout_jours_max`, `abonnement_mensuel` | Ordre de grandeur du coût d'automatisation |

Toutes les grandeurs numériques sont des **chaînes** (`"9"`, `"0.20"`) : elles
sont converties en `Decimal` au chargement, jamais en flottant (ENF-13).

## Reconnaissance

Le score de rapprochement (`src/gisement/motifs/recherche.py`) est un
recouvrement lexical pondéré : verbe 0,50, objets 0,35, systèmes 0,15. Il est
déterministe et ne coûte rien — c'est lui qui regroupe les activités avant
l'appel au modèle, une fois par groupe et non par activité (§21.2, annexe G.1).

Un test vérifie que **chaque motif est reconnu en premier par sa propre phrase
canonique** : si un motif n'est pas reconnu, ce sont ses `indices.objets` qu'il
faut rendre plus distinctifs, pas le code de score.
