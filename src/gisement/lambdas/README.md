# Le paquet Lambda — `gisement.lambdas.api`

Le handler déployé est exactement le code de la démo locale : `api.py` ne fait
que traduire un évènement API Gateway vers les handlers purs de
`gisement.api.handlers`, puis remettre la réponse au format proxy.

## Empaqueter

Projet en **stdlib uniquement** ; la commande d'installation est conservée pour
le jour où une dépendance tierce serait listée dans `requirements-lambda.txt` :

```bash
pip install -r requirements-lambda.txt   # aucune dépendance tierce aujourd'hui
rm -rf dist/lambda && mkdir -p dist/lambda/src dist/lambda/demo
cp -r src/gisement dist/lambda/src/gisement
cp -r config catalogue dist/lambda/
cp -r demo/donnees dist/lambda/demo/donnees
cp demo/spec-processus.json dist/lambda/demo/spec-processus.json
cd dist/lambda && zip -qr ../lambda.zip src config catalogue demo
# sans zip : python3 -m zipfile -c ../lambda.zip src config catalogue demo
```

Le corpus figé (`demo/donnees`, `demo/spec-processus.json`), `config/` et le
`catalogue/` de motifs **font partie du paquet** : `gisement.pipeline`,
`.sequenceur`, `.observabilite`, `.motifs` et `.politique` les retrouvent par
un chemin relatif à la racine du paquet (deux à trois niveaux au-dessus du
module). D'où le préfixe `src/` dans le zip : avec `gisement/` à la racine, ces
données tomberaient hors de `/var/task`. Handler attendu par la stack :
`gisement.lambdas.api.handler`, avec `PYTHONPATH=/var/task/src`.

## Déployer

`./scripts/deploy.sh` enchaîne dépendances, `cdk synth`, paquet, `cdk deploy`
et affiche les URL. Il est idempotent, n'écrit aucun secret (identifiants AWS :
chaîne standard profil / variables / rôle IAM) et ne supprime que `dist/`.
Pour pousser le paquet à la main (nom de fonction généré par la CDK, cf.
`aws lambda list-functions`) :

```bash
aws lambda update-function-code --function-name <fonction> --zip-file fileb://dist/lambda.zip
aws lambda update-function-configuration --function-name <fonction> \
    --environment 'Variables={PYTHONPATH=/var/task/src}'
```

## Garanties portées par ce handler

- **R1 — aucun identifiant de personne n'est exposé.** Les routes ne renvoient
  que des sorties agrégées ; une mesure sous le seuil d'agrégation est refusée
  et le refus nomme la règle (`regle_individu`, `regle_k5`, …).
- **EF-71 — le tenant vient du jeton.** Identité dérivée de l'en-tête
  `Authorization` via `tenant_depuis_jeton` ; jeton absent ou inconnu → `403`.
  Un `tenant_id` dans le corps ou la query string est ignoré (R21).
- **EF-04 — pas d'ingestion sans validation.** `POST …/lancer` répond `409`
  tant qu'aucune conformité DPO/représentants n'est enregistrée.

## État et cycle de vie

`ETAT` est un singleton paresseux : une campagne par conteneur, reconstruite à
chaque démarrage à froid ; `reinitialiser()` (ou `etat(reinitialiser=True)`) la
remet à zéro — c'est ce qu'utilisent les tests, sans AWS ni réseau.
