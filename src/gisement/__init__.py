"""Gisement - measure the real manual work, deliver a sequenced portfolio.

AWS MSP AI Hackathon, Track 2. The package is offline by default: every AWS
service is reached through an adapter with an in-memory fake, so the whole
pipeline runs in CI without credentials and without spending a cent
(spec 26.4 - no Transcribe and no Bedrock Data Automation during development).
"""

from __future__ import annotations

__version__ = "0.1.0"
