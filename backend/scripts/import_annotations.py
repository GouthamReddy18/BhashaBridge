"""CLI for importing reviewer annotations and generating reviewer CSV templates."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.annotation_import import (  # noqa: E402
    import_reviewer_annotations,
    write_merged_dataset,
    write_reviewer_template,
)


def _show_issues(issues, heading: str) -> None:
    for issue in issues:
        row_str = f" row {issue.row}" if issue.row is not None else ""
        ex_str = f" record={issue.example_id}" if issue.example_id else ""
        field_str = f" [{issue.field}]" if issue.field else ""
        print(f"{heading}{row_str}{ex_str}{field_str}: {issue.message}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Subcommand: generate-template
    gen_parser = subparsers.add_parser(
        "generate-template",
        help="Generate a blank reviewer CSV template pre-populated from a pilot draft dataset",
    )
    gen_parser.add_argument(
        "--pilot",
        required=True,
        help="Path to source pilot draft JSONL (e.g. data/drafts/pilot_examples.jsonl)",
    )
    gen_parser.add_argument(
        "--output",
        required=True,
        help="Destination path for the generated CSV template",
    )

    # Subcommand: import
    imp_parser = subparsers.add_parser(
        "import",
        help="Validate completed reviewer CSV annotations and optionally merge into a draft JSONL",
    )
    imp_parser.add_argument(
        "--pilot",
        required=True,
        help="Path to original pilot draft JSONL",
    )
    imp_parser.add_argument(
        "--csv",
        required=True,
        help="Path to completed reviewer CSV file",
    )
    imp_parser.add_argument(
        "--meta",
        default=None,
        help="Optional path to external reviewer metadata JSON file",
    )
    imp_parser.add_argument(
        "--output-jsonl",
        default=None,
        help="Optional new output JSONL path to write merged annotations if validation succeeds",
    )

    args = parser.parse_args(argv)

    try:
        if args.command == "generate-template":
            out_path = write_reviewer_template(args.pilot, args.output)
            print(f"Reviewer template CSV written: {out_path}")
            return 0

        if args.command == "import":
            result = import_reviewer_annotations(
                pilot_path=args.pilot,
                csv_path=args.csv,
                reviewer_meta_path=args.meta,
            )
            print(f"Source pilot: {result.source_path}")
            print(f"Rows examined: {result.rows_examined}")
            print(f"Errors: {len(result.errors)}")
            print(f"Warnings: {len(result.warnings)}")
            _show_issues(result.errors, "ERROR")
            _show_issues(result.warnings, "WARNING")

            if not result.valid:
                print("Import validation FAILED: reviewer annotations contain errors.", file=sys.stderr)
                return 1

            print("Import validation PASSED: all reviewed rows are structurally consistent with pilot.")
            if args.output_jsonl:
                merged_path = write_merged_dataset(result.merged_records, args.output_jsonl)
                print(f"Merged draft JSONL written: {merged_path}")
                print("Note: Imported records remain in 'draft' status until Stage 4 promotion checklist is complete.")

            return 0

    except (OSError, ValueError) as exc:
        print(f"Import command error: {exc}", file=sys.stderr)
        return 2

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
