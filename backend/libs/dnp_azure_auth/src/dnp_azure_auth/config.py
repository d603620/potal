import os
from dataclasses import dataclass

@dataclass(frozen=True)
class AzureOpenAIConfig:
    endpoint: str
    deployment: str
    api_version: str
    scope: str = "https://cognitiveservices.azure.com/.default"

def load_azure_openai_config(
    endpoint_env: str,
    deployment_env: str,
    api_version_env: str | None = None,
) -> AzureOpenAIConfig:
    endpoint = os.getenv(endpoint_env, "").rstrip("/")
    deployment = os.getenv(deployment_env, "")
    api_version = os.getenv(api_version_env, "") if api_version_env else ""

    if not (endpoint and deployment):
        raise RuntimeError(f"Missing env: {endpoint_env} / {deployment_env}")

    return AzureOpenAIConfig(endpoint=endpoint, deployment=deployment, api_version=api_version)
