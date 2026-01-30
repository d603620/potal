# 服装アドバイス生成ロジック
from __future__ import annotations
import os
import json
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv
from app.core.azure_openai_client import call_chat_text

# Azure OpenAI はオプショナル
try:
    from openai import AzureOpenAI  # type: ignore
except Exception:  # ランタイムに無い場合もある
    AzureOpenAI = None  # type: ignore

def _to_float(x: Any) -> Optional[float]:
    try:
        if x is None:
            return None
        if isinstance(x, (int, float)):
            return float(x)
        s = str(x).strip().replace('℃', '').replace(
            '%', '').replace('－', '-').replace('—', '-')
        if s in ('', '-', 'NaN', 'nan'):
            return None
        return float(s)
    except Exception:
        return None


def _max_numeric(values: List[Any]) -> Optional[float]:
    nums: List[float] = []
    for v in values:
        fv = _to_float(v)
        if fv is not None:
            nums.append(fv)
    return max(nums) if nums else None


def _guess_day_temp(data: Dict[str, Any]) -> Optional[float]:
    # JMA の配列は揺れがあるため、今日の temps のうち最初の数値を採用
    today = (data or {}).get("today", {})
    temps = (today or {}).get("temps", {})
    # 代表値として t0 を優先し、無ければ最初に見つかった数値
    for key in ("t0", "max", "min"):
        if key in temps:
            v = _to_float(temps.get(key))
            if v is not None:
                return v
    # 念のため他の値も総なめ
    for v in (temps.values() if isinstance(temps, dict) else []):
        fv = _to_float(v)
        if fv is not None:
            return fv
    return None


def _rain_gear_tip(max_pop: Optional[float]) -> Optional[str]:
    if max_pop is None:
        return None
    if max_pop >= 70:
        return "降水確率が高めです。レインジャケットや防水シューズ、折りたたみでない傘を準備しましょう。"
    if max_pop >= 50:
        return "雨の可能性があります。軽量の雨具や防水バッグカバーがあると安心です。"
    if max_pop >= 30:
        return "にわか雨の可能性があります。小さめの折りたたみ傘を携帯すると安心です。"
    return None


def _wind_tip(winds: List[str]) -> Optional[str]:
    text = " ".join(winds) if winds else ""
    if any(ch in text for ch in ["強", "非常に強い", "やや強い"]):
        return "風が強めの見込みです。フード付きアウターや風を通しにくい素材を選びましょう。"
    return None


def _uv_tip(today_weather: str) -> Optional[str]:
    # 簡易的: 「晴」含むときに UV 注意
    if today_weather and any(tok in today_weather for tok in ["晴", "快晴"]):
        return "日差しが強い時間帯があります。サングラスや帽子、日焼け止めの準備を。"
    return None


def _layering_by_temp(t: Optional[float]) -> str:
    if t is None:
        return "気温情報が不十分のため、重ね着で調整できる服装をおすすめします。"
    if t >= 28:
        return "かなり暑いです。半袖の軽装（通気性のよいTシャツ、リネン素材）＋薄手のボトムスがおすすめ。"
    if 23 <= t < 28:
        return "暖かい時期です。半袖〜薄手の長袖。冷房対策に薄手の羽織りがあると安心。"
    if 18 <= t < 23:
        return "過ごしやすい体感。長袖シャツや薄手ニット、ライトアウターで調整を。"
    if 12 <= t < 18:
        return "やや肌寒いです。長袖＋カーディガン／ライトジャケット、薄手のスカーフも◎。"
    if 7 <= t < 12:
        return "肌寒い〜寒い体感。中厚手のアウターやスウェット、インナーで保温を。"
    if 0 <= t < 7:
        return "寒いです。コートや中綿ジャケット、マフラー・手袋などの防寒小物を。"
    return "非常に寒いです。厚手のコートやダウン、保温インナー＋防風素材でしっかり防寒を。"


def _compose_markdown(pref_name: str, data: Dict[str, Any]) -> str:
    today = (data or {}).get("today", {})
    tomorrow = (data or {}).get("tomorrow", {})
    today_weather = today.get("weather") or ""
    tomorrow_weather = tomorrow.get("weather") or ""
    max_pop = _max_numeric(today.get("pops", []) or [])
    day_temp = _guess_day_temp(data)

    lines: List[str] = []
    lines.append(f"### 👕 {pref_name} — 今日の服装アドバイス")
    lines.append("")
    # コア提案（気温）
    lines.append(
        f"- **気温の目安**: {day_temp:.0f}℃ 前後" if day_temp is not None else "- **気温の目安**: 取得できませんでした")
    if today_weather:
        lines.append(f"- **天気**: {today_weather}")
    if max_pop is not None:
        lines.append(f"- **降水確率(最大)**: {int(max_pop)}%")
    lines.append("")
    # レイヤリング提案
    lines.append(_layering_by_temp(day_temp))
    # 追加 Tips
    tip_rain = _rain_gear_tip(max_pop)
    tip_wind = _wind_tip((data.get("detail", {}) or {}).get("winds", []) or [])
    tip_uv = _uv_tip(today_weather)
    extra = [t for t in [tip_rain, tip_wind, tip_uv] if t]
    if extra:
        lines.append("")
        lines.append("**ひとことメモ**")
        for t in extra:
            lines.append(f"- {t}")

    # 明日の簡易メモ（あれば）
    if tomorrow_weather:
        lines.append("")
        lines.append(f"> 明日の見通し: {tomorrow_weather}")

    return "\n".join(lines)


def _azure_refine(md_text: str, pref_name: str) -> Optional[str]:
    system = "あなたは衣服コーディネートの助言を日本語で簡潔に整える編集者です。専門用語を避け、Markdownは保ちます。"
    user = {"prefecture": pref_name, "markdown": md_text}

    try:
        out = call_chat_text(system, json.dumps(user, ensure_ascii=False))
        return out.strip() or None
    except Exception:
        return None

def get_clothing_advice_markdown(pref_name: str, data: Dict[str, Any], use_azure: bool = True) -> str:
    """服装アドバイスを Markdown で返すメイン関数。"""
    base = _compose_markdown(pref_name or "選択地域", data or {})
    if not use_azure:
        return base
    refined = _azure_refine(base, pref_name or "選択地域")
    return refined or base


__all__ = ["get_clothing_advice_markdown"]
