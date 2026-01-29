# app/routers/json_agent.py
from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
from typing import Optional

# ❌ 間違い:
# from backend.app.core.logic_core import ( ... )

# ✅ 正しい import（パッケージ名は「app」）
from app.core.logic_core import (
    extract_text_from_upload,
    generate_json_draft,
    unified_diff_text,
    load_tree_text,
    hitei_dedupe_and_extract,
)

router = APIRouter(prefix="/api", tags=["json-agent"])


class GenerateRequest(BaseModel):
    po_text: str
    hitei_text: str
    instruction: Optional[str] = None


class DiffRequest(BaseModel):
    current_json: dict
    preview_json: dict


@router.get("/tree")
def get_tree():
    """tree.txt がなくても固定メッセージを返す"""
    try:
        return {"text": load_tree_text()}
    except FileNotFoundError:
        return {"text": "(tree.txt は作成されていません)"}


@router.post("/parse")
async def parse_file(file: UploadFile = File(...)):
    try:
        text = await extract_text_from_upload(file)
        return {"ok": True, "text": text}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"parse failed: {e}")


@router.post("/hitei-dedupe")
async def hitei_dedupe(file: UploadFile = File(...)):
    try:
        text, message = await hitei_dedupe_and_extract(file)
        return {"ok": True, "text": text, "message": message}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"hitei-dedupe failed: {e}")


@router.post("/generate")
async def generate(req: GenerateRequest):
    try:
        data = generate_json_draft(req.po_text, req.hitei_text, req.instruction)
        return {"ok": True, "data": data}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"generate failed: {e}")


@router.post("/diff")
async def diff(req: DiffRequest):
    try:
        text = unified_diff_text(req.current_json, req.preview_json)
        return {"ok": True, "diff": text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"diff failed: {e}")
