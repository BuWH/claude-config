# Foundry project quick reference

Use this when you need to work with model deployments in a Microsoft Foundry project via the `azure-ai-projects` SDK (Python pivot in [SDK overview](https://learn.microsoft.com/en-us/azure/ai-foundry/how-to/develop/sdk-overview?view=foundry&pivots=programming-language-python)).

## Prereqs
- Install: `pip install --pre azure-ai-projects azure-identity requests beautifulsoup4 cachetools` (plus `openai` if you need inference calls).
- Auth: `DefaultAzureCredential` (developer CLI login or env vars like `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`).
- Env vars: `AZURE_AI_PROJECT_ENDPOINT` (project Overview page). Use `AZURE_AI_MODEL_DEPLOYMENT_NAME` when making inference calls.
- For Azure CLI features: Install `az` CLI and authenticate with `az login`.

## Unified CLI
The `foundry_cli.py` provides all functionality in one tool:

```bash
# List already deployed models
python scripts/foundry_cli.py list-deployments [--publisher PUBLISHER] [--model-name MODEL]

# Fetch model prices from Azure documentation
python scripts/foundry_cli.py get-pricing [--region REGION] [--refresh]

# List available LLM models for deployment
python scripts/foundry_cli.py list-available-models [--publisher PUBLISHER] [--refresh]
```

## Connect to Project
```python
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient

project = AIProjectClient(
    endpoint=os.environ["AZURE_AI_PROJECT_ENDPOINT"],
    credential=DefaultAzureCredential(),
)
```

## List deployments (model inventory)
Data-plane supports enumerate + inspect deployed models (no create API yet). Filters mirror the SDK:
```python
for d in project.deployments.list(model_publisher="Microsoft", model_name="Phi-4"):
    print(d.name, d.model_publisher, d.model_name, d.model_version, d.capabilities)
single = project.deployments.get("your-deployment-name")
```
Use `scripts/foundry_cli.py list-deployments` for a ready-to-run CLI helper.

## Fetch Model Prices
- Uses web scraping to fetch Azure OpenAI Service pricing from official documentation
- Caches results for 24 hours with file-based cache
- Extracts pricing per 1K tokens for input/output
- Filter by Azure region with `--region` flag

## List Available Models
- Uses Azure CLI `az cognitiveservices model list` command
- Filters for LLM models with `chatCompletion` capability
- Parses JSON output and formats consistently
- Requires Azure CLI installed and authenticated

## Deploying models (manual)
- The `AIProjectClient` data plane currently offers `list`/`get` only for deployments; creating or updating deployments is done via the Foundry portal or control-plane tooling.
- After creating a deployment in the portal (Models + endpoints), reuse the deployment name in `deployments.get(...)` and in inference calls via `project.get_openai_client().responses.create(model=<deployment_name>, ...)`.
- If control-plane automation is required, use the Azure CLI/ARM for Foundry model deployments (outside the scope of this data-plane SDK); once provisioned, verify with `deployments.list()`.

## Architecture
- `foundry_cli.py`: Unified CLI entry point with subcommands
- `pricing_cache.py`: Web scraping and caching for pricing data
- `azure_cli_wrapper.py`: Azure CLI integration with error handling
- `list_deployments.py`: Original script maintained for backward compatibility
