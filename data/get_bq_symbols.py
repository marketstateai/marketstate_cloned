#!/usr/bin/env python3
"""
Populate a sqlite DB with companies + candidate Yahoo Finance symbols from BigQuery.

Creates the same sqlite structure as `marketstate/get_primary_symbol.py` and pre-populates
`results` with one row per company (no inference yet).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


QUERY = """
select
  c.company_name,
  business_summary,
  country_of_origin,
  string_agg(distinct s.yf_symbol, ', ') as yf_symbols
from general-428410.src_prod.stocks s
left join general-428410.stg_prod.stg_companies c on s.company_name = c.company_name
# where c.company_name in ('Vacasa, Inc.') or lower(c.company_name) like '%general%electric%'
group by company_name, business_summary, country_of_origin
order by (business_summary is not null) desc, count(distinct s.yf_symbol) desc
""".strip()


def _split_symbols(csv: str) -> list[str]:
    parts = [p.strip() for p in (csv or "").split(",")]
    out: list[str] = []
    seen: set[str] = set()
    for p in parts:
        sym = p.strip().upper()
        if not sym or sym in seen:
            continue
        seen.add(sym)
        out.append(sym)
    return out


def _secret_manager_service_account(session) -> dict:
    candidate = getattr(session, "secret_manager_path", None)
    if isinstance(candidate, dict):
        return candidate
    return session.GOOGLE_SECRET_MANAGER_CREDENTIALS


def bq_to_rows(query: str, *, limit: int | None, job_project: str | None) -> list[dict[str, Any]]:
    from marketstate.src.gcp_functions import GCP

    session = GCP()
    if job_project:
        session.project_id = job_project

    bq_creds = session.get_credentials_from_secret_manager(
        secret_id="bigquery",
        version_id=1,
        secret_manager_service_account=_secret_manager_service_account(session),
    )
    df = session.bq_to_df(credentials=bq_creds, query=query)
    if limit is not None:
        df = df.head(limit)
    return df.to_dict(orient="records")


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--db", default="primary_symbols.sqlite", help="SQLite db file (created/updated).")
    p.add_argument("--query", default=QUERY)
    p.add_argument("--limit", type=int, default=None, help="Optional limit for pre-population.")
    p.add_argument("--job-project", default=None, help="Project to run the query job in (needs jobs.create).")
    args = p.parse_args(argv)

    from marketstate.get_primary_symbol import (
        _sqlite_init,
        _sqlite_new_run,
        _sqlite_write_result_row,
    )

    db_path = Path(__file__).resolve().parent / args.db
    conn = _sqlite_init(db_path)
    run_id = _sqlite_new_run(
        conn,
        {
            "type": "bq_populate",
            "query": args.query,
            "limit": args.limit,
            "job_project": args.job_project,
        },
    )
    # `_sqlite_new_run` inserts a row; ensure we're not already inside a transaction
    # before starting our own bulk transaction below.
    conn.commit()

    t0 = time.perf_counter()
    rows = bq_to_rows(args.query, limit=args.limit, job_project=args.job_project)
    t1 = time.perf_counter()
    total = len(rows)
    print(f"Fetched {total} rows from BigQuery in {(t1 - t0):.1f}s", file=sys.stderr)

    # Speed: one transaction, not a commit per row.
    t2 = time.perf_counter()
    try:
        conn.execute("BEGIN")
        for idx, row in enumerate(rows, start=1):
            company = str(row.get("company_name") or "")
            summary = row.get("business_summary")
            country = row.get("country_of_origin")
            yf_symbols_raw = "" if row.get("yf_symbols") is None else str(row.get("yf_symbols"))
            candidates = _split_symbols(yf_symbols_raw)
            result_row = {
                "company_name": company,
                "business_summary": summary,
                "country_of_origin": country,
                "inferred_country_of_origin": None,
                "yf_symbols_raw": yf_symbols_raw,
                "candidate_symbols": candidates,
                "candidate_symbol_count": len(candidates),
                "primary_symbol": None,
                "primary_yf_symbol": None,
                "added_symbol": None,
                "final_symbols": candidates,
                "yfinance_validated": False,
                "yfinance_checks": [],
                "ollama_system_prompt": None,
                "ollama_attempts": [],
                "events": [{"step": "bq_populate"}],
                "row_error": None,
            }
            _sqlite_write_result_row(conn, run_id, idx, result_row)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    t3 = time.perf_counter()
    print(f"Wrote {total} rows to sqlite in {(t3 - t2):.1f}s", file=sys.stderr)

    conn.close()
    print(str(db_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(__import__("sys").argv[1:]))
