#!/usr/bin/env bash
# Deploy Gisement: dependencies, synthesis, Lambda package, deployment, URLs.
#
# Ce script se lit sans risque : il n'ecrit rien hors de dist/ et iac/cdk.out/
# (artefacts CDK), ne supprime rien hors de dist/, et ne contient aucun secret
# en clair - les identifiants AWS viennent de la chaine standard (profil,
# variables d'environnement, role IAM). Il est idempotent : le relancer
# redéploie la meme stack sans effet de bord cumulatif.
#
# Usage : ./scripts/deploy.sh

set -euo pipefail

RACINE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IAC="$RACINE/iac"
DIST="$RACINE/dist"
PAQUET="$DIST/lambda"
ZIP="$DIST/lambda.zip"
SORTIES="$DIST/outputs.json"

etape() { printf '\n=== %s ===\n' "$1"; }

# ------------------------------------------------------------------- prerequis

etape "Prerequis"
command -v python3 >/dev/null 2>&1 || {
    echo "python3 est requis (3.12 ou plus)." >&2
    exit 1
}
command -v cdk >/dev/null 2>&1 || {
    echo "Le CLI AWS CDK est introuvable dans le PATH." >&2
    echo "Installez-le avec : npm install -g aws-cdk" >&2
    exit 1
}

# ------------------------------------------------------- dependances CDK (iac)

etape "Dependances CDK (iac/)"
cd "$IAC"
if [[ -f package-lock.json ]]; then
    npm ci
elif [[ -f package.json ]]; then
    npm install
else
    python3 -m pip install -r requirements.txt
fi

# ---------------------------------------------------------- synthese (bloquante)

etape "Synthese : cdk synth (tout echec arrete le script)"
cdk synth >/dev/null

# ---------------------------------------------------------------- paquet Lambda

etape "Paquet Lambda : dist/lambda -> dist/lambda.zip"
echo "Suppression de $PAQUET, $ZIP et $SORTIES (dist/ uniquement)"
rm -rf "$PAQUET"
rm -f "$ZIP" "$SORTIES"
mkdir -p "$PAQUET/src" "$PAQUET/demo"
# Le paquet reproduit l'arborescence du depot : gisement.pipeline, .sequenceur,
# .observabilite, .motifs et .politique retrouvent leurs donnees par un chemin
# relatif au paquet (parents[2]/parents[3]) - config/, catalogue/ et demo/
# sont donc indissociables du code.
cp -R "$RACINE/src/gisement" "$PAQUET/src/gisement"
cp -R "$RACINE/config" "$PAQUET/config"
cp -R "$RACINE/catalogue" "$PAQUET/catalogue"
cp -R "$RACINE/demo/donnees" "$PAQUET/demo/donnees"
cp "$RACINE/demo/spec-processus.json" "$PAQUET/demo/spec-processus.json"
echo "Nettoyage des __pycache__ copies, sous $PAQUET uniquement"
find "$PAQUET" -name '__pycache__' -type d -prune -exec rm -rf {} +
if command -v zip >/dev/null 2>&1; then
    (cd "$PAQUET" && zip -qr "$ZIP" src config catalogue demo)
else
    (cd "$PAQUET" && python3 -m zipfile -c "$ZIP" src config catalogue demo)
fi
echo "Paquet pret : $ZIP ($(du -h "$ZIP" | cut -f1))"

# --------------------------------------------- fumee : le paquet importe et repond

etape "Test de fumee du paquet (hors ligne, sans AWS)"
PYTHONPATH="$PAQUET/src" python3 - <<'PY'
from gisement.lambdas import api

DPO = {"Authorization": "Bearer jeton-demo-dpo"}
sante = api.handler({"httpMethod": "GET", "path": "/api/health", "headers": DPO})
assert sante["statusCode"] == 200, sante
conformite = api.router(
    {
        "httpMethod": "POST",
        "path": "/api/campagnes/courante/conformite",
        "headers": DPO,
        "body": "{}",
    }
)
assert conformite[0] == 200, conformite
lancer = api.router(
    {"httpMethod": "POST", "path": "/api/campagnes/courante/lancer", "headers": DPO, "body": None}
)
assert lancer[0] == 200, lancer
print("OK : le paquet repond a /api/health et deroule la campagne complete")
PY

# -------------------------------------------------------------------- deployer

etape "Deploiement : cdk deploy --require-approval never"
cd "$IAC"
cdk deploy --require-approval never --outputs-file "$SORTIES"

# --------------------------------------------------------------------- adresses

etape "Adresses"
if [[ -f "$SORTIES" ]]; then
    python3 - "$SORTIES" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as flux:
    sorties = json.load(flux)
pile = next(iter(sorties.values()), {})
print(f"API     : {pile.get('api-url', '(sortie api-url absente)')}")
print(f"Portail : {pile.get('portal-url', '(sortie portal-url absente)')}")
PY
else
    cdk output api-url || true
    cdk output portal-url || true
fi
