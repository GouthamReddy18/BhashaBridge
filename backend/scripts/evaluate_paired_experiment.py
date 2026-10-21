"""Score explicit paired-experiment JSONL artifacts against reviewed annotations."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from types import UnionType
from typing import Union, get_args, get_origin

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pydantic import BaseModel, ValidationError

from app.schemas.evaluation import PairedEvaluationArtifact
from app.services.dataset_validation import _unique_object_pairs, validate_dataset
from app.services.evaluation import evaluate_paired_records
from app.services.evaluation_readiness import check_evaluation_readiness


def _reject_unknown_model_fields(value, annotation, location="paired artifact"):
    origin = get_origin(annotation)
    args = get_args(annotation)
    if origin in (Union, UnionType):
        for option in args:
            if option is not type(None):
                _reject_unknown_model_fields(value, option, location)
        return
    if origin in (list, tuple, set, frozenset):
        if isinstance(value, (list, tuple, set, frozenset)) and args:
            for item in value:
                _reject_unknown_model_fields(item, args[0], location)
        return
    if origin is dict:
        if isinstance(value, dict) and len(args) == 2:
            for item in value.values():
                _reject_unknown_model_fields(item, args[1], location)
        return
    try:
        is_model = isinstance(annotation, type) and issubclass(annotation, BaseModel)
    except TypeError:
        is_model = False
    if is_model:
        if not isinstance(value, dict):
            return  # Pydantic produces the actionable type error.
        model_fields = annotation.model_fields
        if set(value) - set(model_fields):
            raise ValueError(f"unsupported property at {location}")
        for key, field in model_fields.items():
            if key in value:
                _reject_unknown_model_fields(value[key], field.annotation, f"{location}.{key}")


def _read_jsonl(path: Path, *, paired: bool) -> list[tuple[int, dict]] | list[PairedEvaluationArtifact]:
    rows = []
    try:
        with path.open(encoding="utf-8") as stream:
            for line_number, raw in enumerate(stream, start=1):
                if not raw.strip():
                    continue
                try:
                    value = json.loads(raw, object_pairs_hook=_unique_object_pairs)
                except (json.JSONDecodeError, ValueError) as exc:
                    raise ValueError(f"line {line_number}: malformed JSON ({type(exc).__name__})") from None
                if paired:
                    try:
                        _reject_unknown_model_fields(value, PairedEvaluationArtifact)
                        rows.append(PairedEvaluationArtifact.model_validate(value))
                    except ValidationError as exc:
                        first = exc.errors(include_input=False, include_context=False)[0]
                        location = ".".join(str(part) for part in first["loc"])
                        raise ValueError(
                            f"line {line_number}: paired artifact schema error at {location} ({first['type']})"
                        ) from None
                    except ValueError as exc:
                        raise ValueError(f"line {line_number}: {exc}") from None
                else:
                    if not isinstance(value, dict):
                        raise ValueError(f"line {line_number}: annotation row must be a JSON object")
                    rows.append((line_number, value))
    except OSError as exc:
        raise ValueError(f"cannot read {'paired results' if paired else 'annotations'} file: {exc}") from None
    except UnicodeError:
        raise ValueError(f"cannot decode {'paired results' if paired else 'annotations'} file as UTF-8") from None
    return rows


def _write_report(path: Path, payload: str, *, overwrite: bool) -> None:
    if not path.parent.exists():
        raise ValueError("output directory does not exist")
    mode = "w" if overwrite else "x"
    try:
        with path.open(mode, encoding="utf-8", newline="\n") as stream:
            stream.write(payload)
            stream.write("\n")
    except FileExistsError:
        raise ValueError("output file already exists; pass --overwrite to replace it") from None
    except OSError as exc:
        raise ValueError(f"cannot write evaluation report: {exc}") from None


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate paired direct/assisted translations against an explicitly supplied reviewed annotation JSONL."
    )
    parser.add_argument("--annotations", required=True, help="annotation JSONL validated by the project readiness checker")
    parser.add_argument("--paired-results", required=True, help="versioned paired experiment JSONL artifact")
    parser.add_argument("--split", required=True, choices=("train", "validation", "test"), help="dataset split to score")
    parser.add_argument("--output", required=True, help="new JSON report path")
    parser.add_argument("--dataset-label", default="supplied-dataset", help="safe human-readable label; no path is included by default")
    parser.add_argument("--overwrite", action="store_true", help="allow replacing an existing report file")
    parser.add_argument("--include-per-example", action="store_true", help="include IDs and sentence-level proxy scores; no source or translation text")
    args = parser.parse_args(argv)

    annotation_path = Path(args.annotations)
    pair_path = Path(args.paired_results)
    output_path = Path(args.output)
    try:
        resolved_output = output_path.resolve()
        if resolved_output in {annotation_path.resolve(), pair_path.resolve()}:
            raise ValueError("report output must not overwrite either input artifact")
        if resolved_output.exists() and not args.overwrite:
            raise ValueError("output file already exists; pass --overwrite to replace it")

        structural = validate_dataset(annotation_path)
        if structural.errors:
            print(f"Annotation structural validation failed with {len(structural.errors)} error(s).", file=sys.stderr)
            for issue in structural.errors:
                print(f"line {issue.line}: {issue.message}", file=sys.stderr)
            return 2

        annotation_rows = _read_jsonl(annotation_path, paired=False)
        pair_rows = _read_jsonl(pair_path, paired=True)
        readiness = check_evaluation_readiness(annotation_path)
        report = evaluate_paired_records(
            dataset_label=args.dataset_label,
            split=args.split,
            annotation_rows=annotation_rows,
            readiness=readiness,
            paired_artifacts=pair_rows,
            include_per_example=args.include_per_example,
        )
        payload = json.dumps(
            report.model_dump(mode="json"), ensure_ascii=False, indent=2, sort_keys=True,
        )
        _write_report(output_path, payload, overwrite=args.overwrite)
    except ValueError as exc:
        print(f"Evaluation input/output error: {exc}", file=sys.stderr)
        return 2

    print(f"Evaluation status: {report.evaluation_status}")
    print(f"Records discovered: {report.records_discovered}")
    print(f"Eligible records: {report.eligible_records}")
    print(f"Matched successful pairs: {report.matched_output_pairs}")
    print(f"Report: {output_path}")
    return 0 if report.evaluation_status == "evaluated" else 1


if __name__ == "__main__":
    raise SystemExit(main())
