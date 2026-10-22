"""Compose a validated descriptive research report from saved artifacts."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.research_reporting import ResearchReportError, build_research_report_file  # noqa: E402


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evaluation-report", required=True)
    parser.add_argument("--human-ratings", help="optional output from the human-rating aggregator")
    parser.add_argument("--output", required=True, help="new JSON report path; existing files are never overwritten")
    args = parser.parse_args(argv)
    try:
        output = build_research_report_file(
            args.evaluation_report, args.output, human_ratings_path=args.human_ratings,
        )
    except ResearchReportError as exc:
        print(f"Research report blocked: {exc}", file=sys.stderr)
        return 1
    print(f"Research report: {output}")
    print("Descriptive report only; no causal or statistical inference is made.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
