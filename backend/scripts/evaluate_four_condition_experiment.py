"""Evaluate a four-condition JSONL artifact without provider calls."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.four_condition_evaluation import (  # noqa: E402
    FourConditionEvaluationError, evaluate_four_condition_files,
    validate_four_condition_report,
)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--annotations", required=True)
    parser.add_argument("--artifacts", required=True)
    parser.add_argument("--dataset-label", required=True)
    parser.add_argument("--split", required=True, choices=("train", "validation", "test"))
    parser.add_argument("--output", required=True, help="new report path; existing files are never overwritten")
    args = parser.parse_args(argv)
    destination = Path(args.output)
    try:
        report = evaluate_four_condition_files(
            args.annotations, args.artifacts, dataset_label=args.dataset_label,
            split=args.split,
        )
        valid, errors = validate_four_condition_report(report.model_dump(mode="json"))
        if not valid:
            raise FourConditionEvaluationError("internal report validation failed: " + ", ".join(errors))
        payload = json.dumps(report.model_dump(mode="json"), ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
        with destination.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(payload)
    except (FourConditionEvaluationError, OSError, ValueError) as exc:
        print(f"Four-condition evaluation blocked: {exc}", file=sys.stderr)
        return 2
    print(f"Four-condition report written: {destination}")
    print(f"Report status: {report.report_status}; eligible rows: {report.eligible_records}; orphan artifacts: {report.orphan_artifacts}")
    return 0 if report.report_status in {"evaluated", "no_metric_population"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
