"""Real-world connectors: Jira, ServiceNow, ERP exports (idea #8)."""

from __future__ import annotations

from gisement.connecteurs.base import (
    ClientHttp,
    FauxClientHttp,
    normaliser_journal,
    normaliser_ticket,
    paginer,
)
from gisement.connecteurs.jira import SourceJira
from gisement.connecteurs.sage import SourceSage
from gisement.connecteurs.servicenow import SourceServiceNow

__all__ = [
    "ClientHttp",
    "FauxClientHttp",
    "SourceJira",
    "SourceSage",
    "SourceServiceNow",
    "normaliser_journal",
    "normaliser_ticket",
    "paginer",
]
