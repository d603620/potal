from __future__ import annotations
import json
import datetime as dt
from typing import Any, Dict

from app.core.azure_openai_client import call_chat_text

def azure_summary(pref_name: str, data: Dict[str, Any]) -> str:
    system_prompt = (
        "あなたは気象情報を分かりやすく要約するアシスタントです。"
        "以下の指示に従ってください："
        "・まず重要な警戒点や危険度を簡潔に示す。"
        "・続けて『今日』『明日』の見出しで箇条書きにより要点をまとめる。"
        "・可能なら降水確率のピーク帯や気温の目安を明示する。"
        "・最後に短い服装・外出のアドバイスを1〜2行で添える。"
        "・表現は中立的で読みやすい口調にする。"
        "・選択した地方の方言で回答する。"
    )
    payload = {
        "prefecture": pref_name,
        "today": data.get("today"),
        "tomorrow": data.get("tomorrow"),
        "timeDefines": data.get("timeDefines"),
        "issued_date": dt.date.today().isoformat(),
    }
    return call_chat_text(system_prompt, json.dumps(payload, ensure_ascii=False)).strip()
