"""Validate a BhashaBridge annotation JSONL file."""
import argparse
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.dataset_validation import validate_dataset

def main(argv=None):
    parser = argparse.ArgumentParser(description="Validate a BhashaBridge annotation JSONL dataset")
    parser.add_argument("dataset", help="UTF-8 JSONL path")
    args = parser.parse_args(argv)
    report = validate_dataset(args.dataset)
    print(f"Dataset: {report.path}")
    print(f"Records examined: {report.records_examined}")
    print(f"Errors: {len(report.errors)}")
    print(f"Warnings: {len(report.warnings)}")
    for kind, issues in (("ERROR", report.errors), ("WARNING", report.warnings)):
        for issue in issues:
            rid = f" record={issue.record_id}" if issue.record_id else ""
            print(f"{kind} line {issue.line}:{rid} {issue.message}")
    return 0 if report.valid else 1

if __name__ == "__main__": raise SystemExit(main())
