"""Offline draft, validation, revision-manifest, and eligible-export workflow."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.annotation_workflow import (  # noqa: E402
    WorkflowError,
    create_draft,
    export_ready_dataset,
    write_revision_manifest,
)
from app.services.dataset_validation import validate_dataset  # noqa: E402
from app.services.evaluation_readiness import check_evaluation_readiness  # noqa: E402


def _show_report(report, heading: str) -> None:
    print(f"{heading}: {report.path}")
    print(f"Records examined: {report.records_examined}")
    print(f"Errors: {len(report.errors)}")
    print(f"Warnings: {len(report.warnings)}")
    for kind, issues in (("ERROR", report.errors), ("WARNING", report.warnings)):
        for issue in issues:
            rid = f" record={issue.record_id}" if issue.record_id else ""
            print(f"{kind} line {issue.line}:{rid} {issue.message}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    draft = commands.add_parser("create-draft", help="create a new unreviewed draft record")
    draft.add_argument("output", help="new UTF-8 JSONL output path; must not exist")
    draft.add_argument("--id", required=True, dest="record_id")
    draft.add_argument("--text", required=True)
    draft.add_argument("--source-type", required=True)
    draft.add_argument("--source-details", required=True, help="actual source/method notes; no review claim")

    validate = commands.add_parser("validate", help="run structural dataset validation")
    validate.add_argument("dataset")

    readiness = commands.add_parser("check-readiness", help="check benchmark eligibility")
    readiness.add_argument("dataset")

    export = commands.add_parser("export-ready", help="copy a whole eligible dataset to a new path")
    export.add_argument("dataset")
    export.add_argument("output", help="new output path; existing files are never overwritten")

    revision = commands.add_parser("record-revision", help="write a hash-linked manifest for a manually revised dataset")
    revision.add_argument("original")
    revision.add_argument("revised")
    revision.add_argument("manifest", help="new manifest path; existing files are never overwritten")
    revision.add_argument("--change-note", required=True, help="human-supplied description of the revision")

    args = parser.parse_args(argv)
    try:
        if args.command == "create-draft":
            output = create_draft(
                args.output,
                record_id=args.record_id,
                text=args.text,
                source_type=args.source_type,
                source_details=args.source_details,
            )
            print(f"Draft created: {output} (annotation_status=draft; no review claimed)")
            return 0
        if args.command == "validate":
            report = validate_dataset(args.dataset)
            _show_report(report, "Dataset")
            return 0 if report.valid else 1
        if args.command == "check-readiness":
            report = check_evaluation_readiness(args.dataset)
            _show_report(report, "Dataset readiness")
            print(f"Readiness: {'READY' if report.ready else 'NOT READY'}")
            return 0 if report.ready else 1
        if args.command == "export-ready":
            output = export_ready_dataset(args.dataset, args.output)
            print(f"Eligible dataset exported without modification: {output}")
            return 0
        if args.command == "record-revision":
            manifest = write_revision_manifest(
                args.original, args.revised, args.manifest, change_note=args.change_note
            )
            print(f"Revision manifest created: {manifest}")
            return 0
    except WorkflowError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
