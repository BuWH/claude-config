---
name: foundry-deployments
description: "Use when working with Microsoft Foundry (Azure AI Projects) via Python to enumerate model deployments, fetch deployment details, wire an OpenAI client, fetch model prices, list available models, and get deployment guidance. Triggers: listing available models/endpoints, checking deployment metadata (publisher/model/version/SKU), validating deployment names, fetching pricing, or deploying models."
---

# Foundry Deployments

## Overview
- Focuses on the `azure-ai-projects` Python client (Foundry data-plane) to explore project deployments.
- Extends functionality with Azure CLI integration for listing available models and web scraping for pricing.
- Covers authentication, environment variables, and unified CLI for comprehensive deployment management.
- Uses the SDK overview doc (Python pivot) as the canonical reference.

## Quick start
1) Install + env: `pip install --pre azure-ai-projects azure-identity requests beautifulsoup4 cachetools` and set `AZURE_AI_PROJECT_ENDPOINT` (project Overview page). Sign in via `az login` or set Entra client env vars. See references/foundry-deployments.md for details.
2) **Unified CLI**: Use `python scripts/foundry_cli.py` with subcommands:
   - `list-deployments` - List already deployed models
   - `get-pricing` - Fetch model prices from Azure documentation
   - `list-available-models` - List LLM models available for deployment
3) Inspect a deployment: `project_client.deployments.get(<deployment_name>)` to confirm fields like capabilities and SKU before inference.
4) Get OpenAI client for inference: `openai_client = project_client.get_openai_client()` then call `openai_client.responses.create(model=<deployment_name>, input="...")`.

## New Features

### 1. Model Pricing
- Fetches Azure OpenAI Service pricing from official documentation
- Caches results for 24 hours to avoid repeated web requests
- Filter by region with `--region` flag
- Command: `python scripts/foundry_cli.py get-pricing [--region REGION] [--refresh]`

### 2. Available Models Listing
- Uses Azure CLI (`az cognitiveservices model list`) to list available LLM models
- Filters for models with `chatCompletion` capability (LLM models only)
- Requires Azure CLI installed and authenticated (`az login`)
- Command: `python scripts/foundry_cli.py list-available-models [--publisher PUBLISHER] [--refresh]`

## Deploying models
- The Foundry data-plane SDK currently exposes `deployments.list`/`deployments.get` only. Creating or updating deployments is done via the Foundry portal or control-plane tooling (CLI/ARM) outside this SDK.
- After creating a deployment in the portal, validate with `list-deployments` and reuse the deployment name for inference.

## Resources
- `scripts/foundry_cli.py` — Unified CLI with all features (recommended)
- `scripts/list_deployments.py` — Original script for backward compatibility
- `scripts/pricing_cache.py` — Pricing data caching and web scraping
- `scripts/azure_cli_wrapper.py` — Azure CLI integration wrapper
- `references/foundry-deployments.md` — Condensed setup, auth, and usage notes from the Foundry SDK overview plus deployment caveats.
