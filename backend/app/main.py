# app/main.py
from __future__ import annotations
from pathlib import Path
from dotenv import load_dotenv
# ① .env を読み込む
#   - プロジェクトルート（backend ディレクトリの1つ上）に .env がある想定
BASE_DIR = Path(__file__).resolve().parent  # app/ の1つ上 (backend/)
DOTENV_PATH = BASE_DIR / ".env"
load_dotenv(DOTENV_PATH)  # ここでロード


import io
import os
from typing import List, Optional
from fastapi.staticfiles import StaticFiles

from fastapi import HTTPException
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.core.logic_core import extract_text_from_upload  # 追加
from app.routers import auth, api, chatpod_router
from app.routers import json_agent
from app.routers import excel as excel_router
from app.routers import trouble
from app.routers import kpi_analyzer
from app.core import config
from app.routers import scenario as scenario_router
from app.routers import data as data_router
from app.routers import oracle_nlq  # 追加
from app.routers import oracle_diag
from app.routers import auth
from app.routers import clothing
from app.routers import weather as weather_router
 

from app.core.license_models import (
    LicenseSummaryRequest,
    LicenseSummaryResponse,
    LicenseJudgeRequest,
    LicenseJudgeResponse,
)
from app.core.license_logic import (
    summarize_license_logic,
    judge_license_logic,
)
# 既存ルーターがある場合のみ取り込む（無ければスキップして起動できるように）
def _optional_import(module_path: str, attr: str):
    try:
        mod = __import__(module_path, fromlist=[attr])
        return getattr(mod, attr)
    except Exception:
        return None

auth_router = _optional_import("app.routers.auth", "router")
api_router = _optional_import("app.routers.api", "router")
chatpod_router = _optional_import("app.routers.chatpod_router", "router")


app = FastAPI(title="Portal Backend", version="0.1.0")

# --- CORS ---
# 複数フロントから叩く可能性を考慮し、環境変数 OR デフォルト
default_origins = ["http://localhost:5173", "http://127.0.0.1:5173", "http://10.178.7.4:5173", "http://10.178.7.4"]
allow_origins: List[str] = (
    os.getenv("CORS_ALLOW_ORIGINS", ",".join(default_origins)).split(",")
    if os.getenv("CORS_ALLOW_ORIGINS")
    else default_origins
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in allow_origins],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Routers ---
if auth_router:
    app.include_router(auth.router, tags=["auth"])
if api_router:
    app.include_router(api_router, prefix="/api", tags=["api"])
if chatpod_router:
    app.include_router(chatpod_router)
if json_agent:
    app.include_router(json_agent.router) 
if excel_router:
    app.include_router(excel_router.router)
if trouble:
    app.include_router(trouble.router, prefix="/api", tags=["trouble"])
if kpi_analyzer:
    app.include_router(kpi_analyzer.router, prefix="/api", tags=["kpi"])
if scenario_router:
    app.include_router(scenario_router.router, prefix="/api", tags=["scenario"])
if data_router:
    app.include_router(data_router.router, prefix="/api", tags=["data"])
if oracle_nlq:
    app.include_router(oracle_nlq.router, prefix="/api", tags=["oracle-nlq"])  # 追加
if oracle_diag:
    app.include_router(oracle_diag.router, prefix="/api", tags=["oracle-diag"])
if clothing:
    app.include_router(clothing.router, prefix="/api", tags=["clothing"])
if weather_router:
    app.include_router(weather_router.router, prefix="/api", tags=["weather"])
    

# --- Health ---
@app.get("/health", tags=["system"])
def health() -> dict:
    return {"status": "ok"}

# --- CSV / Excel の軽量プレビュー ---
def _read_excel_or_csv(bio: io.BytesIO, ext: str) -> str:
    """
    CSVならそのまま、Excelなら各シートを縦結合してCSV文字列にして返却。
    依存は pandas のみ。pandas が無い環境では 500 を返す。
    """
    try:
        import pandas as pd  # type: ignore
    except Exception as e:  # pragma: no cover
        raise HTTPException(status_code=500, detail=f"pandas not available: {e}")

    bio.seek(0)

    if ext.lower() == ".csv":
        try:
            df = pd.read_csv(bio)
            return df.to_csv(index=False)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"CSV parse error: {e}")

    # Excel
    try:
        xls = pd.ExcelFile(bio)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Excel open error: {e}")

    frames = []
    for sheet in xls.sheet_names:
        try:
            df = xls.parse(sheet)
            df.insert(0, "__sheet__", sheet)
            frames.append(df)
        except Exception as e:
            # 1 シートが壊れても他は読む
            frames.append(pd.DataFrame({"__sheet__": [sheet], "__error__": [str(e)]}))

    if not frames:
        raise HTTPException(status_code=400, detail="No sheets found")

    try:
        merged = pd.concat(frames, ignore_index=True)
        return merged.to_csv(index=False)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Excel concat error: {e}")

@app.post("/files/preview", tags=["files"])
async def preview_file(file: UploadFile = File(...)) -> dict:
    """
    フロントからの簡易プレビュー用途:
      - CSV: そのまま CSV を戻す
      - XLSX/XLS: 全シートを縦連結し CSV で戻す（先頭列に __sheet__ を付与）
    レスポンスは最初の 5,000 文字まで返却（UI 側で続きを要求するならエンドポイント分離推奨）
    """
    name = file.filename or "uploaded"
    _, ext = os.path.splitext(name)
    ext = ext.lower()

    if ext not in {".csv", ".xlsx", ".xls"}:
        raise HTTPException(status_code=415, detail=f"unsupported type: {ext}")

    try:
        raw = await file.read()
    finally:
        await file.close()

    csv_text = _read_excel_or_csv(io.BytesIO(raw), ext)
    head = csv_text[:5000]
    return {"name": name, "ext": ext, "preview_csv": head, "truncated": len(csv_text) > len(head)}

# --- 起動ランナー（直接実行用） ---
if __name__ == "__main__":
    import uvicorn  # type: ignore
    uvicorn.run(
        "app.main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
        reload=os.getenv("RELOAD", "1") == "1",
    )

@app.post("/api/parse", operation_id="parse_file_upload_post",tags=["files"])
async def parse_file(file: UploadFile = File(...)) -> dict:
    try:
        text = await extract_text_from_upload(file)
        return {"ok": True, "text": text}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"parse failed: {e}")
    

@app.post("/api/license/summary", response_model=LicenseSummaryResponse, tags=["license"])
async def summarize_license(req: LicenseSummaryRequest) -> LicenseSummaryResponse:
    """
    ライセンステキストから商用利用に関係する要点を抽出し、構造化して返す API。
    ロジック自体は app.core.license_logic に委譲。
    """
    try:
        return summarize_license_logic(req)
    except RuntimeError as e:
        # Azure OpenAI 未設定など、core 側からのエラーを HTTP に変換
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/license/judge", response_model=LicenseJudgeResponse, tags=["license"])
async def judge_license(req: LicenseJudgeRequest) -> LicenseJudgeResponse:
    """
    ライセンス要約と利用形態から、商用利用可否を判定する API。
    """
    try:
        return judge_license_logic(req)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    