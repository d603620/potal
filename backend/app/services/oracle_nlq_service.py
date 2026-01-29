import os
import re
from typing import Any, Dict, List, Tuple

from app.services.oracle_client import run_select
from app.services.llm_client import generate_sql

# ===== B方針の固定設定 =====
# For USHIKU
REQUIRED_OWNER = "USK_DBA"
REQUIRED_VIEW = "V_製造2部工票稼働"
REQUIRED_FROM = f"FROM {REQUIRED_OWNER}.{REQUIRED_VIEW}"

# For Life-D
#REQUIRED_OWNER = "d603620"
#REQUIRED_VIEW = "V_Orders_progress_shipping"
#REQUIRED_FROM = f"FROM {REQUIRED_OWNER}.{REQUIRED_VIEW}"

# ========================
FORBIDDEN = re.compile(
    r"\b(INSERT|UPDATE|DELETE|MERGE|ALTER|DROP|CREATE|TRUNCATE|GRANT|REVOKE|EXEC|EXECUTE|BEGIN|DECLARE|COMMIT|ROLLBACK)\b",
    re.IGNORECASE,
)

# ---------- helpers ----------
def _sanitize_sql(text: str) -> str:
    """
    LLMが ```sql ... ``` や "SQL:" を付けて返すことがあるので除去。
    末尾の ; も落とす。
    """
    s = (text or "").strip()
    s = re.sub(r"^```(?:sql)?\s*", "", s, flags=re.IGNORECASE)
    s = re.sub(r"\s*```$", "", s)
    s = re.sub(r"^\s*SQL\s*:\s*", "", s, flags=re.IGNORECASE)
    return s.strip().rstrip(";")

def _load_allowed() -> set[str]:
    """
    .env:
      ORACLE_ALLOWED_OBJECTS=USK_DBA.V_製造2部工票稼働
    ※クォート/前後スペース混入対策込み
    """
    raw = os.environ.get("ORACLE_ALLOWED_OBJECTS", "")
    items: List[str] = []
    for x in raw.split(","):
        x = x.strip().strip('"').strip("'")
        if x:
            items.append(x.upper())
    return set(items)

def _extract_from_targets(sql: str) -> List[str]:
    """
    FROM 直後のオブジェクトを抽出（JOINはB方針で禁止だが、念のため）。
    例: FROM USK_DBA.V_製造2部工票稼働 A  -> "USK_DBA.V_製造2部工票稼働"
    """
    s = " ".join(sql.strip().split())
    m = re.search(r"\bFROM\s+([^\s]+)", s, flags=re.IGNORECASE)
    if not m:
        return []
    target = m.group(1).strip().rstrip(",")
    return [target]

def _is_safe_sql(sql: str) -> Tuple[bool, str]:
    s = _sanitize_sql(sql)

    # 先頭が SELECT / WITH のみ許可
    if not re.match(r"^(SELECT|WITH)\b", s, re.IGNORECASE):
        return False, "SELECT/WITH 以外で始まっています"

    # DML/DDL/PLSQL を拒否
    if FORBIDDEN.search(s):
        return False, "禁止キーワード（更新/定義/PLSQL）が含まれています"

    # B方針: JOIN禁止
    if re.search(r"\bJOIN\b", s, re.IGNORECASE):
        return False, "JOIN は禁止です（1ビュー固定）"

    # B方針: ページング禁止（OFFSET/FETCH NEXTは禁止）
    if re.search(r"\bOFFSET\b", s, re.IGNORECASE):
        return False, "OFFSET は禁止です（ページング不可）"
    if re.search(r"\bFETCH\s+NEXT\b", s, re.IGNORECASE):
        return False, "FETCH NEXT は禁止です（ページング不可）"

    # Oracleで使わない LIMIT を拒否（LLMが出しがち）
    if re.search(r"\bLIMIT\b", s, re.IGNORECASE):
        return False, "LIMIT はOracleで使用できません（FETCH FIRST を使用してください）"

    return True, "OK"

def _check_view_only(sql: str) -> None:
    """
    B方針の核心：FROMは必ず USK_DBA.V_製造2部工票稼働 のみ。
    スキーマ省略も禁止。
    """
    s = _sanitize_sql(sql)
    targets = _extract_from_targets(s)
    if not targets:
        raise ValueError("FROM句が見つかりません")

    t = targets[0]
    if "." not in t:
        raise ValueError(f"Object must be schema-qualified: {t}")

    required = f"{REQUIRED_OWNER}.{REQUIRED_VIEW}".upper()
    if t.upper() != required:
        raise ValueError(f"Unauthorized table/view: {t}")

    allowed = _load_allowed()
    if allowed and required not in allowed:
        # .env が未設定/誤設定のときに早期に気づけるようにする
        raise ValueError(f"Allowed list mismatch. ORACLE_ALLOWED_OBJECTS must include {required}")
def _enforce_limit(sql: str, limit: int) -> str:
    """

    アプリ側で件数制限を付与する。
    ただし、SQL内にFETCHが既にある場合は二重付与しない。
    （B方針でOFFSET/FETCH NEXTは禁止なので、FETCHがあればFETCH FIRST想定）
    """
    s = _sanitize_sql(sql)

    # 既にFETCHが含まれていれば触らない（二重付与防止）
    if re.search(r"\bFETCH\b", s, re.IGNORECASE):
        return s

    return f"{s}\nFETCH FIRST {int(limit)} ROWS ONLY"

def build_schema_context(owner: str, view_name: str) -> str:
    """
    LLMに渡すスキーマ文脈（列一覧）。精度を上げつつ、ルールを強制する。
    """
    sql = """
    SELECT column_name, data_type
    FROM all_tab_columns
    WHERE owner = :owner AND table_name = :view_name
    ORDER BY column_id
    """
    _, rows = run_select(sql, {"owner": owner.upper(), "view_name": view_name.upper()})

    lines: List[str] = []
    lines.append(f"Allowed view: {owner}.{view_name}")
    lines.append("Columns:")
    for r in rows:
        # oracle_client.py 側で lower() されている可能性があるため両対応
        col = r.get("column_name") or r.get("COLUMN_NAME")
        dt = r.get("data_type") or r.get("DATA_TYPE")
        lines.append(f"- {col} ({dt})")

    lines.append("")
    lines.append("STRICT RULES (must follow):")
    lines.append(f"- You MUST use exactly this FROM clause: {REQUIRED_FROM}")
    lines.append("- Do NOT use any other table/view.")
    lines.append("- Do NOT use JOIN.")
    lines.append("- Do NOT use OFFSET or FETCH NEXT.")
    lines.append("- Do NOT use LIMIT.")
    lines.append("- Output ONLY one SQL statement (no explanation, no markdown, no backticks).")
    lines.append("- Do not use DML or DDL.")
    return "\n".join(lines)

# ---------- main ----------
def answer_with_oracle(question: str, limit: int = 200) -> Dict[str, Any]:
    schema_context = build_schema_context(REQUIRED_OWNER, REQUIRED_VIEW)

    proposed_sql_raw = generate_sql(question=question, schema_context=schema_context)
    proposed_sql = _sanitize_sql(proposed_sql_raw)

    ok, msg = _is_safe_sql(proposed_sql)
    if not ok:
        raise ValueError(f"SQL rejected: {msg}")

    # B方針：ビュー固定（1本）
    _check_view_only(proposed_sql)

    exec_sql = _enforce_limit(proposed_sql, limit)

    # デバッグ（必要なときだけ有効化）
    # print("EXEC_SQL:\n", exec_sql)

    columns, rows = run_select(exec_sql, params={})
    return {"sql": exec_sql, "columns": columns, "rows": rows}
