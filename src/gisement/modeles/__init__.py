"""Model adapters. `ModeleFictif` for tests and the demo, `BedrockModele`
(added by lot 10 in `modeles/bedrock.py`) for the real deployment."""

from __future__ import annotations

from gisement.modeles.base import Modele, ReponseModele, estimer_jetons
from gisement.modeles.fictif import ModeleFictif
from gisement.modeles.rejoue import ModeleRejoue

__all__ = ["Modele", "ModeleFictif", "ModeleRejoue", "ReponseModele", "estimer_jetons"]
