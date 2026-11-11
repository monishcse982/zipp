#!/usr/bin/env python3
"""Evaluate explicitly configured redirect thresholds from Locust CSV output."""

import argparse
import csv
import json
import math
from pathlib import Path


def finite_number(value: str, label: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be a number") from exc
    if not math.isfinite(number) or number < 0:
        raise ValueError(f"{label} must be finite and non-negative")
    return number


def validate_thresholds(p95: str, p99: str, error_pct: str) -> dict | None:
    limits = (p95, p99, error_pct)
    if not any(limits):
        return None
    if not all(limits):
        raise ValueError("Set all three thresholds: p95, p99, and error percentage")

    max_p95 = finite_number(p95, "p95 limit")
    max_p99 = finite_number(p99, "p99 limit")
    max_errors = finite_number(error_pct, "error percentage limit")
    if max_errors > 100:
        raise ValueError("error percentage limit must not exceed 100")

    return {"p95_ms": max_p95, "p99_ms": max_p99, "error_percent": max_errors}


def evaluate(stats_path: Path, p95: str, p99: str, error_pct: str) -> dict:
    thresholds = validate_thresholds(p95, p99, error_pct)
    if thresholds is None:
        return {"status": "NOT_EVALUATED", "reason": "No thresholds configured"}

    with stats_path.open(newline="", encoding="utf-8") as handle:
        rows = [
            row
            for row in csv.DictReader(handle)
            if row.get("Type") == "GET" and row.get("Name") == "GET /link/{short_code}"
        ]
    if len(rows) != 1:
        raise ValueError(
            "Expected exactly one named GET /link/{short_code} statistics row"
        )
    row = rows[0]
    count = finite_number(row.get("Request Count", ""), "request count")
    failures = finite_number(row.get("Failure Count", ""), "failure count")
    if (
        count <= 0
        or not count.is_integer()
        or not failures.is_integer()
        or failures > count
    ):
        raise ValueError("Redirect request and failure counts are invalid")

    values = {
        "p95_ms": finite_number(row.get("95%", ""), "p95"),
        "p99_ms": finite_number(row.get("99%", ""), "p99"),
        "error_percent": failures * 100 / count,
    }
    return {
        "status": (
            "PASS"
            if all(values[k] <= limit for k, limit in thresholds.items())
            else "FAIL"
        ),
        "request_count": int(count),
        "failure_count": int(failures),
        "observed": values,
        "maximum": thresholds,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stats", type=Path, nargs="?")
    parser.add_argument("--p95-ms", default="")
    parser.add_argument("--p99-ms", default="")
    parser.add_argument("--error-percent", default="")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    try:
        if args.validate_only:
            thresholds = validate_thresholds(
                args.p95_ms, args.p99_ms, args.error_percent
            )
            result = {"status": "VALID" if thresholds is not None else "NOT_EVALUATED"}
        else:
            if args.stats is None or args.output is None:
                raise ValueError("statistics path and --output are required")
            result = evaluate(args.stats, args.p95_ms, args.p99_ms, args.error_percent)
    except (OSError, ValueError, csv.Error) as exc:
        result = {"status": "ERROR", "reason": str(exc)}
    serialized = json.dumps(result, indent=2) + "\n"
    if args.output is not None:
        args.output.write_text(serialized, encoding="utf-8")
    print(serialized, end="")
    return 1 if result["status"] in {"FAIL", "ERROR"} else 0


if __name__ == "__main__":
    raise SystemExit(main())
