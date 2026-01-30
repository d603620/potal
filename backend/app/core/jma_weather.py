from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple
import requests

AREA_JSON_URL = "https://www.jma.go.jp/bosai/common/const/area.json"
FORECAST_URL_TMPL = "https://www.jma.go.jp/bosai/forecast/data/forecast/{office}.json"
ICON_URL_TMPL = "https://www.jma.go.jp/bosai/forecast/img/{code}.svg"

def load_area() -> Dict[str, Any]:
    r = requests.get(AREA_JSON_URL, timeout=10)
    r.raise_for_status()
    return r.json()

def fetch_forecast(office_code: str) -> List[Dict[str, Any]]:
    r = requests.get(FORECAST_URL_TMPL.format(office=office_code), timeout=10)
    r.raise_for_status()
    return r.json()

def _as_int_or_none(x: Any) -> Optional[int]:
    try:
        if x is None:
            return None
        s = str(x).strip().replace("%", "")
        if s in ("", "-", "NaN", "nan"):
            return None
        return int(float(s))
    except Exception:
        return None

def extract_pref_summary(forecast_json: List[Dict[str, Any]]) -> Dict[str, Any]:
    # 3_Wether_AI.py と同等の「揺れに強い」抽出（today/tomorrow/pops/temps/timeDefines）:contentReference[oaicite:7]{index=7}
    out = {
        "today": {"weather": None, "weather_code": None, "pops": [], "temps": {}},
        "tomorrow": {"weather": None, "weather_code": None, "pops": [], "temps": {}},
        "timeDefines": [],
        "detail": {},
    }
    if not forecast_json:
        return out

    ts_list = (forecast_json[0].get("timeSeries") or [])
    for ts in ts_list:
        areas = ts.get("areas") or []
        if not areas:
            continue
        a0 = areas[0]

        if "weathers" in a0:
            ws = a0["weathers"]
            if len(ws) >= 1: out["today"]["weather"] = ws[0]
            if len(ws) >= 2: out["tomorrow"]["weather"] = ws[1]
        if "weatherCodes" in a0:
            wc = a0["weatherCodes"]
            if len(wc) >= 1: out["today"]["weather_code"] = wc[0]
            if len(wc) >= 2: out["tomorrow"]["weather_code"] = wc[1]

        if "pops" in a0:
            pops = a0["pops"]
            half = len(pops) // 2 if len(pops) > 1 else len(pops)
            out["today"]["pops"] = pops[:half]
            out["tomorrow"]["pops"] = pops[half:]
            out["timeDefines"] = ts.get("timeDefines", [])

        if "temps" in a0:
            t = a0["temps"]
            if len(t) > 0: out["today"]["temps"]["t0"] = t[0]
            if len(t) > 1: out["tomorrow"]["temps"]["t0"] = t[1]

        for k in ("winds", "waves", "reliabilities"):
            if k in a0:
                out["detail"][k] = a0[k]

    return out

def build_pop_rows(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    time_defines = data.get("timeDefines") or []
    pops_today = (data.get("today") or {}).get("pops") or []
    pops_tomorrow = (data.get("tomorrow") or {}).get("pops") or []

    if not time_defines:
        rows: List[Dict[str, Any]] = []
        for i, p in enumerate(pops_today):
            rows.append({"day": "today", "slot": f"slot{i+1}", "pop": _as_int_or_none(p)})
        for i, p in enumerate(pops_tomorrow):
            rows.append({"day": "tomorrow", "slot": f"slot{i+1}", "pop": _as_int_or_none(p)})
        return rows

    half = len(time_defines) // 2 if len(time_defines) > 1 else len(time_defines)
    td_today = time_defines[:half]
    td_tomorrow = time_defines[half:]

    rows: List[Dict[str, Any]] = []
    for i, t in enumerate(td_today):
        p = pops_today[i] if i < len(pops_today) else None
        rows.append({"day": "today", "slot": t, "pop": _as_int_or_none(p)})

    for i, t in enumerate(td_tomorrow):
        p = pops_tomorrow[i] if i < len(pops_tomorrow) else None
        rows.append({"day": "tomorrow", "slot": t, "pop": _as_int_or_none(p)})

    # ズレ吸収
    if len(pops_today) > len(td_today):
        for i in range(len(td_today), len(pops_today)):
            rows.append({"day": "today", "slot": f"slot{i+1}", "pop": _as_int_or_none(pops_today[i])})
    if len(pops_tomorrow) > len(td_tomorrow):
        for i in range(len(td_tomorrow), len(pops_tomorrow)):
            rows.append({"day": "tomorrow", "slot": f"slot{i+1}", "pop": _as_int_or_none(pops_tomorrow[i])})

    return rows

def max_pop_by_day(data: Dict[str, Any]) -> Tuple[Optional[int], Optional[int]]:
    def m(pops: List[Any]) -> Optional[int]:
        vals = [_as_int_or_none(p) for p in pops]
        vals2 = [v for v in vals if v is not None]
        return max(vals2) if vals2 else None

    tmax = m((data.get("today") or {}).get("pops") or [])
    tomax = m((data.get("tomorrow") or {}).get("pops") or [])
    return tmax, tomax

def icon_url(weather_code: Optional[str]) -> Optional[str]:
    return ICON_URL_TMPL.format(code=weather_code) if weather_code else None
