# Annotation and Promotion Checklist (Version 1.0)

This checklist operationalises the promotion workflow defined in
`docs/dataset-acquisition-and-review.md`. Complete every item before
changing `annotation_status` from `draft` to `reviewed` or before running
`export-ready`.

---

## Stage 1 — Draft preparation (automatable)

These checks can be run with existing tooling before a reviewer is involved.

- [ ] Each record has a stable, unique `id` that does not imply review status.
- [ ] `text` is the exact, unmodified source utterance.
- [ ] `normalized_text` equals `" ".join(text.split())`.
- [ ] Token boundaries and `surface` values match the project's tokenizer output exactly.
- [ ] Token offsets use Python Unicode code-point indices over `normalized_text`.
- [ ] All `language_label` values are from the permitted set.
- [ ] `annotation_status` is `draft`.
- [ ] `review` is absent or `{"status": "not_reviewed"}`.
- [ ] `reference_translation` and `intended_meaning` are `null` (or present with `not_reviewed` field provenance if draft candidates are recorded separately).
- [ ] `source_type` and `annotation_provenance` accurately describe how the example was created.
- [ ] Structural validator exits 0: `python backend/scripts/validate_dataset.py <path>`

**Automated gate:** Structural validation must exit 0. Warnings (draft status) are expected and do not block this stage.

---

## Stage 2 — Independent annotation (requires human reviewer)

A qualified bilingual Telugu–English reviewer performs these steps.
The reviewer must not have been involved in system development, normalization rule writing, or transliteration resource development.

- [ ] Reviewer has read the reviewer handoff package (`data/guidelines/reviewer_handoff.md`).
- [ ] Reviewer has read the annotation guidelines (`data/guidelines/annotation_guidelines.md`).
- [ ] For each record, reviewer has read the source text exactly as written.
- [ ] Reviewer has recorded the **intended meaning** in English.
- [ ] Reviewer has written an **English reference translation** without seeing any system output or condition output.
- [ ] Reviewer has confirmed or corrected all `language_label` values, recording disagreements and evidence.
- [ ] For tokens labeled `UNKNOWN`, reviewer has assessed whether a specific label is defensible.
- [ ] For records with flagged ambiguity, reviewer has listed candidate interpretations with evidence, and recorded resolution or abstention.
- [ ] Reviewer has identified any **protected entities** (named entities, app names, kin terms) that must not be normalized or transliterated.
- [ ] Reviewer has assessed any proposed normalization for meaning preservation.
- [ ] Reviewer has assessed any proposed transliteration for appropriateness and meaning preservation.
- [ ] Reviewer has recommended exclusion of any record that is unintelligible, unethical, or uninterpretable.
- [ ] All annotations have been recorded in the offline annotation log with the reviewer's pseudonymous identifier.

**This stage cannot be simulated, automated, or skipped.** A record cannot advance to Stage 3 until a real, independent human reviewer has performed these steps.

---

## Stage 3 — Review and disagreement resolution (requires second annotator where feasible)

- [ ] Where a second annotator is available, they have reviewed the intended meaning and reference translation independently.
- [ ] Disagreements between annotators have been recorded with both positions and evidence.
- [ ] A designated adjudicator has resolved or recorded unresolved disagreements.
- [ ] Records with unresolvable disagreements are marked `disputed` and excluded from evaluation populations.
- [ ] Exclusion recommendations have been reviewed by the project team.
- [ ] **If only one reviewer is available:** This limitation is explicitly documented in the dataset manifest. No inter-annotator agreement score is reported.

---

## Stage 4 — Record promotion (requires all of Stage 2 complete)

A record may be promoted from `draft` to `reviewed` only when **all** of the following are true:

- [ ] A real reviewer has completed Stage 2 for this record.
- [ ] `annotation_status` is being set to `reviewed` by (or under the direct instruction of) the actual reviewer.
- [ ] `review.status` is set to `reviewed`.
- [ ] `review.reviewer_id` contains the reviewer's actual pseudonymous identifier.
- [ ] `review.reviewed_at` contains the actual date of review (YYYY-MM-DD).
- [ ] `reference_translation` contains the reviewer's approved English translation.
- [ ] `annotation_provenance.fields.reference_translation` is present with:
  - `origin`: `human` or `human_and_machine`
  - `review_status`: `reviewed`
  - `details`: non-empty description of how the translation was produced
  - `source_reference`: reference to the offline annotation log entry
- [ ] `intended_meaning` contains the reviewer's approved meaning statement.
- [ ] `annotation_provenance.fields.intended_meaning` is present with the same requirements as `reference_translation` above.
- [ ] All `language_label` corrections from the reviewer have been applied.
- [ ] The structural validator still exits 0 after changes.

**Do not promote a record by setting `annotation_status: reviewed` without a real reviewer having performed Stage 2.** The validator checks consistency of metadata but cannot authenticate the review.

---

## Stage 5 — Split and group assignment (after Stage 4)

- [ ] Every related record (same source template, near-paraphrase, same ambiguity scenario) has been assigned to the same `split_group`.
- [ ] Each `split_group` is wholly contained within one `split` value (train, validation, or test).
- [ ] No `split_group` crosses partition boundaries.
- [ ] Test records have not been used in normalization rule development, transliteration resource development, or system prompt tuning.
- [ ] Test records have at least one `TELUGU_ROMANIZED` and one `ENGLISH` token.
- [ ] The split assignment algorithm (deterministic method, seed) is documented outside the JSONL file.
- [ ] No exact normalized-source-text duplicate appears across splits.
- [ ] No exact normalized-source-text duplicate appears within the same split.
- [ ] The structural validator exits 0.
- [ ] The readiness checker exits 0: `python backend/scripts/check_evaluation_readiness.py <path>`

---

## Stage 6 — Promotion to evaluation eligibility

Run the full promotion checklist:

```powershell
python backend/scripts/validate_dataset.py path/to/candidate.jsonl
python backend/scripts/check_evaluation_readiness.py path/to/candidate.jsonl
python backend/scripts/annotation_workflow.py check-readiness path/to/candidate.jsonl
```

All three must exit 0. Inspect every diagnostic before promoting.

**Current pilot status (pilot_v0.1):** Does NOT satisfy Stage 2, 3, 4, or 5. The readiness checker exits 1 (NOT READY) for all 28 records. This is the correct and expected status for an unreviewed draft.

---

## Exclusion log template

For each excluded record, maintain an entry in the offline exclusion log:

| Field | Value |
|---|---|
| Record ID | e.g., `pilot-007` |
| Exclusion reason | e.g., "unintelligible source text" |
| Stage at exclusion | e.g., "Stage 2 — reviewer recommendation" |
| Reviewer/adjudicator | Reviewer pseudonymous ID |
| Date | YYYY-MM-DD |
| Affected evaluation populations | e.g., "all conditions" |

---

*This checklist is part of BhashaBridge 2.0 Phase 28. It implements the promotion workflow described in `docs/dataset-acquisition-and-review.md`.*
