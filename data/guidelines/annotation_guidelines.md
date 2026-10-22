# Annotation guidelines (version 1.0)

These instructions support careful draft annotation. They do not turn the project's current rules into linguistic ground truth.

## Scope and preservation

A Romanized Telugu?English code-mixed example contains Telugu words represented in Latin script and English material in the same utterance or sentence. Do not infer that every Latin token is Telugu. Keep `text` exactly as obtained or composed, including script, punctuation, capitalization, emoji, and spelling. Do not silently correct it.

Set `normalized_text` using the project convention: `" ".join(text.split())`. This trims leading/trailing whitespace and collapses each run of whitespace to one ASCII space. It leaves other characters intact. Token offsets refer to this normalized value, as Python Unicode code-point indexes with inclusive `start` and exclusive `end`.

Use the backend tokenizer (`app.services.tokenization.tokenize`) for token boundaries. It groups Unicode letters, numbers, and combining marks; keeps an apostrophe inside a word only when surrounded by word characters; and emits other non-whitespace symbols individually. Indices start at zero in sequence. Never calculate offsets in UTF-8 bytes or UTF-16 code units.

## Language labels

Use the existing labels exactly:

- `TELUGU_ROMANIZED`: use only when there is sufficient evidence the token is Telugu written in Latin script.
- `TELUGU_SCRIPT`: Telugu Unicode script evidence; it does not guarantee the token's language or meaning.
- `ENGLISH`: English token when supported by the annotation evidence.
- `PUNCTUATION`: punctuation/symbol token under the project classifier convention.
- `NUMBER`: numeric token under the project classifier convention.
- `OTHER`: a supported language/script category outside the listed primary labels, with evidence recorded in notes.
- `UNKNOWN`: insufficient evidence for a language label. Unknown is not a semantic ambiguity label.

For mixed-language annotation, label each token independently. Mark a Latin token `TELUGU_ROMANIZED` only when the annotator has sufficient evidence it represents Telugu; mark English only when supported by context or a source. Borrowed words can be difficult to assign: record the convention/source used and use `UNKNOWN` when language identity is not defensible. Do not treat Latin script alone as Telugu evidence. Keep abbreviations and names `UNKNOWN` unless independently supported. Numeric tokens use `NUMBER`; punctuation and standalone symbols follow the tokenizer/classifier labels; emoji are preserved and labeled according to the current classifier output (often `OTHER` or `PUNCTUATION`), without interpreting them as words. Do not force a label. Preserve Telugu-script text as written. Keep punctuation, numeric strings, emoji, and other Unicode symbols as tokenizer emits them; do not convert them into words.

## Interpretation and ambiguity

Only enter `romanized_interpretation` or `telugu_script_equivalent` when the annotator has a defensible source or knowledge and records field-level provenance. Otherwise use `null`. A script equivalent is transliteration; it is not automatically a translation. If a Romanized spelling has multiple plausible readings, preserve the spelling, list only sourced/documented alternatives, explain the uncertainty, and abstain from choosing unless evidence supports one. Never invent transliterations or confidence.

Use `ambiguity: null` when no semantic ambiguity has been established. For a genuine candidate set, list at least two distinct `candidate_id` values, each with a concise meaning and source. Use `status: detected` when alternatives are documented but context has not justified selection; `resolved` only when evidence supports one listed candidate; and `abstained` when evidence is insufficient or conflicting. Detected/abstained records have `selected_candidate: null`. Explain actual evidence and uncertainty. Do not copy the illustrative Phase 3 fixture as verified Telugu-English evidence.

Unknown language identification and semantic ambiguity are separate: an unknown token does not by itself have multiple meanings. Conversely, a known language label does not settle meaning.

## Reference translation

`reference_translation` is nullable. Add a translation only when a qualified annotator supplies and reviews it with an appropriate provenance source. Preserve uncertainty and explain disagreements; do not generate translations just to fill the field. A transliteration, paraphrase, or machine suggestion is not a reference translation. Prepare and review the reference before experimental outputs exist; reference annotators should not see condition outputs or favor a condition's wording. Record the reference language (English for this study) in the dataset release record because schema version 1.0 has no dedicated language-code fields.

For future semantic-preservation evaluation, `intended_meaning` records the reviewed interpretation that raters should preserve. Supply field-level provenance and a source reference. Keep it null when not established; the evaluation-readiness checker requires a reviewed, human-contributed meaning before benchmark use. This metadata does not establish that the interpretation is correct.

## Provenance and review

Every row records `source_type` and `annotation_provenance.method` plus `.details`. Record actual origin, permissions/licensing constraints where applicable, and how annotations were produced. Generated examples must say so; model/rule suggestions are not human-reviewed annotations.

New rows are `annotation_status: draft`. Do not add reviewer identity or date unless supplied by a real reviewer and review actually occurred. To mark a record reviewed, a reviewer must check the source text, normalization, tokenization/labels, every optional linguistic annotation and its evidence, and resolve or record disagreements. Then set both annotation and review statuses to `reviewed`, supply the reviewer identifier/pseudonym and ISO review date, and retain notes. Metadata consistency is not proof that a real review happened; maintain an audit trail outside the validator too.

### Offline annotation workflow

Use `python backend/scripts/annotation_workflow.py --help` for the offline workflow. `create-draft` writes one new JSONL draft and refuses to overwrite its output. Its token labels come from the project's conservative baseline and the row is marked machine-origin and `draft`; treat every label as an annotation suggestion. Add records to a working copy with a text editor or your annotation process. Record the actual source type, source permissions, and annotation method in the supplied metadata and notes.

For each revision, keep the prior JSONL file, make edits in a new copy, run `validate`, then run `record-revision OLD NEW MANIFEST --change-note "..."`. The manifest stores hashes of the exact old and new bytes and a sorted list of changed record IDs; it is deterministic and refuses to replace an existing file. It is an integrity aid, not a digital signature or proof of who made the edit. It requires stable record IDs and structurally valid versions of both datasets.

Only the actual reviewer may enter that review's identifier, date, outcomes, and field-level reviewed provenance after performing the stated checks. The workflow never promotes a draft or fills reviewer metadata. Run `check-readiness` after review and split/group assignment. `export-ready DATASET OUTPUT` copies the complete input byte-for-byte only when the whole dataset passes readiness; the output must be new. It does not filter out ineligible rows, modify annotations, authenticate provenance, or certify linguistic truth. Synthetic records used in software tests are not annotation examples or research evidence.

When annotators disagree, preserve the alternatives and notes; do not silently majority-vote or erase uncertainty. Use `disputed` review status where needed and do not place unresolved records in evaluation data. Resolve disagreements through a documented adjudication by a designated reviewer; record the actual reviewer, date, evidence, and outcome. If unresolved, retain the disagreement and abstain.

## Dataset split metadata

For a future reviewed release, assign each related source/template/paraphrase/ambiguity-context family a stable `split_group` and place the entire group in one `split`: `train`, `validation`, or `test`. Freeze and version the group assignment. The readiness check blocks groups split across partitions and exact duplicate normalized source text both within and across partitions, but it cannot detect semantic near-duplicates or shared templates automatically; review those overlaps manually. Do not add split assignments to illustrative drafts to imply benchmark readiness.

For ambiguity, annotate a record only when at least two plausible interpretations have documented provenance. Record candidate IDs, meanings, sources, actual contextual evidence, and a rule/source identifier. Use `detected` when alternatives are established but no selection is justified; `resolved` only when the evidence supports one listed candidate; use `abstained` when evidence is insufficient or conflicting. In both non-resolved states selection is null. The validator checks consistency but cannot prove the interpretations are correct or that review occurred.

A reference translation is a reviewed English rendering of the source utterance, not a gloss, transliteration, machine suggestion, or paraphrase supplied without review. Record its human or human-and-machine origin, field review status, reviewer metadata, and source/reference identifier. The schema validator checks these claims for consistency, not truth.

For future semantic-preservation annotation, a proposed pilot rubric should compare source and output for (1) core meaning, (2) entities and their roles, (3) negation, (4) tense/aspect where applicable, (5) communicative intent, and (6) important contextual information. Annotators should mark each dimension preserved, changed, omitted, added, or not assessable and cite evidence. This is a proposed protocol requiring pilot testing and inter-annotator review; it is not a validated evaluation method.

## Splits and leakage

Draft/review status and train/development/test split are separate concepts. Do not make an evaluation split from unreviewed drafts. Once a sufficiently reviewed dataset exists, group exact duplicates, near duplicates, paraphrases, shared source items, and repeated templates before deterministic assignment. Keep groups wholly within one split; record split algorithm/version and seed, and freeze assignments for a release. Inspect source overlap and template frequency because these can inflate evaluation. The current schema carries no split assignment and this phase creates no evaluation set.
