# app/core/license_logic.py
import json

from .license_models import (
    LicenseSummaryRequest,
    LicenseSummaryResponse,
    LicenseSummary,
    LicenseJudgeRequest,
    LicenseJudgeResponse,
    LicenseJudgeResult,
)
from .azure_openai_client import call_chat
from app.services.license_fetch_service import fetch_license_text_from_web  # ★追加

def summarize_license_logic(req: LicenseSummaryRequest) -> LicenseSummaryResponse:
    """
    ライセンステキストから商用利用に関係する要点を抽出し、構造化して返すロジック。
    """
    system_prompt = """
    あなたは企業のソフトウェアライセンス審査を支援するAIです。
    以下のライセンステキストを読み取り、商用利用に関係する要点を
    JSON 形式で構造化して日本語で出力してください。

    出力形式（厳守）:
    {
    "commercial_use": "allowed | restricted | prohibited | unknown",
    "redistribution": "allowed | restricted | prohibited | unknown",
    "modification": "allowed | restricted | prohibited | unknown",
    "credit_required": true/false,
    "copyleft": true/false,
    "license_cost": "free | paid | mixed | unknown",
    "key_conditions": ["..."],
    "risk_points": ["..."]
    }

    解釈の目安:
    - license_cost = "free": 無償利用が前提のOSSライセンスであり、有償ライセンスに関する記載がない場合
    - license_cost = "paid": ライセンス料や使用料の支払いが必要である旨が明記されている場合
    - license_cost = "mixed": 非商用は無料、商用は有償契約が必要など、条件で分かれている場合
    - license_cost = "unknown": テキストから判断できない・不明な場合
    """


    user_prompt = f"""
ソフトウェア名: {req.software_name}
ライセンステキスト:
{req.license_text}
"""

    raw = call_chat(system_prompt, user_prompt)

    try:
        data = json.loads(raw)
        summary = LicenseSummary(**data)
    except Exception:
        # JSON 解析に失敗した場合でも、API が落ちないように unknown で埋める
        summary = LicenseSummary(
            commercial_use="unknown",
            redistribution="unknown",
            modification="unknown",
            credit_required=False,
            copyleft=False,
            license_cost="unknown",
            key_conditions=[],
            risk_points=["LLM の出力が JSON として解析できませんでした"],
        )

    return LicenseSummaryResponse(summary=summary, raw_output=raw)


def judge_license_logic(req: LicenseJudgeRequest) -> LicenseJudgeResponse:
    """
    ライセンス要約と利用形態から商用利用可否を判定するロジック。
    """
    system_prompt = """
あなたは企業のライセンス審査担当です。
与えられたライセンス要約と利用形態から、商用利用可否を
以下の JSON 形式で日本語で出力してください。
判定理由には可能なら根拠となる公式ドキュメントやライセンス原文の URL も含めること

{
  "is_allowed": true/false,
  "level": "ok | conditional | ng | unknown",
  "reasons": ["..."],
  "conditions": ["..."]
  "url": "参考URL（もしあれば）"
}

判断基準:
- 商用利用に制限がある場合 → conditional
- 明確に禁止される場合 → ng
- 情報不足・曖昧 → unknown
最終的な法的判断は人間が行う前提で、慎重にフラグを立ててください。
"""

    summary_json = json.dumps(
        req.license_summary.model_dump(),  # Pydantic v2 で dict 取得
        indent=2,
        ensure_ascii=False,
    )
    
    user_prompt = f"""
    ソフトウェア名: {req.software_name}
    利用形態: {req.usage_type}

    ライセンスの要約(JSON):
    {summary_json}
    """

    raw = call_chat(system_prompt, user_prompt)

    try:
        data = json.loads(raw)
        result = LicenseJudgeResult(**data)
    except Exception:
        result = LicenseJudgeResult(
            is_allowed=False,
            level="unknown",
            reasons=["LLM の JSON 出力解析に失敗しました"],
            conditions=[],
        )

    return LicenseJudgeResponse(result=result, raw_output=raw)
