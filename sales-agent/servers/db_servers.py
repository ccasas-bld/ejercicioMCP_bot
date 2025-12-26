# servers/db_server.py
import json
import sqlite3
from pathlib import Path
from datetime import datetime

import pandas as pd
import matplotlib.pyplot as plt
import sqlparse
from fastmcp import FastMCP

mcp = FastMCP("sales-db-server")

DB_PATH = Path(__file__).resolve().parents[1] / "src" / "ventas.db"
OUT_DIR = Path(__file__).resolve().parents[1] / "outputs"
OUT_DIR.mkdir(parents=True, exist_ok=True)

BLOCKED_KEYWORDS = {
    "insert", "update", "delete", "drop", "alter", "create",
    "attach", "detach", "pragma", "vacuum", "reindex", "replace"
}

def _is_safe_select(sql: str) -> bool:
    s = (sql or "").strip()
    if not s:
        return False

    # 1 statement only (evita "SELECT...; DROP TABLE...")
    parsed = sqlparse.parse(s)
    if len(parsed) != 1:
        return False

    # bloquear keywords peligrosas (best-effort)
    lowered = s.lower()
    if any(k in lowered for k in BLOCKED_KEYWORDS):
        return False

    stmt = parsed[0]
    # validar que sea SELECT
    return stmt.get_type() == "SELECT"

def _wrap_limit(sql: str, max_rows: int) -> str:
    s = sql.strip().rstrip(";")
    # envolver para no romper ORDER BY/GROUP BY
    return f"SELECT * FROM ({s}) LIMIT {max_rows}"

def _conn():
    return sqlite3.connect(str(DB_PATH))

@mcp.tool
def get_schema() -> str:
    """Devuelve el schema de la base y la tabla ventas."""
    with _conn() as c:
        tables = pd.read_sql_query(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;", c
        )
        ventas_cols = pd.read_sql_query("PRAGMA table_info(ventas);", c)
    return json.dumps({
        "db_path": str(DB_PATH),
        "tables": tables.to_dict(orient="records"),
        "ventas_columns": ventas_cols.to_dict(orient="records"),
    }, ensure_ascii=False)

@mcp.tool
def run_sql(sql: str, max_rows: int = 200) -> str:
    """Ejecuta SOLO SELECT y retorna filas/columnas en JSON."""
    if not _is_safe_select(sql):
        return json.dumps({"error": "SQL no permitido. Solo SELECT, 1 statement."}, ensure_ascii=False)

    safe_sql = _wrap_limit(sql, max_rows=max_rows)

    try:
        with _conn() as c:
            df = pd.read_sql_query(safe_sql, c)
        return json.dumps({
            "columns": list(df.columns),
            "rows": df.to_dict(orient="records"),
            "rowcount": int(len(df)),
            "limited_to": max_rows
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)

@mcp.tool
def plot_sql(sql: str, chart_type: str = "bar", x: str | None = None, y: str | None = None, title: str | None = None) -> str:
    """Ejecuta un SELECT y genera un gráfico (PNG) en ./outputs."""
    if not _is_safe_select(sql):
        return json.dumps({"error": "SQL no permitido. Solo SELECT, 1 statement."}, ensure_ascii=False)

    safe_sql = _wrap_limit(sql, max_rows=500)

    try:
        with _conn() as c:
            df = pd.read_sql_query(safe_sql, c)

        if df.empty:
            return json.dumps({"error": "Query sin filas; no se puede graficar."}, ensure_ascii=False)

        # autodetección simple x/y si no vienen
        cols = list(df.columns)
        if x is None or y is None:
            numeric = [c for c in cols if pd.api.types.is_numeric_dtype(df[c])]
            nonnum = [c for c in cols if c not in numeric]
            if x is None:
                x = nonnum[0] if nonnum else cols[0]
            if y is None:
                y = numeric[0] if numeric else cols[-1]

        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        out = OUT_DIR / f"plot_{chart_type}_{ts}.png"

        plt.figure()
        if chart_type == "line":
            df.plot(x=x, y=y, kind="line")
        elif chart_type == "pie":
            df.set_index(x)[y].plot(kind="pie", autopct="%1.1f%%")
        else:
            df.plot(x=x, y=y, kind="bar")

        plt.title(title or f"{chart_type}: {y} por {x}")
        plt.tight_layout()
        plt.savefig(out, dpi=140)
        plt.close()

        return json.dumps({"ok": True, "file": str(out), "x": x, "y": y, "rows": int(len(df))}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)

@mcp.tool
def export_sql(sql: str, format: str = "csv", filename: str | None = None) -> str:
    """Ejecuta SELECT y exporta a CSV o XLSX en ./outputs."""
    if not _is_safe_select(sql):
        return json.dumps({"error": "SQL no permitido. Solo SELECT, 1 statement."}, ensure_ascii=False)

    safe_sql = _wrap_limit(sql, max_rows=100000)

    try:
        with _conn() as c:
            df = pd.read_sql_query(safe_sql, c)

        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        fmt = format.lower().strip()
        if filename:
            out = OUT_DIR / filename
        else:
            out = OUT_DIR / f"export_{ts}.{ 'xlsx' if fmt in ('xlsx','excel') else 'csv' }"

        if fmt in ("xlsx", "excel"):
            df.to_excel(out, index=False)
        else:
            df.to_csv(out, index=False)

        return json.dumps({"ok": True, "file": str(out), "rows": int(len(df))}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)

if __name__ == "__main__":
    # stdio = recomendado para correrlo como subprocess desde el agente
    mcp.run(transport="stdio")
