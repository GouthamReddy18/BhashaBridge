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
