# Data

`samples/illustrative.jsonl` contains schema-conforming illustrative examples only. It is not a validated benchmark, has no train/test split, and must not be used to report evaluation scores. Establish annotations and licensing provenance before quantitative work.

`samples/lid_illustrative.jsonl` demonstrates possible token-level language labels and intentionally includes `UNKNOWN` examples. These labels are illustrative, not independently reviewed or suitable for accuracy claims.
## Phase 4 annotation structure

- `schema/annotation.schema.json`: structural record schema, version 1.0.
- `guidelines/annotation_guidelines.md`: annotation and review process.
- `drafts/illustrative_examples.jsonl`: 16 synthetic, machine-generated draft examples; not ground truth.
- `reviewed/`: currently contains no human-reviewed dataset.
- `splits/`: documented future split/leakage policy; no split is created.

Each JSONL record preserves original `text`, project-normalized text, provenance, token surfaces/labels/code-point offsets, nullable interpretation/transliteration/ambiguity/translation fields, and optional review metadata. Add new drafts without overwriting existing `samples/`. Validate with `python backend/scripts/validate_dataset.py path/to/file.jsonl`. The validator checks JSONL and structural constraints using JSON Schema conventions, plus Python-only cross-row IDs, duplicate object keys, project normalization/token boundaries, candidate ID uniqueness, and cross-field provenance/review consistency. It cannot establish linguistic correctness, licensing, or that a person actually reviewed a record. No human-reviewed benchmark or measured Telugu-English ambiguity/semantic-preservation result is available. A later reviewed corpus can support comparative translation and semantic-preservation evaluation, but this phase does not perform those experiments.

Phase 6D.1 adds optional `intended_meaning`, `split`, and `split_group` metadata to annotation schema version 1.0. Existing records remain valid without those fields. Check benchmark eligibility with `python backend/scripts/check_evaluation_readiness.py path/to/file.jsonl`; this read-only check reuses structural validation and requires reviewed human-contributed meaning/reference provenance and group-aware split metadata. The 16 synthetic drafts remain not evaluation-ready. Phase 6D.2 adds the offline scoring service and CLI, but no empirical score is available. See [the evaluation protocol](../docs/evaluation_protocol.md) for eligibility, metric settings, human assessment, and leakage controls.

The offline annotation workflow is `python backend/scripts/annotation_workflow.py --help`. It can create a new machine-labeled draft scaffold, validate data, check readiness, record hash-linked revisions, and copy a whole ready dataset to a new path without overwriting. The tool does not assign human review metadata or filter partially eligible data into a benchmark. See the [annotation workflow guidance](guidelines/annotation_guidelines.md#offline-annotation-workflow).
