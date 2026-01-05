"""List deployments in a Microsoft Foundry project using the azure-ai-projects SDK.

Usage:
  python list_deployments.py [--publisher Microsoft] [--model-name Phi-4] [--deployment-type ModelDeployment]

Prereqs:
  - pip install --pre azure-ai-projects azure-identity
  - Set AZURE_AI_PROJECT_ENDPOINT to your project endpoint.
  - Ensure DefaultAzureCredential can obtain a token (login via `az login` or env vars).
"""

import argparse
import os
import sys
from typing import Optional

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="List Foundry model deployments")
    parser.add_argument(
        "--publisher",
        dest="publisher",
        help="Filter by model publisher (for example: Microsoft, OpenAI)",
    )
    parser.add_argument(
        "--model-name",
        dest="model_name",
        help="Filter by model name (publisher-specific model id, for example: Phi-4)",
    )
    parser.add_argument(
        "--deployment-type",
        dest="deployment_type",
        default="ModelDeployment",
        help="Deployment type filter (default: ModelDeployment)",
    )
    return parser.parse_args()


def ensure_endpoint() -> str:
    endpoint = os.environ.get("AZURE_AI_PROJECT_ENDPOINT")
    if not endpoint:
        sys.exit("AZURE_AI_PROJECT_ENDPOINT is required (from the Project Overview page).")
    return endpoint


def format_deployment(deployment) -> str:
    # Guard against missing fields on preview models.
    parts = [
        f"Name: {getattr(deployment, 'name', '')}",
        f"Publisher: {getattr(deployment, 'model_publisher', '')}",
        f"Model: {getattr(deployment, 'model_name', '')} v{getattr(deployment, 'model_version', '')}",
        f"SKU: {getattr(deployment, 'sku', '')}",
        f"Capabilities: {getattr(deployment, 'capabilities', '')}",
        f"Connection: {getattr(deployment, 'connection_name', '')}",
    ]
    return " | ".join(parts)


def list_deployments(
    endpoint: str,
    publisher: Optional[str],
    model_name: Optional[str],
    deployment_type: Optional[str],
) -> None:
    with (
        DefaultAzureCredential() as credential,
        AIProjectClient(endpoint=endpoint, credential=credential) as project_client,
    ):
        deployments = project_client.deployments.list(
            model_publisher=publisher,
            model_name=model_name,
            deployment_type=deployment_type,
        )
        for deployment in deployments:
            print(format_deployment(deployment))


def main() -> None:
    args = parse_args()
    endpoint = ensure_endpoint()
    list_deployments(
        endpoint=endpoint,
        publisher=args.publisher,
        model_name=args.model_name,
        deployment_type=args.deployment_type,
    )


if __name__ == "__main__":
    main()
