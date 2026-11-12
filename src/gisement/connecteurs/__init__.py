"""Real-world connectors: Jira, ServiceNow, ERP exports (idea #8).

`http_reel` is the standard-library client used when a connector is pointed at
a real system (`reel/`); no test ever instantiates it (26.4).
"""

from __future__ import annotations

from gisement.connecteurs.base import (
    ClientHttp,
    FauxClientHttp,
    normaliser_journal,
    normaliser_ticket,
    paginer,
    paginer_decalage,
)
from gisement.connecteurs.http_reel import ClientHttpReel, ErreurHttpReel
from gisement.connecteurs.jira import SourceJira
from gisement.connecteurs.sage import SourceSage
from gisement.connecteurs.servicenow import SourceServiceNow

__all__ = [
    "ClientHttp",
    "ClientHttpReel",
    "ErreurHttpReel",
    "FauxClientHttp",
    "SourceJira",
    "SourceSage",
    "SourceServiceNow",
    "normaliser_journal",
    "normaliser_ticket",
    "paginer",
    "paginer_decalage",
]
