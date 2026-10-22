"""Validate a serialized Phase 6D.2 evaluation report without modifying it."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.evaluation_report_validation import validate_evaluation_report


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON object key")
        result[key] = value
    return result


def _reject_nonstandard_constant(value: str):
    raise ValueError("non-standard JSON numeric constant")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate structure and internal consistency of a saved BhashaBridge evaluation report."
    )
    parser.add_argument("report", help="path to a UTF-8 JSON evaluation report")
    args = parser.parse_args(argv)

    path = Path(args.report)
    try:
        if not path.is_file():
            print("Report input error: path is not a readable regular file.", file=sys.stderr)
            return 2
        payload = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        print("Report input error: could not read a UTF-8 report file.", file=sys.stderr)
        return 2

    try:
        parsed = json.loads(
            payload,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_nonstandard_constant,
        )
    except (json.JSONDecodeError, ValueError):
        print("Report is INVALID: malformed or non-standard JSON.")
        return 1

    result = validate_evaluation_report(parsed)
    print(f"Report validation: {result.status}")
    for diagnostic in result.diagnostics:
        print(f"{diagnostic.severity.upper()} {diagnostic.code} at {diagnostic.location}: {diagnostic.message}")
    if result.status == "VALID":
        print("VALID establishes supported-contract structure and internal consistency only.")
        print("It does not authenticate data or establish research evidence.")
        return 0
    if result.status == "UNSUPPORTED_VERSION":
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
