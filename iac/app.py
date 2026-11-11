#!/usr/bin/env python3
"""CDK entry point of Gisement (lot 21).

    cd iac && cdk synth && cdk deploy

One stack, one region (eu-west-3, fallback eu-central-1). Serverless only: no
dedicated endpoint, no always-on SageMaker, no GPU (26.4). The stack is the
deployment of the offline demo: the same handlers, the same policy, the same
frozen corpus for the judge login.
"""

from __future__ import annotations

import aws_cdk as cdk

from gisement_stack import GisementStack

APP = cdk.App()
ENV = cdk.Environment(region="eu-west-3")

GisementStack(
    APP,
    "GisementStack",
    env=ENV,
    description=(
        "Gisement - measure the real manual work, deliver a sequenced "
        "portfolio (AWS MSP AI Hackathon, Track 2)"
    ),
)

APP.synth()
