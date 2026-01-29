# backend/app/core/kpi_analyzer_core.py
from __future__ import annotations
import io
import os
from datetime import datetime
from typing import Any, Dict

import pandas as pd
from openai import AzureOpenAI

# CSV列名（固定）
DATE_COL = "date"
UPTIME_COL = "uptime_rate"
THROUGHPUT_COL = "throughput_per_hr"
DOWNTIME_COL = "downtime_min"
DEFECT_COL = "defect_rate_pct"
ENERGY_COL = "energy_kwh"
PROFIT_COL = "profit_yen"


def load_csv(file_bytes: bytes, encoding: str = "utf-8") -> pd.DataFrame:
    """アップロードされたCSVバイト列をDataFrameに変換"""
    buf = io.BytesIO(file_bytes)
    df = pd.read_csv(buf, encoding=encoding)

    # 必須列チェック
    required_cols = {
        DATE_COL,
        UPTIME_COL,
        THROUGHPUT_COL,
        DOWNTIME_COL,
        DEFECT_COL,
        ENERGY_COL,
        PROFIT_COL,
    }
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(
            "CSVに必要な列が不足しています。\n"
            f"必要列: {', '.join(sorted(required_cols))}\n"
            f"不足列: {', '.join(sorted(missing))}"
        )

    # 日付列を datetime 化
    df[DATE_COL] = pd.to_datetime(df[DATE_COL])
    df = df.sort_values(DATE_COL).reset_index(drop=True)
    return df


def calc_kpis(df: pd.DataFrame) -> dict:
    """最新と1週間前の主要KPI・差分を計算"""
    df = df.copy()
    df[DATE_COL] = pd.to_datetime(df[DATE_COL])

    latest = df.iloc[-1]
    prev = df.iloc[-8] if len(df) >= 8 else df.iloc[0]

    # Pylance が誤認識するため ignore
    latest_date = latest[DATE_COL].strftime("%Y-%m-%d")  # type: ignore
    prev_date = prev[DATE_COL].strftime("%Y-%m-%d")      # type: ignore

    def diff(col: str) -> float:
        return float(latest[col] - prev[col])

    result = {
        "latest_date": latest_date,
        "prev_date": prev_date,

        "uptime_rate_latest": float(latest[UPTIME_COL]),
        "uptime_rate_diff": diff(UPTIME_COL),

        "throughput_latest": float(latest[THROUGHPUT_COL]),
        "throughput_diff": diff(THROUGHPUT_COL),

        "downtime_latest": float(latest[DOWNTIME_COL]),
        "downtime_diff": diff(DOWNTIME_COL),

        "defect_latest": float(latest[DEFECT_COL]),
        "defect_diff": diff(DEFECT_COL),

        "energy_latest": float(latest[ENERGY_COL]),
        "energy_diff": diff(ENERGY_COL),

        "profit_latest": float(latest[PROFIT_COL]),
        "profit_diff": diff(PROFIT_COL),
    }

    return result


def build_chart_data(df: pd.DataFrame) -> Dict[str, Any]:
    """React 用のグラフデータ形式に変換"""
    dates = df[DATE_COL].dt.strftime("%Y-%m-%d").tolist()  # type: ignore

    return {
        "dates": dates,
        "series": {
            "uptime_rate": df[UPTIME_COL].tolist(),
            "throughput_per_hr": df[THROUGHPUT_COL].tolist(),
            "downtime_min": df[DOWNTIME_COL].tolist(),
            "defect_rate_pct": df[DEFECT_COL].tolist(),
            "energy_kwh": df[ENERGY_COL].tolist(),
            "profit_yen": df[PROFIT_COL].tolist(),
        },
    }


def call_azure_reasoning(summary_text: str) -> str:
    """Azure OpenAI を呼んで要因説明を生成（Azure AD 認証）"""
    endpoint = os.getenv("API_AZURE_OPENAI_ENDPOINT")
    api_version = os.getenv("API_AZURE_OPENAI_API_VERSION")
    deployment = os.getenv("API_AZURE_OPENAI_DEPLOYMENT", "gpt-5")

    # API Key は不要になる（従来互換のため未設定でもOK）
    if not (endpoint and api_version):
        return "Azure OpenAI の設定がないため、自動要因説明はスキップされました。"

    # dnp_azure_auth を利用
    from dnp_azure_auth.config import AzureOpenAIConfig
    from dnp_azure_auth.credential import get_credential

    # scope はライブラリ既定に合わせる（Azure OpenAI 用）
    cfg = AzureOpenAIConfig(
        endpoint=endpoint,
        deployment=deployment,
        api_version=api_version,
    )

    auth_mode = os.getenv("AZURE_AUTH_MODE", "auto")  # auto | mi | sp | cli
    cred = get_credential(auth_mode)

    def azure_ad_token_provider() -> str:
        return cred.get_token(cfg.scope).token

    # ★ここで client を必ず定義
    client = AzureOpenAI(
        azure_endpoint=cfg.endpoint,
        api_version=cfg.api_version,
        azure_ad_token_provider=azure_ad_token_provider,
    )

    prompt = f"""
    あなたは製造業の経営指標・生産指標の分析コンサルタントです。
    以下のKPIサマリーを読み、変化の主な要因を簡潔に説明してください。

    KPI概要:
    {summary_text}
    """

    # ★responses ではなく chat.completions を使う
    resp = client.chat.completions.create(
        model=deployment,  # Azureでは deployment 名
        messages=[{"role": "user", "content": prompt}],
        # temperature=1.0,
        # max_tokens=600,
    )

    try:
        return resp.choices[0].message.content or ""
    except Exception as e:
        return f"Azure OpenAI のレスポンス解析中にエラーが発生しました: {e}"
