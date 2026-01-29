import os
from collections import defaultdict, deque
from typing import Dict, List, Deque
from pathlib import Path

from dotenv import load_dotenv

from dnp_azure_auth.config import load_azure_openai_config
from dnp_azure_auth.credential import get_credential

# ===== 環境変数ロード =====
# .env の場所に応じて、ここは調整してください。
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)

# ===== Azure OpenAI 設定 & 認証（共通ライブラリ）=====
cfg = load_azure_openai_config(
    endpoint_env="API_AZURE_OPENAI_ENDPOINT",
    deployment_env="API_AZURE_OPENAI_DEPLOYMENT",
    api_version_env="API_AZURE_OPENAI_API_VERSION",
)

AZURE_ENDPOINT = cfg.endpoint
AZURE_DEPLOYMENT = cfg.deployment
AZURE_API_VERSION = cfg.api_version
AZURE_SCOPE = cfg.scope

# mode: auto / mi / sp / cli
AZURE_CREDENTIAL = get_credential(mode=os.getenv("AZURE_AUTH_MODE", "auto"))

# ==============================
#  セッションごとの会話履歴（インメモリ）
#  本番運用では Redis 等に置き換え推奨
# ==============================
SESSIONS: dict[str, Deque[Dict[str, str]]] = defaultdict(lambda: deque(maxlen=100))
SYSTEM_PROMPT = "あなたは有能なアシスタントです。すべて日本語で回答してください。"


def build_messages_for_model(
    history: Deque[Dict[str, str]],
    new_user_text: str,
) -> List[Dict[str, str]]:
    """
    history: user/assistant のみが入っている前提。
    system + history + 現在の user を組み立て、メッセージ数ベースで簡易トリム。
    """
    msgs: List[Dict[str, str]] = [{"role": "system", "content": SYSTEM_PROMPT}]
    msgs.extend(list(history))
    msgs.append({"role": "user", "content": new_user_text})

    MAX_MSGS = 40
    if len(msgs) > MAX_MSGS:
        head = msgs[0:1]      # system
        tail = msgs[-1:]      # 最新 user
        middle = msgs[1:-1]   # 既存履歴
        msgs = head + middle[-(MAX_MSGS - 2):] + tail

    return msgs
