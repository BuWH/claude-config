"""Azure CLI wrapper for listing available models in Azure Cognitive Services.

This module provides functionality to interact with Azure CLI to:
1. Check if Azure CLI is installed and authenticated
2. List available models using `az cognitiveservices model list`
3. Parse and format model information
"""

import json
import subprocess
import sys
from typing import Dict, List, Optional, Any
from pathlib import Path


class AzureCLIWrapper:
    """Wrapper for Azure CLI operations."""

    def __init__(self):
        self.az_path = self._find_az_cli()

    def _find_az_cli(self) -> str:
        """Find Azure CLI executable path."""
        try:
            # Try to find az in PATH
            result = subprocess.run(
                ["which", "az"],
                capture_output=True,
                text=True,
                check=False
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except (subprocess.SubprocessError, FileNotFoundError):
            pass

        # Default to 'az' and hope it's in PATH
        return "az"

    def check_az_cli_installed(self) -> bool:
        """Check if Azure CLI is installed and accessible."""
        try:
            result = subprocess.run(
                [self.az_path, "--version"],
                capture_output=True,
                text=True,
                check=False
            )
            return result.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError):
            return False

    def check_az_login(self) -> bool:
        """Check if user is authenticated with Azure CLI."""
        try:
            result = subprocess.run(
                [self.az_path, "account", "show"],
                capture_output=True,
                text=True,
                check=False
            )
            return result.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError):
            return False

    def run_az_command(self, args: List[str], timeout: int = 30) -> Dict[str, Any]:
        """
        Run an Azure CLI command and return parsed JSON output.

        Args:
            args: List of arguments for az command
            timeout: Command timeout in seconds

        Returns:
            Parsed JSON output as dictionary

        Raises:
            RuntimeError: If command fails or returns invalid JSON
        """
        cmd = [self.az_path] + args + ["--output", "json"]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError("Azure CLI command timed out")
        except (subprocess.SubprocessError, FileNotFoundError) as e:
            raise RuntimeError(f"Failed to execute Azure CLI: {e}")

        if result.returncode != 0:
            error_msg = result.stderr.strip() or "Unknown error"
            raise RuntimeError(f"Azure CLI command failed: {error_msg}")

        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Failed to parse Azure CLI output as JSON: {e}")

    def list_available_models(
        self,
        location: str = "eastus",
        publisher: Optional[str] = None,
        kind: Optional[str] = None,
        llm_only: bool = True
    ) -> List[Dict[str, Any]]:
        """
        List available models using Azure CLI.

        Args:
            location: Azure region (default: eastus)
            publisher: Filter by publisher (optional)
            kind: Filter by kind (e.g., OpenAI, ContentSafety)
            llm_only: Filter for LLM models with chatCompletion capability (default: True)

        Returns:
            List of model information dictionaries
        """
        args = ["cognitiveservices", "model", "list", "--location", location]

        if kind:
            args.extend(["--kind", kind])

        try:
            models_data = self.run_az_command(args)
        except RuntimeError as e:
            print(f"Error listing models: {e}", file=sys.stderr)
            return []

        # Parse and format model data
        parsed_models = []
        for model_entry in models_data:
            model_info = self._parse_model_entry(model_entry)

            # Apply filters
            if publisher and model_info.get("publisher") != publisher:
                continue
            if kind and model_info.get("kind") != kind:
                continue

            # Filter for LLM models (chatCompletion capability)
            if llm_only:
                capabilities = model_info.get("capabilities", [])
                if "chatCompletion" not in capabilities:
                    continue

            parsed_models.append(model_info)

        return parsed_models

    def _parse_model_entry(self, model_entry: Dict[str, Any]) -> Dict[str, Any]:
        """Parse a single model entry from Azure CLI output."""
        model_data = model_entry.get("model", {})

        # Extract basic information
        parsed = {
            "id": model_entry.get("id", ""),
            "name": model_data.get("name", ""),
            "kind": model_entry.get("kind", ""),
            "location": model_entry.get("location", ""),
            "publisher": model_data.get("publisher", ""),
            "format": model_data.get("format", ""),
            "version": self._extract_version_from_id(model_entry.get("id", "")),
            "lifecycle_status": model_data.get("lifecycleStatus", ""),
            "is_default_version": model_data.get("isDefaultVersion", False),
            "capabilities": self._parse_capabilities(model_data.get("capabilities", {})),
            "skus": self._parse_skus(model_data.get("skus", [])),
            "deprecation": model_data.get("deprecation", {}),
        }

        return parsed

    def _extract_version_from_id(self, model_id: str) -> str:
        """Extract version from model ID."""
        # Model ID format: .../models/OpenAI.dall-e-3.3.0
        parts = model_id.split("/")
        if len(parts) > 0:
            last_part = parts[-1]
            # Split by dots and get last part as version
            subparts = last_part.split(".")
            if len(subparts) > 1:
                return subparts[-1]
        return ""

    def _parse_capabilities(self, capabilities: Dict[str, Any]) -> List[str]:
        """Parse capabilities dictionary into list of enabled capabilities."""
        enabled = []
        for key, value in capabilities.items():
            if value == "true" or value is True:
                enabled.append(key)
        return enabled

    def _parse_skus(self, skus: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Parse SKU information."""
        parsed_skus = []
        for sku in skus:
            parsed_sku = {
                "name": sku.get("name", ""),
                "capacity": sku.get("capacity", {}),
                "rate_limits": sku.get("rateLimits", []),
                "deprecation_date": sku.get("deprecationDate", ""),
            }
            parsed_skus.append(parsed_sku)
        return parsed_skus

    def get_model_details(self, model_name: str, location: str = "eastus") -> Optional[Dict[str, Any]]:
        """Get detailed information for a specific model."""
        models = self.list_available_models(location=location)
        for model in models:
            if model.get("name", "").lower() == model_name.lower():
                return model
        return None


# Convenience functions for backward compatibility
def list_available_models(
    location: str = "eastus",
    publisher: Optional[str] = None,
    kind: Optional[str] = None,
    refresh_cache: bool = False,
    llm_only: bool = True
) -> List[Dict[str, Any]]:
    """
    List available models (convenience function).

    Args:
        location: Azure region
        publisher: Filter by publisher
        kind: Filter by kind
        refresh_cache: Included for API compatibility (cache not implemented yet)
        llm_only: Filter for LLM models with chatCompletion capability (default: True)

    Returns:
        List of model information dictionaries
    """
    wrapper = AzureCLIWrapper()
    return wrapper.list_available_models(location=location, publisher=publisher, kind=kind, llm_only=llm_only)


def check_az_cli_installed() -> bool:
    """Check if Azure CLI is installed."""
    wrapper = AzureCLIWrapper()
    return wrapper.check_az_cli_installed()


def check_az_login() -> bool:
    """Check if user is authenticated."""
    wrapper = AzureCLIWrapper()
    return wrapper.check_az_login()


if __name__ == "__main__":
    # Test the wrapper
    wrapper = AzureCLIWrapper()

    print("Testing Azure CLI wrapper...")
    print(f"Azure CLI installed: {wrapper.check_az_cli_installed()}")
    print(f"Azure CLI authenticated: {wrapper.check_az_login()}")

    if wrapper.check_az_cli_installed() and wrapper.check_az_login():
        print("\nFetching available models (first 5)...")
        try:
            models = wrapper.list_available_models(location="eastus", kind="OpenAI")
            print(f"Found {len(models)} models")
            for i, model in enumerate(models[:5]):
                print(f"\n{i+1}. {model.get('name', 'Unknown')}")
                print(f"   Publisher: {model.get('publisher', 'Unknown')}")
                print(f"   Version: {model.get('version', 'Unknown')}")
                print(f"   Capabilities: {', '.join(model.get('capabilities', []))}")
        except Exception as e:
            print(f"Error: {e}")
    else:
        print("\nCannot fetch models. Please ensure Azure CLI is installed and authenticated.")