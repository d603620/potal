# app/core/azure_openai_client.py
import os
from typing import Optional

from azure.core.credentials import TokenCredential

from dnp_azure_auth.config import load_azure_openai_config
from dnp_azure_auth.credential import get_credential

# openai==1.x 系を想定
# ※ Azure OpenAI 用のクライアントは AzureOpenAI を使う
from openai import AzureOpenAI


# -----------------------------
# 設定（共通 config 経由）
# -----------------------------
# 既存の *4 付き env を使っている場合でも動くように、まずは *4 を優先しつつ
# 無ければ通常名へフォールバックする運用にできます。
# （完全移行するなら *4 は削除してOK）
def _env(primary: str, fallback: str) -> str:
    return os.getenv(primary) or os.getenv(fallback) or ""


# env名の互換（*4 -> 通常名）
_ENDPOINT_ENV = "API_AZURE_OPENAI_ENDPOINT"
_DEPLOYMENT_ENV = "API_AZURE_OPENAI_DEPLOYMENT"
_API_VERSION_ENV = "API_AZURE_OPENAI_API_VERSION"

# 共通ライブラリに渡す “実際に読む env 名” を決める
# *4 が入っているなら *4 を読む / 無いなら通常名を読む
_endpoint_env_name = _ENDPOINT_ENV if os.getenv(_ENDPOINT_ENV) else "AZURE_OPENAI_ENDPOINT"
_deployment_env_name = _DEPLOYMENT_ENV if os.getenv(_DEPLOYMENT_ENV) else "AZURE_OPENAI_DEPLOYMENT"
_api_version_env_name = _API_VERSION_ENV if os.getenv(_API_VERSION_ENV) else "AZURE_OPENAI_API_VERSION"

_cfg = load_azure_openai_config(
    endpoint_env=_endpoint_env_name,
    deployment_env=_deployment_env_name,
    api_version_env=_api_version_env_name,
)

# 認証（共通ライブラリ）
# mode: auto / mi / sp / cli（本番は mi 推奨）
_credential: TokenCredential = get_credential(mode=os.getenv("AZURE_AUTH_MODE", "auto"))

# クライアントは1回作って使い回す
_client: Optional[AzureOpenAI] = None


def _get_client() -> AzureOpenAI:
    """
    Entra ID の TokenCredential からトークンを取り、AzureOpenAI クライアントに渡す。
    """
    global _client
    if _client is not None:
        return _client

    def _token_provider() -> str:
        # Azure OpenAI の scope は Cognitive Services 既定
        return _credential.get_token(_cfg.scope).token

    # AzureOpenAI は api_version と azure_endpoint を受け取る
    _client = AzureOpenAI(
        azure_endpoint=_cfg.endpoint,
        api_version=_cfg.api_version,
        azure_ad_token_provider=_token_provider,
    )
    return _client


def call_chat(system_prompt: str, user_prompt: str) -> str:
    """
    既存の call_chat と同じ I/F のまま、Entra ID 認証で Azure OpenAI を呼ぶ。
    """
    client = _get_client()
    resp = client.chat.completions.create(
        model=_cfg.deployment,          # Azure では deployment 名を model に渡す
        temperature=1.0,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    return resp.choices[0].message.content or ""
