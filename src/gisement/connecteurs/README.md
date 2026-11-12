# Connecteurs réels (idée #8)

Le jeu de démonstration est synthétique ; un client réel a déjà des outils. Ces
connecteurs traduisent la charge utile d'un fournisseur vers le schéma figé de
`docs/CONTRACTS.md` §5 — rien de plus. Tout le reste (assainissement,
empreinte, mesure) est identique quel que soit le canal.

| Connecteur | Canal | Source |
|---|---|---|
| `SourceJira` | tickets | `/rest/api/3/search` avec un JQL par projet |
| `SourceServiceNow` | tickets | `/api/now/table/<table>` |
| `SourceSage` | journaux | un export CSV (Sage, Cegid, SAP), séparateur `;` ou `,`, BOM toléré, en-têtes FR/EN |

## Brancher un vrai système

Le client HTTP est **injecté** : n'importe quelle session authentifiée convient.

```python
import requests
from gisement.connecteurs import SourceJira

session = requests.Session()
session.headers["Authorization"] = f"Bearer {token}"  # jamais en clair dans le depot
source = SourceJira(client=session, projet="SUP")
activites, rapport = tickets.collecter(source, parametres)
```

(`requests.Session.get` renvoie un objet dont `.json()` donne le dictionnaire ;
entourez-le d'un adaptateur de deux lignes si votre client ne répond pas
exactement au protocole `ClientHttp`.)

## Ajouter un connecteur

1. Implémenter `Source` (`canal`, `lire()`, `volume()`).
2. Normaliser avec `normaliser_ticket` ou `normaliser_journal`, ou écrire un
   normaliseur dédié si le schéma du fournisseur est exotique.
3. Paginer avec `paginer(client, url)` — la borne `max_pages` existe pour qu'un
   curseur infini soit un arrêt bruyant, pas une boucle.
4. Tester avec `FauxClientHttp` : aucune requête réseau en CI.

## Règles de sécurité

- **Aucun identifiant de personne ne sort du connecteur vers un stockage** : la
  pseudonymisation est appliquée en aval par `gisement.assainissement`, à
  l'ingestion, avant tout traitement (R3, ENF-02).
- Le connecteur ne lit **que le périmètre déclaré** dans la campagne (EF-01) :
  un JQL, une table, un fichier — jamais un compte entier.
- Les jetons d'accès ne sont jamais écrits dans le dépôt ni journalisés ; le
  registre de conformité note quel périmètre a été lu, pas avec quoi.
