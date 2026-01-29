# backend/app/routers/trouble.py

from pathlib import Path
from typing import Optional, List, Any, Dict

from fastapi import APIRouter, Query, Body
import numpy as np        # ★ 追加
import pandas as pd       # ★ 追加
from app.core.trouble_search_core import (
    search_cases,
    record_feedback,
    append_tacit_knowledge,
    merge_approved_notes_into_meta,
    load_feedback_stats,
    load_tacit_knowledge,       # ★ 追加
    update_tacit_status,        # ★ 追加
)

router = APIRouter()

# ============================================
# 設定：各パスを調整する（必要なら環境変数でもOK）
# ============================================

INDEX_DIR = Path("data/index")       # trouble.faiss / metadata.parquet / config.pkl の場所
FEEDBACK_CSV = Path("data/search_feedback.csv")
TACIT_CSV = Path("data/tacit_knowledge.csv")


# ============================================
# 1. 検索 API
# ============================================

@router.get("/trouble/search")
def trouble_search(
    q: str = Query(..., description="検索クエリ"),
    years: Optional[int] = Query(None),
    severity_min: Optional[float] = Query(None),
    severity_max: Optional[float] = Query(None),
    products: Optional[List[str]] = Query(None),
    tags: Optional[List[str]] = Query(None),
    top_k: int = Query(20),
    alpha: float = Query(0.5),
):
    """
    トラブル事例検索 API
    """
    results = search_cases(
        INDEX_DIR,
        q,
        years=years,
        severity_min=severity_min,
        severity_max=severity_max,
        products=products,
        tags=tags,
        top_k=top_k,
        alpha=alpha,
    )
    return {"count": len(results), "results": results}


# ============================================
# 2. フィードバック登録
# ============================================

@router.post("/trouble/feedback")
def trouble_feedback(
    query: str = Body(...),
    case_id: Any = Body(...),
    helpful: bool = Body(...),
    solve_hours: Optional[float] = Body(None),
    extra: Optional[Dict[str, Any]] = Body(None),
):
    """
    検索結果に対するフィードバックを登録する
    """
    record_feedback(
        FEEDBACK_CSV,
        query=query,
        case_id=case_id,
        helpful=helpful,
        solve_hours=solve_hours,
        extra=extra,
    )
    return {"status": "ok"}


# ============================================
# 3. 暗黙知（タシット）登録
# ============================================

@router.post("/trouble/tacit")
def trouble_tacit(
    case_id: Any = Body(...),
    note: str = Body(...),
    category: Optional[str] = Body(None),
    author: Optional[str] = Body(None),
    approver: Optional[str] = Body(None),
    status: str = Body("pending"),
    extra: Optional[Dict[str, Any]] = Body(None),
):
    """
    暗黙知の登録（承認前の pending 状態）
    """
    append_tacit_knowledge(
        TACIT_CSV,
        case_id=case_id,
        note=note,
        category=category,
        author=author,
        approver=approver,
        status=status,
        extra=extra,
    )
    return {"status": "ok"}


# ============================================
# 暗黙知一覧取得（承認画面用）
# ============================================

import numpy as np
import pandas as pd
import math
...
@router.get("/trouble/tacit/list")
def trouble_tacit_list(
    status: Optional[str] = Query(None, description="フィルタするステータス（例: pending, approved）")
):
    """
    暗黙知CSVの一覧を返す。
    status が指定されていれば、そのステータスの行だけに絞る。
    """
    df = load_tacit_knowledge(TACIT_CSV)

    if status is not None and "status" in df.columns:
        df = df[df["status"] == status]

    # ★ JSON にできない値を潰す（inf/-inf → NaN）
    df = df.replace([np.inf, -np.inf], np.nan)

    # いったん Python の list[dict] に変換
    raw_records = df.to_dict(orient="records")

    # ★ NaN を None に変換（JSON で null になる）
    records = []
    for rec in raw_records:
        clean: Dict[Any, Any] = {}
        for k, v in rec.items():
            if isinstance(v, float) and math.isnan(v):
                clean[k] = None
            else:
                clean[k] = v
        records.append(clean)

    return {"count": len(records), "results": records}


# ============================================
# 暗黙知の承認（ステータス更新）
# ============================================

@router.post("/trouble/tacit/approve")
def trouble_tacit_approve(
    row_id: int = Body(..., embed=True, description="tacit_knowledge.csv 上の id"),
    approver: Optional[str] = Body(None, embed=True),
):
    """
    暗黙知1件のステータスを 'approved' に更新する。
    """
    update_tacit_status(
        TACIT_CSV,
        row_id=row_id,
        status="approved",
        approver=approver,
    )
    return {"status": "ok"}

# ============================================
# 4. 暗黙知マージ（承認済み→metadata.parquet へ反映）
# ============================================

@router.post("/trouble/tacit/apply")
def trouble_tacit_apply():
    """
    承認済み暗黙知を metadata.parquet にマージ
    """
    merge_approved_notes_into_meta(
        INDEX_DIR,
        tacit_csv=TACIT_CSV,
        target_col="tacit_notes",
        approved_status="approved",
    )
    return {"status": "updated"}


# ============================================
# 5. 分析情報（feedback CSV → 統計情報）
# ============================================

@router.get("/trouble/analytics")
def trouble_analytics():
    """
    フィードバック CSV を集計して分析データを返す
    """
    stats = load_feedback_stats(FEEDBACK_CSV)
    return stats
