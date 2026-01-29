import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from app.services.oracle_nlq_service import answer_with_oracle

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/oracle-nlq", tags=["oracle-nlq"])

class OracleNlqRequest(BaseModel):
    question: str = Field(..., min_length=1)
    limit: int = Field(200, ge=1, le=1000)

class OracleNlqResponse(BaseModel):
    sql: str
    columns: list[str]
    rows: list[dict]

@router.post("/query", response_model=OracleNlqResponse)
def query(req: OracleNlqRequest):
    try:
        return answer_with_oracle(question=req.question, limit=req.limit)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("oracle-nlq failed")  # ★これが重要
        raise HTTPException(status_code=500, detail="Internal server error")
