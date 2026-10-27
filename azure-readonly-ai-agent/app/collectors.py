from datetime import timedelta
from typing import Any
from azure.identity import DefaultAzureCredential
from azure.monitor.query import LogsQueryClient, LogsQueryStatus
from kubernetes import client, config
from kubernetes.config.config_exception import ConfigException
from .config import settings

def query_azure_monitor(lookback_minutes: int) -> dict[str, Any]:
    if not settings.azure_log_workspace_id:
        return {"source": "azure_monitor", "status": "skipped", "reason": "Workspace ID not configured", "rows": []}
    lookback_minutes = max(1, min(lookback_minutes, settings.max_lookback_minutes))
    query = settings.azure_log_query.format(lookback=lookback_minutes)
    try:
        credential = DefaultAzureCredential()
        logs = LogsQueryClient(credential)
        result = logs.query_workspace(
            workspace_id=settings.azure_log_workspace_id,
            query=query,
            timespan=timedelta(minutes=lookback_minutes),
        )
        if result.status == LogsQueryStatus.SUCCESS:
            table = result.tables[0] if result.tables else None
            rows = []
            if table:
                for row in table.rows[:settings.max_log_rows]:
                    rows.append({str(table.columns[i].name): str(value) for i, value in enumerate(row)})
            return {"source": "azure_monitor", "status": "ok", "rows": rows}
        return {"source": "azure_monitor", "status": "partial", "rows": []}
    except Exception as exc:
        return {"source": "azure_monitor", "status": "error", "error_type": type(exc).__name__, "message": str(exc)[:400]}

def _load_kube_config():
    if settings.k8s_in_cluster:
        config.load_incluster_config()
    else:
        try:
            config.load_kube_config()
        except ConfigException:
            config.load_incluster_config()

def collect_kubernetes() -> dict[str, Any]:
    if not settings.k8s_enabled:
        return {"source": "kubernetes", "status": "skipped"}
    try:
        _load_kube_config()
        core, apps = client.CoreV1Api(), client.AppsV1Api()
        ns = settings.k8s_namespace
        pods = core.list_namespaced_pod(namespace=ns, limit=100)
        events = core.list_namespaced_event(namespace=ns, limit=100)
        deployments = apps.list_namespaced_deployment(namespace=ns, limit=100)
        return {
            "source": "kubernetes", "status": "ok", "namespace": ns,
            "pods": [{
                "name": p.metadata.name,
                "phase": p.status.phase if p.status else None,
                "node": p.spec.node_name if p.spec else None,
                "restarts": sum(c.restart_count or 0 for c in (p.status.container_statuses or []))
                    if p.status and p.status.container_statuses else 0
            } for p in pods.items],
            "events": [{
                "type": e.type, "reason": e.reason,
                "object": f"{e.involved_object.kind}/{e.involved_object.name}",
                "message": (e.message or "")[:400]
            } for e in events.items[-50:]],
            "deployments": [{
                "name": d.metadata.name,
                "desired_replicas": d.spec.replicas if d.spec else None,
                "ready_replicas": d.status.ready_replicas if d.status else 0
            } for d in deployments.items]
        }
    except Exception as exc:
        return {"source": "kubernetes", "status": "error", "error_type": type(exc).__name__, "message": str(exc)[:400]}
