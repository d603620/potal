from fastapi import APIRouter, HTTPException

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
from app.services.license_fetch_service import fetch_license_text_from_web

router = APIRouter(prefix="/license", tags=["license"])


# -------------------------
# 1. ライセンス要約 API
# -------------------------
@router.post("/summary", response_model=LicenseSummaryResponse)
def summarize_license(req: LicenseSummaryRequest):
    """
    ライセンステキストから商用利用に関係する要点を抽出する。
    ライセンステキストが空の場合は、ソフトウェア名から取得を試みる。
    """

    license_text = (req.license_text or "").strip()

    # ライセンステキストが空の場合は、ソフトウェア名から取得
    if not license_text:
        if not req.software_name:
            raise HTTPException(
                status_code=400,
                detail="ライセンステキストが空です。ソフトウェア名を指定するか、本文を貼り付けてください。",
            )

        license_text = fetch_license_text_from_web(req.software_name)

    # logic に渡すため、license_text を上書きした request を作る
    req_with_text = LicenseSummaryRequest(
        software_name=req.software_name,
        license_text=license_text,
    )

    return summarize_license_logic(req_with_text)


# -------------------------
# 2. 商用利用可否の判定 API
# -------------------------
@router.post("/judge", response_model=LicenseJudgeResponse)
def judge_license(req: LicenseJudgeRequest):
    """
    ライセンス要約と利用形態から、商用利用可否を判定する。
    """
    return judge_license_logic(req)
