from __future__ import annotations
from typing import Any, Dict, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.jma_weather import load_area, fetch_forecast, extract_pref_summary, build_pop_rows, max_pop_by_day, icon_url
from app.core.weather_summary import azure_summary

router = APIRouter()

class WeatherSummaryRequest(BaseModel):
    # 最小セット：destination を受け、バックエンドで office_code を決める
    destination: str

class WeatherSummaryResponse(BaseModel):
    pref_name: str
    office_code: str
    data: Dict[str, Any]
    summary: str
    pop_rows: list[dict]
    max_pop_today: Optional[int]
    max_pop_tomorrow: Optional[int]
    icon_today: Optional[str]
    icon_tomorrow: Optional[str]

def _normalize(s: str) -> str:
    return s.strip().lower().replace("都", "").replace("道", "").replace("府", "").replace("県", "")

def _guess_office_from_destination(dest: str, offices: Dict[str, Any]) -> Optional[tuple[str, str]]:
    nd = _normalize(dest)
    # まず office name 部分一致
    for code, info in offices.items():
        name = info.get("name") or str(code)
        if _normalize(name) in nd or nd in _normalize(name):
            return (name, code)

    # 3_Wether_AI.py と同様に別名マップ（必要に応じて拡張）:contentReference[oaicite:10]{index=10}
    aliases = {
        "東京": "東京都",
        "大阪": "大阪府",
        "京都": "京都府",
        "名古屋": "愛知県",
        "横浜": "神奈川県",
        "神戸": "兵庫県",
        "那覇": "沖縄県",
        "仙台": "宮城県",
        "広島": "広島県",
        "福岡": "福岡県",
        "松山": "愛媛県",
        "高松": "香川県",
        "稚内": "宗谷地方",
        "釧路": "釧路地方",
        "帯広": "十勝地方", 
        "大津": "滋賀県",
        "札幌": "石狩・空知・後志地方",
        "函館": "渡島・檜山地方",

    }
    # alias で name を当てて code を引く
    name_to_code = { (info.get("name") or ""): code for code, info in offices.items() }
    for k, v in aliases.items():
        if k in dest and v in name_to_code:
            return (v, name_to_code[v])

    return None

@router.post("/weather/summary", response_model=WeatherSummaryResponse, tags=["weather"])
def weather_summary(req: WeatherSummaryRequest) -> WeatherSummaryResponse:
    if not req.destination.strip():
        raise HTTPException(status_code=400, detail="destination is required")

    area = load_area()
    offices = area.get("offices") or {}

    match = _guess_office_from_destination(req.destination, offices)
    if match is None:
        raise HTTPException(status_code=404, detail="destination did not match any office")

    pref_name, office_code = match
    fj = fetch_forecast(office_code)
    data = extract_pref_summary(fj)

    summary = azure_summary(pref_name, data)
    rows = build_pop_rows(data)
    tmax, tomax = max_pop_by_day(data)

    icon_today = icon_url((data.get("today") or {}).get("weather_code"))
    icon_tomorrow = icon_url((data.get("tomorrow") or {}).get("weather_code"))

    return WeatherSummaryResponse(
        pref_name=pref_name,
        office_code=office_code,
        data=data,
        summary=summary,
        pop_rows=rows,
        max_pop_today=tmax,
        max_pop_tomorrow=tomax,
        icon_today=icon_today,
        icon_tomorrow=icon_tomorrow,
    )
