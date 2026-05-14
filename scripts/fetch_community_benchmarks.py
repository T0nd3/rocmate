#!/usr/bin/env python3
"""Fetch AMD benchmark submissions from mate-bench D1 and write data/community_benchmarks.json."""

import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone

ACCOUNT_ID  = "27f81d43eb028aafd002283332cff05a"
DATABASE_ID = "f4edf4d1-c57b-449c-9dcc-bc1a418824da"
API_BASE    = f"https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/d1/database/{DATABASE_ID}"

TOKEN = os.environ.get("MATE_BENCH_CF_TOKEN", "")
if not TOKEN:
    print("MATE_BENCH_CF_TOKEN not set", file=sys.stderr)
    sys.exit(1)

OUT = "data/community_benchmarks.json"


def d1_query(sql: str) -> list[dict]:
    url  = f"{API_BASE}/query"
    body = json.dumps({"sql": sql}).encode()
    req  = urllib.request.Request(
        url, data=body, method="POST",
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.load(resp)
    except urllib.error.HTTPError as e:
        print(f"D1 HTTP error {e.code}: {e.read().decode()}", file=sys.stderr)
        sys.exit(1)

    if not data.get("success"):
        print(f"D1 error: {data}", file=sys.stderr)
        sys.exit(1)

    result = data["result"][0]
    cols   = result["results"].get("columns", [])
    rows   = result["results"].get("rows", [])
    return [dict(zip(cols, row)) for row in rows]


def main() -> None:
    rows = d1_query("""
        SELECT
            gpu_chip,
            engine,
            COUNT(*)                        AS submission_count,
            ROUND(MAX(tokens_per_second), 1) AS best_tps,
            ROUND(AVG(tokens_per_second), 1) AS avg_tps,
            MAX(submitted_at)               AS last_submitted_at
        FROM submissions
        WHERE tokens_per_second IS NOT NULL
          AND throttling_detected = 0
          AND gpu_vendor = 'amd'
        GROUP BY gpu_chip, engine
    """)

    benchmarks: dict = {}
    for row in rows:
        chip   = row["gpu_chip"]
        engine = row["engine"]
        benchmarks.setdefault(chip, {})[engine] = {
            "best_tps":         row["best_tps"],
            "avg_tps":          row["avg_tps"],
            "submission_count": row["submission_count"],
            "last_submitted_at": row["last_submitted_at"],
        }

    out = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "benchmarks": benchmarks,
    }

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
        f.write("\n")

    total = sum(len(v) for v in benchmarks.values())
    print(f"Written {total} chip/engine pairs across {len(benchmarks)} chips.")


if __name__ == "__main__":
    main()
