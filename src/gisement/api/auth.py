"""Tenant identity, derived from the token, never from text (EF-71).

No route accepts a tenant as a parameter: the tenant comes from the bearer
token, so a client cannot read another client's data by changing a query string
(R21). The demo tokens are fixed; in production Cognito issues them and
AgentCore Identity derives the tenant.
"""

from __future__ import annotations

from dataclasses import dataclass

from gisement.types.communs import Role

#: Demo tokens -> (tenant, role). In production this is a Cognito/AgentCore lookup.
JETONS_DEMO: dict[str, tuple[str, Role]] = {
    "jeton-demo-msp": ("T-DEMO", Role.CONSULTANT_MSP),
    "jeton-demo-dpo": ("T-DEMO", Role.DPO),
    "jeton-demo-commanditaire": ("T-DEMO", Role.COMMANDITAIRE),
    "jeton-demo-responsable": ("T-DEMO", Role.RESPONSABLE_SERVICE),
    "jeton-demo-compte": ("T-DEMO", Role.RESPONSABLE_COMPTE),
    "jeton-autre-client": ("T-AUTRE", Role.CONSULTANT_MSP),
}


@dataclass(frozen=True)
class Identite:
    tenant_id: str
    role: Role
    utilisateur: str


def tenant_depuis_jeton(jeton: str | None) -> Identite | None:
    """Resolve a bearer token into an identity, or None if unknown."""
    if not jeton:
        return None
    cle = jeton.removeprefix("Bearer ").strip()
    trouve = JETONS_DEMO.get(cle)
    if trouve is None:
        return None
    tenant, role = trouve
    return Identite(tenant_id=tenant, role=role, utilisateur=f"u-{role.value}")


def est_dpo_ou_suspension(identite: Identite) -> bool:
    """Only the DPO or a staff representative can suspend (11.4)."""
    return identite.role == Role.DPO


def peut_valider_conformite(identite: Identite) -> bool:
    return identite.role == Role.DPO


def peut_lancer(identite: Identite) -> bool:
    return identite.role in (Role.CONSULTANT_MSP, Role.DPO)
