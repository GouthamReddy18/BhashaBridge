"""Validate a versioned four-condition evaluation report."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.four_condition_evaluation import validate_four_condition_report  # noqa: E402
from app.services.dataset_validation import _unique_object_pairs  # noqa: E402


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report")
    args = parser.parse_args(argv)
    try:
        with Path(args.report).open(encoding="utf-8") as stream:
            report = json.load(stream, object_pairs_hook=_unique_object_pairs)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
        print("Invalid four-condition report: unreadable JSON or duplicate keys", file=sys.stderr)
        return 2
    valid, errors = validate_four_condition_report(report)
    if not valid:
        print("Invalid four-condition report:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Valid four-condition evaluation report.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
