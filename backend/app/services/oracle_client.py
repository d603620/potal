import os
from typing import Any, Dict, List, Tuple
import oracledb

def run_select(sql: str, params: dict):
    user = os.environ["ORACLE_USER"]
    password = os.environ["ORACLE_PASSWORD"]
    host = os.environ["ORACLE_HOST"]
    port = int(os.environ.get("ORACLE_PORT", "1521"))
    service = os.environ["ORACLE_SERVICE"]

    dsn = oracledb.makedsn(host, port, service_name=service)

    conn = oracledb.connect(user=user, password=password, dsn=dsn)

    try:
        with conn.cursor() as cur:
            cur.execute(sql, params or {})

            desc = cur.description
            if desc is None:
                raise RuntimeError("No result set (cursor.description is None). SQL must be SELECT.")

            cols = [str(c[0]).lower() for c in desc]
            data = cur.fetchmany(int(os.environ.get("ORACLE_FETCH_MAX", "1000")))
            rows = [dict(zip(cols, r)) for r in data]
            return cols, rows
    finally:
        conn.close()
