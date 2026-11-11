"""Shared fixtures of the policy tests: one compliant context, one clean request."""

from __future__ import annotations

from decimal import Decimal

import pytest

from gisement.politique import ContextePolitique
from gisement.types import Canal, Regle, Role
from gisement.types.conformite import OUTIL_MESURE, RequeteMesure


@pytest.fixture
def ctx() -> ContextePolitique:
    return ContextePolitique(
        campagne_id="CMP-0031",
        tenant_id="T-DEMO",
        conforme=True,
        suspendue=False,
        seuil=5,
        canaux_autorises=tuple(c.value for c in Canal),
        budget_restant=Decimal("12.50"),
        requetes_utilisateur=0,
        quota_requetes=200,
        corpus_assainis=frozenset({"CORP-0031-tickets"}),
    )


@pytest.fixture
def requete_agregee() -> RequeteMesure:
    """A request that must be allowed: one service, thirty four people."""
    return RequeteMesure(
        outil=OUTIL_MESURE,
        tenant_id="T-DEMO",
        utilisateur="u-consultant-01",
        role=Role.CONSULTANT_MSP,
        campagne_id="CMP-0031",
        canal=Canal.TICKETS,
        filtres={"service": "adv"},
        groupements=("service", "motif"),
        sortie=("occurrences", "temps_net"),
        taille_groupe=34,
        taille_resultat_apres_filtres=34,
    )


@pytest.fixture
def fabrique_requete(requete_agregee):
    def construire(**modifications) -> RequeteMesure:
        from dataclasses import replace

        return replace(requete_agregee, **modifications)

    return construire


@pytest.fixture
def regle_k5() -> Regle:
    return Regle.K5
