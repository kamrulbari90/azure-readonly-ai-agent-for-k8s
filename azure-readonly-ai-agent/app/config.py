from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    foundry_endpoint: str = ""
    foundry_api_key: str = ""
    foundry_deployment: str = ""
    foundry_api_version: str = "2024-10-21"
    azure_log_workspace_id: str = ""
    azure_log_query: str = (
        "ContainerLogV2 | where TimeGenerated >= ago({lookback}m) "
        "| project TimeGenerated, PodName, ContainerName, LogMessage | take 100"
    )
    k8s_namespace: str = "default"
    k8s_in_cluster: bool = False
    k8s_enabled: bool = True
    max_lookback_minutes: int = 240
    max_log_rows: int = 100
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
