import os
import re
from openai import AzureOpenAI

from dnp_azure_auth.config import load_azure_openai_config
from dnp_azure_auth.credential import get_credential

#REQUIRED_FROM = "FROM USK_DBA.V_製造2部工票稼働"
REQUIRED_FROM = os.getenv("ORACLE_ALLOWED_OBJECTS","")


# ===== Azure OpenAI config (env) =====
cfg = load_azure_openai_config(
    endpoint_env="API_AZURE_OPENAI_ENDPOINT",
    deployment_env="API_AZURE_OPENAI_DEPLOYMENT",
    api_version_env="API_AZURE_OPENAI_API_VERSION",
)

# ===== Azure AD auth (dnp_azure_auth) =====
# mode: auto | mi | sp | cli
auth_mode = os.getenv("AZURE_AUTH_MODE", "auto")
cred = get_credential(auth_mode)


def azure_ad_token_provider() -> str:
    """
    AzureOpenAI(azure_ad_token_provider=...) 用。
    返り値は access token の文字列。
    """
    return cred.get_token(cfg.scope).token


client = AzureOpenAI(
    azure_endpoint=cfg.endpoint,
    api_version=cfg.api_version or "2024-10-21",
    azure_ad_token_provider=azure_ad_token_provider,
)

DEPLOYMENT = cfg.deployment


def generate_sql(question: str, schema_context: str) -> str:
    system_prompt = f"""
You are an Oracle SQL generator.

{schema_context}

STRICT RULES:
- Output ONLY one SQL statement
- Use exactly this FROM clause:
  {REQUIRED_FROM}
- Do NOT use any other table or view
- Do NOT use JOIN
- Do NOT output explanations or comments
- Do NOT use DML or DDL
"""

    response = client.chat.completions.create(
        model=DEPLOYMENT,
        temperature=1.0,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question},
        ],
    )

    content = response.choices[0].message.content
    if content is None:
        raise ValueError("LLM returned empty content")

    sql = _sanitize_sql(content)
    _validate_sql(sql)
    return sql


def _sanitize_sql(text: str) -> str:
    """
    LLMが ```sql ... ``` や "SQL:" を付けて返すことがあるので除去。
    末尾の ; も落とす。
    """
    s = (text or "").strip()
    s = re.sub(r"^```(?:sql)?\s*", "", s, flags=re.IGNORECASE)
    s = re.sub(r"\s*```$", "", s)
    s = re.sub(r"^\s*SQL\s*:\s*", "", s, flags=re.IGNORECASE)
    return s.strip().rstrip(";")


def _validate_sql(sql: str) -> None:
    s = " ".join(sql.split())

    # FROM句固定
    if REQUIRED_FROM.upper() not in s.upper():
        raise ValueError(f"SQL must use only: {REQUIRED_FROM}")

    # JOIN禁止
    if re.search(r"\bJOIN\b", s, flags=re.IGNORECASE):
        raise ValueError("JOIN is not allowed")

    # FROMは1回のみ
    if len(re.findall(r"\bFROM\b", s, flags=re.IGNORECASE)) != 1:
        raise ValueError("Only one FROM clause is allowed")

    # 危険語
    if re.search(
        r"\b(INSERT|UPDATE|DELETE|MERGE|ALTER|DROP|CREATE|TRUNCATE|EXEC|BEGIN)\b",
        s,
        flags=re.IGNORECASE,
    ):
        raise ValueError("DML/DDL is not allowed")
