from fastapi import APIRouter, HTTPException
from app.services.oracle_client import run_select

router = APIRouter(prefix="/oracle-diag", tags=["oracle-diag"])

@router.get("/whoami")
def whoami():
    sql = "SELECT USER AS username FROM dual"
    cols, rows = run_select(sql, {})
    return rows[0]

@router.get("/tables")
def tables():
    # 自分が見える表/ビュー
    sql = """
    select * from T_製造2部工票_工票明細
    where
    kinmubi ='20251222'
    and
    kikaicd = 'MX0024'
    and
    jyotai ='終'
    order by  endtime asc
    """
    cols, rows = run_select(sql, {})
    return {"columns": cols, "rows": rows}
