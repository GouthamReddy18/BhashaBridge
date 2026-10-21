"""Check whether an annotation JSONL file is ready for future evaluation."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.evaluation_readiness import check_evaluation_readiness


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Check reviewed dataset eligibility for future research evaluation"
    )
    parser.add_argument("dataset", help="UTF-8 JSONL path")
    args = parser.parse_args(argv)
    report = check_evaluation_readiness(args.dataset)
    print(f"Dataset: {report.path}")
    print(f"Records examined: {report.records_examined}")
    print(f"Readiness: {'READY' if report.ready else 'NOT READY'}")
    print(f"Errors: {len(report.errors)}")
    print(f"Warnings: {len(report.warnings)}")
    for kind, issues in (("ERROR", report.errors), ("WARNING", report.warnings)):
        for issue in issues:
            rid = f" record={issue.record_id}" if issue.record_id else ""
            print(f"{kind} line {issue.line}:{rid} {issue.message}")
    return 0 if report.ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
