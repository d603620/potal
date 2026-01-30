# app/routers/clothing.py
from __future__ import annotations
from typing import Any, Dict, Optional
from fastapi import APIRouter
from pydantic import BaseModel

from app.core.clothing_advice import get_clothing_advice_markdown  # パスは配置に合わせて調整

router = APIRouter()

class ClothingAdviceRequest(BaseModel):
    pref_name: str
    data: Dict[str, Any]              # JMA要約データ想定（today/tomorrow/detail など）
    use_azure: bool = True

class ClothingAdviceResponse(BaseModel):
    markdown: str

@router.post("/clothing/advice", response_model=ClothingAdviceResponse, tags=["clothing"])
def clothing_advice(req: ClothingAdviceRequest) -> ClothingAdviceResponse:
    md = get_clothing_advice_markdown(req.pref_name, req.data, use_azure=req.use_azure)
    return ClothingAdviceResponse(markdown=md)
