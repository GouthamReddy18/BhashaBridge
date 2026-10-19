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

Names, abbreviations, and unfamiliar spellings may remain `UNKNOWN`. Do not force a label. Preserve Telugu-script text as written. Keep punctuation, numeric strings, emoji, and other Unicode symbols as tokenizer emits them; do not convert them into words.

## Interpretation and ambiguity

Only enter `romanized_interpretation` or `telugu_script_equivalent` when the annotator has a defensible source or knowledge and records the provenance. Otherwise use `null`. A script equivalent is transliteration; it is not automatically a translation.

Use `ambiguity: null` when no semantic ambiguity has been established. For a genuine candidate set, list at least two distinct `candidate_id` values, each with a concise meaning and source. Use `status: detected` when alternatives are documented but context has not justified selection; `resolved` only when evidence supports one listed candidate; and `abstained` when evidence is insufficient or conflicting. Detected/abstained records have `selected_candidate: null`. Explain actual evidence and uncertainty. Do not copy the illustrative Phase 3 fixture as verified Telugu-English evidence.

Unknown language identification and semantic ambiguity are separate: an unknown token does not by itself have multiple meanings. Conversely, a known language label does not settle meaning.

## Reference translation

`reference_translation` is nullable. Add a translation only when a qualified annotator supplies and reviews it with an appropriate provenance source. Preserve uncertainty and explain disagreements; do not generate translations just to fill the field. A transliteration, paraphrase, or machine suggestion is not a reference translation.

## Provenance and review

Every row records `source_type` and `annotation_provenance.method` plus `.details`. Record actual origin, permissions/licensing constraints where applicable, and how annotations were produced. Generated examples must say so; model/rule suggestions are not human-reviewed annotations.

New rows are `annotation_status: draft`. Do not add reviewer identity or date unless supplied by a real reviewer and review actually occurred. To mark a record reviewed, a reviewer must check the source text, normalization, tokenization/labels, every optional linguistic annotation and its evidence, and resolve or record disagreements. Then set both annotation and review statuses to `reviewed`, supply the reviewer identifier/pseudonym and ISO review date, and retain notes. Metadata consistency is not proof that a real review happened; maintain an audit trail outside the validator too.

When annotators disagree, preserve the alternatives and notes; do not silently majority-vote or erase uncertainty. Use `disputed` review status where needed and do not place unresolved records in evaluation data.

## Splits and leakage

Draft/review status and train/development/test split are separate concepts. Do not make an evaluation split from unreviewed drafts. Once a sufficiently reviewed dataset exists, group exact duplicates, near duplicates, paraphrases, shared source items, and repeated templates before deterministic assignment. Keep groups wholly within one split; record split algorithm/version and seed, and freeze assignments for a release. Inspect source overlap and template frequency because these can inflate evaluation. The current schema carries no split assignment and this phase creates no evaluation set.
