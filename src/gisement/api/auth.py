"""Tenant identity, derived from the token, never from text (EF-71).

No route accepts a tenant as a parameter: the tenant comes from the bearer
token, so a client cannot read another client's data by changing a query string
(R21). The demo tokens are fixed; in production Cognito issues them and
AgentCore Identity derives the tenant.
"""

from __future__ import annotations

from dataclasses import dataclass

from gisement.types.communs import Role

#: The tenant of a client that is NOT the one this server serves. Its token is
#: refused everywhere: it is the negative case of R21.
TENANT_AUTRE = "T-AUTRE"

#: Demo tokens -> (role, tenant of another client?). The demo tokens are the
#: staff of the client this server serves, so their tenant is the one of the
#: campaign being served - never a hard-coded one, or the real corpus (whose
#: client is T-KAFKA) could never be measured.
#: In production this is a Cognito/AgentCore lookup.
JETONS_DEMO: dict[str, tuple[Role, bool]] = {
    "jeton-demo-msp": (Role.CONSULTANT_MSP, False),
    "jeton-demo-dpo": (Role.DPO, False),
    "jeton-demo-commanditaire": (Role.COMMANDITAIRE, False),
    "jeton-demo-responsable": (Role.RESPONSABLE_SERVICE, False),
    "jeton-demo-compte": (Role.RESPONSABLE_COMPTE, False),
    "jeton-autre-client": (Role.CONSULTANT_MSP, True),
}


@dataclass(frozen=True)
class Identite:
    tenant_id: str
    role: Role
    utilisateur: str


def tenant_depuis_jeton(jeton: str | None, tenant_servei: str = "T-DEMO") -> Identite | None:
    """Resolve a bearer token into an identity, or None if unknown.

    `tenant_servei` is the tenant of the campaign this server serves: the demo
    tokens belong to that client. The token of another client keeps its own
    tenant, so the isolation can be exercised (R21).
    """
    if not jeton:
        return None
    cle = jeton.removeprefix("Bearer ").strip()
    trouve = JETONS_DEMO.get(cle)
    if trouve is None:
        return None
    role, autre_tenant = trouve
    tenant = TENANT_AUTRE if autre_tenant else tenant_servei
    return Identite(tenant_id=tenant, role=role, utilisateur=f"u-{role.value}")


def est_dpo_ou_suspension(identite: Identite) -> bool:
    """Only the DPO or a staff representative can suspend (11.4)."""
    return identite.role == Role.DPO


def peut_valider_conformite(identite: Identite) -> bool:
    return identite.role == Role.DPO


def peut_lancer(identite: Identite) -> bool:
    return identite.role in (Role.CONSULTANT_MSP, Role.DPO)


def meme_tenant(identite: Identite, tenant_campagne: str) -> bool:
    """R21 - a client reads its own campaign only.

    The tenant of the campaign is the one the server was started for; the
    tenant of the request comes from the token. A mismatch means the client
    asks for another client's data: it is refused, never served.
    """
    return identite.tenant_id == tenant_campagne
