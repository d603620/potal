import os
from typing import List

from azure.core.credentials import TokenCredential
from azure.identity import (
    ChainedTokenCredential,
    ManagedIdentityCredential,
    ClientSecretCredential,
    AzureCliCredential,
)


def get_credential(mode: str = "auto") -> TokenCredential:
    """
    Azure 認証用 TokenCredential を返す。

    mode:
      - "auto": Managed Identity -> Service Principal(env) -> Azure CLI
      - "mi":   Managed Identity のみ
      - "sp":   Service Principal のみ
      - "cli":  Azure CLI のみ
    """
    mode = (mode or "auto").lower()

    if mode == "mi":
        return ManagedIdentityCredential()

    if mode == "sp":
        return ClientSecretCredential(
            tenant_id=os.environ["AZURE_TENANT_ID"],
            client_id=os.environ["AZURE_CLIENT_ID"],
            client_secret=os.environ["AZURE_CLIENT_SECRET"],
        )

    if mode == "cli":
        return AzureCliCredential()

    # auto: MI -> SP(env) -> CLI
    parts: List[TokenCredential] = [
        ManagedIdentityCredential()
    ]

    if all(
        key in os.environ
        for key in ("AZURE_TENANT_ID", "AZURE_CLIENT_ID", "AZURE_CLIENT_SECRET")
    ):
        parts.append(
            ClientSecretCredential(
                tenant_id=os.environ["AZURE_TENANT_ID"],
                client_id=os.environ["AZURE_CLIENT_ID"],
                client_secret=os.environ["AZURE_CLIENT_SECRET"],
            )
        )

    parts.append(AzureCliCredential())

    return ChainedTokenCredential(*parts)
