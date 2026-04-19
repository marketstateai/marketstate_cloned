#!/usr/bin/env python3
"""
Resolve primary Yahoo Finance symbols for companies stored in a sqlite DB.

Basic approach:
1) Try to find the primary from candidate symbols (and base-symbol expansions).
2) If no candidate looks like the primary, ask Ollama to guess up to 3 symbols.
3) Validate each attempted symbol via yfinance `Ticker(...).get_info()` AND a simple
   business-summary/name match against the company name.

DB is pre-populated by: `python3 -m get_bq_symbols`
"""

from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import difflib
import io
import json
import os
import random
import re
import sqlite3
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any

# Ensure `import marketstate...` works even when running from `./marketstate`.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

MODEL = "gemma3:27b"
# MODEL = "gpt-oss:120b"
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434").rstrip("/")


GUESS_SYSTEM = """You propose up to 3 likely PRIMARY Yahoo Finance tickers for a company.

Input: company name + a list of candidate tickers (may be wrong/foreign).
Output: ONLY JSON:
{"symbols": [string, string, string]}

Rules:
- Return 1 to 3 symbols, distinct, non-empty.
- Prefer the company's primary/common listing.
- Use Yahoo Finance ticker formatting.
"""


def _parse_bool(val: str | bool | None) -> bool:
    if val is None:
        return False
    if isinstance(val, bool):
        return val
    v = val.strip().lower()
    if v in {"1", "true", "t", "yes", "y", "on"}:
        return True
    if v in {"0", "false", "f", "no", "n", "off"}:
        return False
    raise ValueError(f"Invalid boolean value: {val!r} (expected True/False)")


def _norm_symbol(s: str) -> str:
    s = (s or "").strip().upper()
    s = re.sub(r"\s+", "", s)
    s = s.strip("`\"' \n\t,")
    return s.replace("/", "-").replace("_", "-").replace("·", "-")


def _base_symbol(yf_symbol: str) -> str:
    sym = _norm_symbol(yf_symbol)
    return sym.split(".", 1)[0] if "." in sym else sym


def _candidate_expansions(symbols: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for s in symbols:
        sym = _norm_symbol(s)
        if not sym:
            continue
        if sym not in seen:
            seen.add(sym)
            out.append(sym)
        if "." in sym:
            base = sym.split(".", 1)[0]
            if base and base not in seen:
                seen.add(base)
                out.append(base)
    return out


def _symbols_from_row(row: dict[str, Any]) -> list[str]:
    val = row.get("candidate_symbols")
    if isinstance(val, list):
        raw = [str(x) for x in val]
    else:
        raw = [p.strip() for p in str(row.get("yf_symbols_raw") or row.get("yf_symbols") or "").split(",")]
    out: list[str] = []
    seen: set[str] = set()
    for part in raw:
        sym = _norm_symbol(part)
        if sym and sym not in seen:
            seen.add(sym)
            out.append(sym)
    return out


def _text_similarity(a: str, b: str) -> float:
    a = (a or "").strip().lower()
    b = (b or "").strip().lower()
    if not a or not b:
        return 0.0
    return difflib.SequenceMatcher(None, a, b).ratio()


_STOPWORDS = {
    "the",
    "and",
    "&",
    "inc",
    "incorporated",
    "corp",
    "corporation",
    "co",
    "company",
    "ltd",
    "limited",
    "plc",
    "sa",
    "s",
    "a",
    "nv",
    "ag",
    "ab",
    "as",
    "spa",
    "holdings",
    "group",
}


def _tokens(text: str) -> list[str]:
    text = (text or "").lower()
    parts = re.findall(r"[a-z0-9]+", text)
    return [p for p in parts if p and p not in _STOPWORDS]


def _jaccard(a: list[str], b: list[str]) -> float:
    sa, sb = set(a), set(b)
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def _yf_check(symbol: str) -> dict[str, Any]:
    import yfinance as yf  # type: ignore

    sym = _norm_symbol(symbol)
    if not sym:
        return {"symbol": sym, "ok": False, "error": "empty_symbol"}

    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(
            io.StringIO()
        ):
            info = yf.Ticker(sym).get_info()
    except Exception as e:
        msg = str(e)
        http_status = None
        m = re.search(r"HTTP Error (\d+)", msg)
        if m:
            try:
                http_status = int(m.group(1))
            except ValueError:
                http_status = None
        return {
            "symbol": sym,
            "ok": False,
            "error": {"type": type(e).__name__, "message": msg, "http_status": http_status},
        }

    if not isinstance(info, dict) or not info:
        return {"symbol": sym, "ok": False, "error": "empty_info"}

    lbs = info.get("longBusinessSummary")
    lbs_snip = lbs.strip()[:1200] if isinstance(lbs, str) and lbs.strip() else ""
    info_small = {
        "symbol": info.get("symbol"),
        "shortName": info.get("shortName"),
        "longName": info.get("longName"),
        "exchange": info.get("exchange"),
        "quoteType": info.get("quoteType"),
        "country": info.get("country"),
        "website": info.get("website"),
        "industry": info.get("industry"),
        "sector": info.get("sector"),
        "longBusinessSummary": lbs_snip,
    }
    return {"symbol": sym, "ok": True, "info": info_small}


def _company_matches_symbol(company_name: str, yf_info: dict[str, Any]) -> float:
    long_name = str(yf_info.get("longName") or "")
    short_name = str(yf_info.get("shortName") or "")
    lbs = str(yf_info.get("longBusinessSummary") or "")
    name_blob = (long_name + " " + short_name).strip()

    company_norm = " ".join(_tokens(company_name))
    name_norm = " ".join(_tokens(name_blob))
    lbs_norm = " ".join(_tokens(lbs))

    # Strong signal: company name tokens appear in the Yahoo name/summary.
    contains_name = company_norm and (company_norm in name_norm)
    contains_lbs = company_norm and (company_norm in lbs_norm)

    company_toks = _tokens(company_name)
    name_toks = _tokens(name_blob)
    # Limit summary tokens to keep this cheap/stable.
    lbs_toks = _tokens(lbs)[:200]

    score = 0.0
    score = max(score, _jaccard(company_toks, name_toks))
    score = max(score, _jaccard(company_toks, lbs_toks))
    score = max(score, _text_similarity(company_name, name_blob))

    if contains_name:
        score = max(score, 0.85)
    if contains_lbs:
        score = max(score, 0.75)
    return float(score)


def _validate_symbol(company_name: str, symbol: str) -> dict[str, Any]:
    check = _yf_check(symbol)
    if not check.get("ok"):
        check["match_score"] = 0.0
        check["is_company_match"] = False
        return check

    info = check.get("info") if isinstance(check.get("info"), dict) else {}
    score = _company_matches_symbol(company_name, info)
    check["match_score"] = round(float(score), 4)
    # Threshold is intentionally conservative; we’d rather fail and guess again than accept a wrong company.
    check["is_company_match"] = score >= 0.5
    return check


def _looks_like_primary(symbol: str, yf_info: dict[str, Any]) -> bool:
    sym = _norm_symbol(symbol)
    if "." not in sym:
        return True
    country = str(yf_info.get("country") or "").strip().lower()
    exchange = str(yf_info.get("exchange") or "").strip().upper()
    us_exchanges = {"NYQ", "NMS", "NGM", "NAS", "ASE", "BATS", "PNK", "OTC"}
    if country in {"united states", "united states of america", "usa", "us"}:
        return exchange in us_exchanges
    return True


def _pick_best_validated(
    company_name: str, symbols: list[str]
) -> tuple[str | None, dict[str, dict[str, Any]], list[dict[str, Any]]]:
    checks: list[dict[str, Any]] = []
    checks_by_symbol: dict[str, dict[str, Any]] = {}
    best: tuple[tuple[int, float], str] | None = None
    seen: set[str] = set()

    for sym in symbols:
        sym = _norm_symbol(sym)
        if not sym or sym in seen:
            continue
        seen.add(sym)
        c = _validate_symbol(company_name, sym)
        checks.append(c)
        checks_by_symbol[sym] = c
        if c.get("ok") and c.get("is_company_match"):
            score = float(c.get("match_score") or 0.0)
            dot_penalty = 1 if "." in sym else 0
            key = (dot_penalty, -score)
            if best is None or key < best[0]:
                best = (key, sym)

    return (best[1] if best else None), checks_by_symbol, checks


def _validate_up_to_n(company_name: str, symbols: list[str], n: int) -> tuple[str | None, list[dict[str, Any]]]:
    checks: list[dict[str, Any]] = []
    best: tuple[tuple[int, float], str] | None = None
    seen: set[str] = set()
    for sym in symbols:
        if len(checks) >= n:
            break
        sym = _norm_symbol(sym)
        if not sym or sym in seen:
            continue
        seen.add(sym)
        c = _validate_symbol(company_name, sym)
        checks.append(c)
        if c.get("ok") and c.get("is_company_match"):
            score = float(c.get("match_score") or 0.0)
            dot_penalty = 1 if "." in sym else 0
            key = (dot_penalty, -score)
            if best is None or key < best[0]:
                best = (key, sym)
    return (best[1] if best else None), checks


def _ollama_guess_symbols(company_name: str, candidates: list[str], *, model: str, url: str) -> list[str]:
    payload_obj = {"company_name": company_name, "candidate_symbols": candidates}
    user_prompt = json.dumps(payload_obj, ensure_ascii=False)
    payload = {
        "model": model,
        "stream": False,
        "messages": [
            {"role": "system", "content": GUESS_SYSTEM},
            {"role": "user", "content": user_prompt},
        ],
        "options": {"temperature": 0.0},
    }
    req = urllib.request.Request(
        f"{url}/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60.0) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    text = ((body.get("message") or {}).get("content") or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
        text = re.sub(r"\s*```$", "", text).strip()
    obj = json.loads(text) if text.startswith("{") else json.loads(re.search(r"\{.*\}", text, re.DOTALL).group(0))  # type: ignore[union-attr]
    symbols = obj.get("symbols", [])
    out: list[str] = []
    if isinstance(symbols, list):
        for s in symbols:
            sym = _norm_symbol(str(s))
            if sym:
                out.append(sym)
    out = list(dict.fromkeys(out))[:3]
    return out


def infer_primary_symbol_for_row(
    row: dict[str, Any],
    *,
    idx: int,
    total: int,
    model: str,
    url: str,
) -> dict[str, Any]:
    company = str(row.get("company_name") or "")
    summary = row.get("business_summary")
    country = row.get("country_of_origin")
    candidates = _symbols_from_row(row)
    yf_symbols_raw = row.get("yf_symbols_raw", row.get("yf_symbols"))

    print(f"\n[{idx}/{total}] Company: {company}", file=sys.stderr)
    print(f"  Candidates ({len(candidates)}): {', '.join(candidates)}", file=sys.stderr)

    # Step 1: evaluate candidates. If we believe the primary is present, use it.
    best_cand, by_sym, cand_checks = _pick_best_validated(company, candidates)
    if best_cand:
        info = (by_sym.get(best_cand) or {}).get("info") if isinstance((by_sym.get(best_cand) or {}).get("info"), dict) else {}
        is_primary_like = _looks_like_primary(best_cand, info if isinstance(info, dict) else {})
        print(
            f"  Best candidate match -> {best_cand} | primary_like={is_primary_like}",
            file=sys.stderr,
        )
        if is_primary_like:
            primary_yf = best_cand
            primary = _base_symbol(primary_yf)
            added = None
            final = candidates
            return {
                "company_name": company,
                "business_summary": summary,
                "country_of_origin": country,
                "inferred_country_of_origin": None,
                "yf_symbols_raw": yf_symbols_raw,
                "candidate_symbols": candidates,
                "candidate_symbol_count": len(candidates),
                "primary_symbol": primary,
                "primary_yf_symbol": primary_yf,
                "added_symbol": added,
                "final_symbols": final,
                "yfinance_validated": True,
                "yfinance_checks": cand_checks,
                "ollama_system_prompt": None,
                "ollama_attempts": [],
                "events": [{"step": "used_candidate_primary"}],
                "row_error": None,
            }

    print("  Candidate eval suggests primary missing; guessing...", file=sys.stderr)

    # Step 2: guess up to 3 symbols (include base expansions of candidates first).
    base_guesses = []
    for s in candidates:
        sym = _norm_symbol(s)
        if "." in sym:
            base_guesses.append(sym.split(".", 1)[0])
    base_guesses = list(dict.fromkeys([_norm_symbol(x) for x in base_guesses if _norm_symbol(x)]))

    print(f"  Calling Ollama for up to 3 guesses (model={model})...", file=sys.stderr)
    llm_prompt = {"company_name": company, "candidate_symbols": candidates}
    try:
        llm_guesses = _ollama_guess_symbols(company, candidates, model=model, url=url)
    except Exception as e:
        llm_guesses = []
        print(f"  Ollama guess failed: {e}", file=sys.stderr)
    guesses = list(dict.fromkeys(base_guesses + llm_guesses))[:3]
    print(f"  Guess list (max 3): {guesses} (llm={llm_guesses})", file=sys.stderr)

    best, guess_checks = _validate_up_to_n(company, guesses, 3)
    all_checks = cand_checks + guess_checks

    if best:
        primary_yf = best
        primary = _base_symbol(primary_yf)
        added = None if primary_yf in candidates else primary_yf
        final = candidates if added is None else candidates + [added]
        print(f"  Picked from guesses -> {primary_yf}", file=sys.stderr)
        return {
            "company_name": company,
            "business_summary": summary,
            "country_of_origin": country,
            "inferred_country_of_origin": None,
            "yf_symbols_raw": yf_symbols_raw,
            "candidate_symbols": candidates,
            "candidate_symbol_count": len(candidates),
            "primary_symbol": primary,
            "primary_yf_symbol": primary_yf,
            "added_symbol": added,
            "final_symbols": final,
            "yfinance_validated": True,
            "yfinance_checks": all_checks,
            "ollama_system_prompt": GUESS_SYSTEM,
            "ollama_attempts": [{"attempt": 1, "user_input": llm_prompt, "llm_guesses": llm_guesses, "guesses": guesses}],
            "events": [{"step": "picked_from_guesses"}],
            "row_error": None,
        }

    print("  Failed to validate any guessed symbol.", file=sys.stderr)
    return {
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
        "yfinance_checks": all_checks,
        "ollama_system_prompt": GUESS_SYSTEM,
        "ollama_attempts": [{"attempt": 1, "user_input": llm_prompt, "llm_guesses": llm_guesses, "guesses": guesses}],
        "events": [{"step": "no_valid_symbol"}],
        "row_error": None,
    }


# ---- sqlite helpers (shared with get_bq_symbols.py) ----


def _sqlite_init(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    # Avoid creating `*.sqlite-wal` and `*.sqlite-shm` sidecar files by not using WAL mode.
    conn.execute("PRAGMA journal_mode=DELETE;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runs (
          run_id INTEGER PRIMARY KEY AUTOINCREMENT,
          started_ts TEXT NOT NULL,
          params_json TEXT NOT NULL,
          error TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS results (
          run_id INTEGER NOT NULL,
          row_idx INTEGER NOT NULL,
          company_name TEXT,
          business_summary TEXT,
          country_of_origin TEXT,
          inferred_country_of_origin TEXT,
          yf_symbols_raw TEXT,
          candidate_symbols_json TEXT,
          candidate_symbol_count INTEGER,
          primary_symbol TEXT,
          primary_yf_symbol TEXT,
          added_symbol TEXT,
          final_symbols_json TEXT,
          yfinance_validated INTEGER,
          yfinance_checks_json TEXT,
          ollama_system_prompt TEXT,
          ollama_attempts_json TEXT,
          events_json TEXT,
          row_error TEXT,
          PRIMARY KEY (run_id, row_idx)
        )
        """
    )
    existing_cols = {row[1] for row in conn.execute("PRAGMA table_info(results)")}
    for col in (
        "primary_yf_symbol",
        "row_error",
        "ollama_system_prompt",
        "ollama_attempts_json",
        "inferred_country_of_origin",
    ):
        if col not in existing_cols:
            conn.execute(f"ALTER TABLE results ADD COLUMN {col} TEXT")
    return conn


def _sqlite_new_run(conn: sqlite3.Connection, params: dict[str, Any]) -> int:
    started_ts = dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    cur = conn.execute(
        "INSERT INTO runs (started_ts, params_json, error) VALUES (?, ?, NULL)",
        (started_ts, json.dumps(params, ensure_ascii=False)),
    )
    return int(cur.lastrowid)


def _sqlite_set_run_error(conn: sqlite3.Connection, run_id: int, error: str) -> None:
    conn.execute("UPDATE runs SET error=? WHERE run_id=?", (error, run_id))


def _sqlite_write_result_row(
    conn: sqlite3.Connection, run_id: int, row_idx: int, r: dict[str, Any]
) -> None:
    conn.execute(
        """
        INSERT OR REPLACE INTO results (
          run_id, row_idx, company_name, business_summary, country_of_origin, inferred_country_of_origin, yf_symbols_raw,
          candidate_symbols_json, candidate_symbol_count, primary_symbol, primary_yf_symbol, added_symbol,
          final_symbols_json, yfinance_validated, yfinance_checks_json, ollama_system_prompt,
          ollama_attempts_json, events_json, row_error
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            run_id,
            row_idx,
            r.get("company_name"),
            r.get("business_summary"),
            r.get("country_of_origin"),
            r.get("inferred_country_of_origin"),
            None if r.get("yf_symbols_raw") is None else str(r.get("yf_symbols_raw")),
            json.dumps(r.get("candidate_symbols", []), ensure_ascii=False),
            int(r.get("candidate_symbol_count") or 0),
            r.get("primary_symbol"),
            r.get("primary_yf_symbol"),
            r.get("added_symbol"),
            json.dumps(r.get("final_symbols", []), ensure_ascii=False),
            1 if r.get("yfinance_validated") else 0,
            json.dumps(r.get("yfinance_checks", []), ensure_ascii=False),
            r.get("ollama_system_prompt"),
            json.dumps(r.get("ollama_attempts", []), ensure_ascii=False),
            json.dumps(r.get("events", []), ensure_ascii=False),
            r.get("row_error"),
        ),
    )


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--db", default="primary_symbols.sqlite", help="SQLite db to read/update.")
    p.add_argument("--run-id", type=int, default=None, help="Run id to update (default: latest).")
    p.add_argument("--limit", type=int, default=None, help="Process N pending rows (default: all).")
    p.add_argument("--model", default=MODEL)
    p.add_argument("--ollama-url", default=OLLAMA_URL)
    p.add_argument("--shuffle", default="False", help="Shuffle pending rows before processing.")
    p.add_argument("--shuffle-seed", type=int, default=None)
    a = p.parse_args(argv)

    db_path = Path(__file__).resolve().parent / a.db
    conn = _sqlite_init(db_path)

    run_id = a.run_id
    if run_id is None:
        row = conn.execute("SELECT MAX(run_id) FROM runs").fetchone()
        run_id = int(row[0]) if row and row[0] is not None else None
    if run_id is None:
        raise SystemExit("No runs found in sqlite. Run `python3 -m get_bq_symbols` first.")

    shuffle = _parse_bool(a.shuffle)
    print(
        f"Updating db={db_path} run_id={run_id} (limit={'ALL' if a.limit is None else a.limit}, shuffle={shuffle})...",
        file=sys.stderr,
    )

    sql = """
    SELECT
      row_idx,
      company_name,
      business_summary,
      country_of_origin,
      inferred_country_of_origin,
      yf_symbols_raw,
      candidate_symbols_json,
      candidate_symbol_count
    FROM results
    WHERE run_id = ?
      AND (primary_yf_symbol IS NULL OR yfinance_validated = 0 OR row_error IS NOT NULL)
    ORDER BY (business_summary IS NOT NULL) DESC, candidate_symbol_count DESC, row_idx ASC
    """
    rows_raw = conn.execute(sql, (run_id,)).fetchall()

    pending: list[dict[str, Any]] = []
    for r in rows_raw:
        pending.append(
            {
                "row_idx": int(r[0]),
                "company_name": r[1],
                "business_summary": r[2],
                "country_of_origin": r[3],
                "inferred_country_of_origin": r[4],
                "yf_symbols_raw": r[5],
                "candidate_symbols": json.loads(r[6] or "[]"),
                "candidate_symbol_count": int(r[7] or 0),
            }
        )

    if shuffle:
        rng = random.Random(a.shuffle_seed)
        rng.shuffle(pending)
    if a.limit is not None:
        pending = pending[: a.limit]

    total = len(pending)
    print(f"Pending rows: {total}", file=sys.stderr)

    start_wall = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
    start_wall_s = start_wall.isoformat()
    start_perf = time.perf_counter()
    per_row: list[float] = []

    try:
        for pos, row in enumerate(pending, start=1):
            row_start = time.perf_counter()
            try:
                result = infer_primary_symbol_for_row(row, idx=pos, total=total, model=a.model, url=a.ollama_url)
            except Exception as e:
                result = {
                    "company_name": row.get("company_name"),
                    "business_summary": row.get("business_summary"),
                    "country_of_origin": row.get("country_of_origin"),
                    "inferred_country_of_origin": None,
                    "yf_symbols_raw": row.get("yf_symbols_raw"),
                    "candidate_symbols": _symbols_from_row(row),
                    "candidate_symbol_count": len(_symbols_from_row(row)),
                    "primary_symbol": None,
                    "primary_yf_symbol": None,
                    "added_symbol": None,
                    "final_symbols": _symbols_from_row(row),
                    "yfinance_validated": False,
                    "yfinance_checks": [{"error": str(e)}],
                    "ollama_system_prompt": None,
                    "ollama_attempts": [],
                    "events": [{"step": "row_error"}],
                    "row_error": str(e),
                }

            with conn:
                _sqlite_write_result_row(conn, run_id, int(row["row_idx"]), result)

            row_s = time.perf_counter() - row_start
            per_row.append(row_s)
            avg_s = sum(per_row) / len(per_row)
            elapsed_s = time.perf_counter() - start_perf
            remaining_s = max(0.0, avg_s * total - elapsed_s)
            eta = (dt.datetime.now(dt.timezone.utc) + dt.timedelta(seconds=remaining_s)).replace(microsecond=0).isoformat()
            print(
                f"Progress: {pos}/{total} | start={start_wall_s} | eta={eta} | "
                f"elapsed={elapsed_s/60.0:.1f}m | this_row={row_s:.1f}s | avg={avg_s:.1f}s",
                file=sys.stderr,
            )
    except Exception as e:
        with conn:
            _sqlite_set_run_error(conn, run_id, str(e))
        raise
    finally:
        conn.close()

    print(str(db_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
