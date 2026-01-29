# app/core/license_models.py
from pydantic import BaseModel, Field
from typing import List, Optional, Literal


class LicenseSummaryRequest(BaseModel):
    """ライセンス本文から要点抽出を依頼するリクエスト"""
    software_name: Optional[str] = Field(None, description="ソフトウェア名")
    license_text: str = Field(..., description="ライセンステキスト原文")


class LicenseSummary(BaseModel):
    """LLM が生成するライセンス要約（構造化）"""
    commercial_use: Literal["allowed", "restricted", "prohibited", "unknown"]
    redistribution: Literal["allowed", "restricted", "prohibited", "unknown"]
    modification: Literal["allowed", "restricted", "prohibited", "unknown"]
    credit_required: bool
    copyleft: bool
    # ★ ここから追加 ★
    license_cost: Literal[
        "free",      # 無償
        "paid",      # 有償（費用が必要）
        "mixed",     # 条件によって有償/無償が分かれる（例：非商用は無料）
        "unknown",   # 読み取れない / 曖昧
    ]
    # ★ ここまで追加 ★
    key_conditions: List[str]
    risk_points: List[str]


class LicenseSummaryResponse(BaseModel):
    """ライセンスの要約出力"""
    summary: LicenseSummary
    raw_output: str  # LLM の生出力（デバッグ／確認用）


class LicenseJudgeRequest(BaseModel):
    """利用シナリオと要約を元に商用利用可否を判定するリクエスト"""
    software_name: Optional[str] = None
    usage_type: Literal["internal", "product", "saas", "redistribution"]
    license_summary: LicenseSummary


class LicenseJudgeResult(BaseModel):
    """商用利用可否判定結果"""
    is_allowed: bool
    level: Literal["ok", "conditional", "ng", "unknown"]
    reasons: List[str]
    conditions: List[str]


class LicenseJudgeResponse(BaseModel):
    """判定結果レスポンス"""
    result: LicenseJudgeResult
    raw_output: str
