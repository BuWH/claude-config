"""Unified CLI for Microsoft Foundry (Azure AI Projects) operations.

Usage:
  python foundry_cli.py list-deployments [--publisher PUBLISHER] [--model-name MODEL] [--deployment-type TYPE]
  python foundry_cli.py get-pricing [--region REGION] [--refresh]
  python foundry_cli.py list-available-models [--publisher PUBLISHER] [--refresh]

Commands:
  list-deployments      List already deployed models (existing functionality)
  get-pricing           Fetch model prices from Azure documentation
  list-available-models List models available for deployment (LLM models only)

Prereqs:
  - pip install --pre azure-ai-projects azure-identity requests beautifulsoup4 cachetools
  - Set AZURE_AI_PROJECT_ENDPOINT to your project endpoint.
  - Ensure DefaultAzureCredential can obtain a token (login via `az login` or env vars).
  - For Azure CLI commands: `az` CLI must be installed and authenticated.
"""

import argparse
import os
import sys
import json
from typing import Optional, List, Dict, Any
from pathlib import Path

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential


def ensure_endpoint() -> str:
    """Ensure AZURE_AI_PROJECT_ENDPOINT environment variable is set."""
    endpoint = os.environ.get("AZURE_AI_PROJECT_ENDPOINT")
    if not endpoint:
        sys.exit("AZURE_AI_PROJECT_ENDPOINT is required (from the Project Overview page).")
    return endpoint


def format_deployment(deployment) -> str:
    """Format deployment information for display."""
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


# ============================================================================
# Command: list-deployments (existing functionality)
# ============================================================================

def list_deployments_cmd(
    endpoint: str,
    publisher: Optional[str],
    model_name: Optional[str],
    deployment_type: Optional[str],
) -> None:
    """List already deployed models."""
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


# ============================================================================
# Command: get-pricing (new feature)
# ============================================================================

def get_pricing_cmd(region: Optional[str], refresh: bool) -> None:
    """Fetch model prices from Azure documentation."""
    try:
        # Import here to avoid dependency issues if module not available yet
        import pricing_cache
    except ImportError:
        print("Error: Pricing module not available. Make sure dependencies are installed.")
        print("Required: pip install requests beautifulsoup4 cachetools")
        sys.exit(1)

    cache = pricing_cache.PricingCache()

    if refresh:
        cache.clear()
        print("Cache cleared. Fetching fresh pricing data...")

    pricing_data = cache.get_pricing(region=region)

    if not pricing_data:
        print("No pricing data available. Try with --refresh flag.")
        return

    print("Azure OpenAI Service Pricing (per 1K tokens):")
    print("=" * 80)
    for region_name, models in pricing_data.items():
        if region and region.lower() != region_name.lower():
            continue

        print(f"\nRegion: {region_name}")
        print("-" * 40)
        for model_info in models:
            name = model_info.get('model', 'Unknown')
            input_price = model_info.get('input_price', 'N/A')
            output_price = model_info.get('output_price', 'N/A')
            print(f"  {name}:")
            print(f"    Input:  ${input_price}/1K tokens")
            print(f"    Output: ${output_price}/1K tokens")


# ============================================================================
# Command: list-available-models (new feature)
# ============================================================================

def list_available_models_cmd(publisher: Optional[str], refresh: bool) -> None:
    """List models available for deployment via Azure CLI."""
    try:
        # Import here to avoid dependency issues
        import azure_cli_wrapper
    except ImportError:
        print("Error: Azure CLI wrapper not available.")
        sys.exit(1)

    cli_wrapper = azure_cli_wrapper.AzureCLIWrapper()

    if not cli_wrapper.check_az_cli_installed():
        print("Error: Azure CLI is not installed.")
        print("Install from: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli")
        sys.exit(1)

    if not cli_wrapper.check_az_login():
        print("Error: Not authenticated with Azure CLI.")
        print("Run: az login")
        sys.exit(1)

    models = azure_cli_wrapper.list_available_models(publisher=publisher, refresh_cache=refresh, llm_only=True)

    if not models:
        print("No available models found.")
        return

    print(f"Available Models for Deployment ({len(models)} total):")
    print("=" * 80)
    for model in models:
        name = model.get('name', 'Unknown')
        model_publisher = model.get('publisher', 'Unknown')
        version = model.get('version', 'Unknown')
        capabilities = model.get('capabilities', [])

        if publisher and publisher.lower() != model_publisher.lower():
            continue

        print(f"Name: {name} | Publisher: {model_publisher} | Version: {version}")
        if capabilities:
            print(f"  Capabilities: {', '.join(capabilities)}")
        print()




# ============================================================================
# Main CLI Parser
# ============================================================================

def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Unified CLI for Microsoft Foundry (Azure AI Projects) operations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute", required=True)

    # list-deployments command
    list_parser = subparsers.add_parser("list-deployments", help="List already deployed models")
    list_parser.add_argument("--publisher", help="Filter by model publisher (e.g., Microsoft, OpenAI)")
    list_parser.add_argument("--model-name", help="Filter by model name (e.g., Phi-4, gpt-4)")
    list_parser.add_argument("--deployment-type", default="ModelDeployment",
                           help="Deployment type filter (default: ModelDeployment)")

    # get-pricing command
    pricing_parser = subparsers.add_parser("get-pricing", help="Fetch model prices from Azure documentation")
    pricing_parser.add_argument("--region", help="Filter by Azure region (e.g., eastus, westeurope)")
    pricing_parser.add_argument("--refresh", action="store_true", help="Refresh cache and fetch fresh data")

    # list-available-models command
    models_parser = subparsers.add_parser("list-available-models", help="List models available for deployment")
    models_parser.add_argument("--publisher", help="Filter by publisher")
    models_parser.add_argument("--refresh", action="store_true", help="Refresh cache and fetch fresh data")


    return parser.parse_args()


def main() -> None:
    """Main entry point."""
    args = parse_args()

    if args.command == "list-deployments":
        endpoint = ensure_endpoint()
        list_deployments_cmd(
            endpoint=endpoint,
            publisher=args.publisher,
            model_name=args.model_name,
            deployment_type=args.deployment_type,
        )
    elif args.command == "get-pricing":
        get_pricing_cmd(region=args.region, refresh=args.refresh)
    elif args.command == "list-available-models":
        list_available_models_cmd(publisher=args.publisher, refresh=args.refresh)
    else:
        print(f"Unknown command: {args.command}")
        sys.exit(1)


if __name__ == "__main__":
    main()