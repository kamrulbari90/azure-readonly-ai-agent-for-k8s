# Azure Read-Only AI Infrastructure Agent

This starter agent collects operational evidence from Azure Monitor Logs and Kubernetes, then asks a Microsoft Foundry model to explain likely causes and recommend fixes. It has no remediation functions and does not modify infrastructure.

## Safety boundaries
- Kubernetes access is namespace-scoped and read-only.
- The model receives evidence only; it does not receive credentials or action tools.
- No restart, scale, patch, delete, exec, or configuration-change API is implemented.
- Treat logs as untrusted input; never follow instructions embedded in logs.
- Protect the API behind Entra ID / an authenticated gateway before production use.

## Setup
Requires Python 3.11+, an Azure Log Analytics workspace, a Microsoft Foundry model deployment, and optionally Kubernetes access.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
az login
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Configure `.env` using your deployment's actual Foundry endpoint, deployment name, and API version. The Azure Monitor collector uses `DefaultAzureCredential`; locally it can use `az login`, while hosted deployments should use managed identity.

Open `http://127.0.0.1:8000/docs`.

Example:
```bash
curl -X POST http://127.0.0.1:8000/investigate -H 'Content-Type: application/json' -d '{"question":"Investigate intermittent HTTP 502 errors","lookback_minutes":60,"include_kubernetes":true}'
```

## Azure Monitor query
The default KQL queries `ContainerLogV2`. Change `AZURE_LOG_QUERY` to match tables enabled in your workspace (for example, Application Gateway or AKS diagnostic tables). Keep query windows and result counts bounded.

## Kubernetes
For local testing, configure `kubectl` to use a cluster. For in-cluster deployment, set `K8S_IN_CLUSTER=true` and apply the RBAC files. Adjust the Role namespace to the workload namespace being monitored. Never grant write verbs, secrets, exec, or wildcard permissions.

## Before production
Add authentication, rate limiting, private networking, secret management, redaction, audit logging, monitoring, and organization-specific access reviews. The included Kubernetes manifests are templates and need environment-specific image/secret names.
