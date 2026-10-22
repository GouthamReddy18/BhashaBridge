# Dataset acquisition and review guide

This guide describes how to prepare a real dataset for the existing annotation schema and readiness checker. It does not create examples, grant usage rights, certify a review, or make the illustrative drafts eligible.

## 1. Define the release before collecting

Create a dataset release record outside the JSONL file that identifies its version, collection period/method, source language scope, English reference language, source rights and restrictions, source families, annotation protocol version, and split assignment version. Treat source language as Telugu-English code-mixed (including the script forms admitted by the study) and reference language as English. Keep exact source identifiers or private participant details out of public examples when consent or privacy requires; maintain any protected source mapping separately with appropriate access controls.

Use only sources for which collection and reuse are permitted. Record the license or permission basis, attribution conditions, retention limits, and any consent constraints. If rights are unclear, exclude the source until resolved. Do not infer a permissive license from public availability.

## 2. Collect and annotate each example

1. Preserve the source utterance exactly in `text`; do not silently normalize spelling, grammar, punctuation, or code-mixing.
2. Assign a stable, non-personal `id`. Record `source_type` and the actual collection/provenance method and details.
3. Compute `normalized_text` using the current convention, `" ".join(text.split())`, and use the project's tokenizer for indices and Python Unicode code-point offsets.
4. Label tokens conservatively. Use `UNKNOWN` when a Latin spelling, name, borrowing, abbreviation, or language identity is uncertain. Script is evidence about script, not proof of language or meaning.
5. Add Romanized interpretations, Telugu-script equivalents, ambiguity alternatives, and selected meanings only when supported by cited evidence. Keep unresolved or conflicting meaning explicitly abstained/disputed.
6. Have a qualified annotator create and review the English reference independently of system outputs and condition labels. The reference should communicate the utterance's intended content, not favor a particular condition's wording. Record `reference_translation` and `intended_meaning`, with field-level human provenance and a source reference.
7. Record source and reference language in the dataset release record. The current record schema does not have dedicated language-code fields; do not add undocumented fields to version 1.0 records.

Machine suggestions can assist workflow but remain machine-origin until a human actually reviews each relevant field. Never copy generated translation output into the reference field as if it were ground truth.

## 3. Independent review and adjudication

New records stay `draft`. An actual reviewer checks source fidelity, whitespace normalization, token surfaces/offsets, language labels, optional interpretations, ambiguity evidence, intended meaning, and reference translation. Only that person records the reviewer identifier or pseudonym, review date, review status, and field-level review provenance after completing the review.

Where feasible, a second annotator independently reviews meaning and translation before seeing the first annotator's decisions. Preserve disagreements and cited evidence. A designated adjudicator records the alternatives, evidence, date, and resolution. If evidence does not resolve the issue, retain uncertainty and exclude the example from the relevant evaluation population. Do not silently majority-vote or rewrite an uncertain source.

## 4. Reference and semantic-rating safeguards

Prepare references and intended meanings before experimental outputs are produced. Reference annotators should not see condition outputs or know which condition will be evaluated. Keep held-out test references unavailable to rule/resource developers.

The existing 0–4 human rating is a proposed ordinal assessment, not a validated instrument. Raters compare each translation against both the original utterance and reviewed intended meaning; they judge meaning separately from fluency. Consider:

- core event, participants, and their roles;
- negation, modality, tense/aspect, and communicative intent where present;
- named entities and code-mixed expressions;
- omissions of material meaning;
- unsupported additions or hallucinated details;
- contextual meaning where the source is ambiguous.

Rate an omission, role reversal, polarity change, or unsupported addition as a semantic error proportional to its effect on the core meaning. Do not penalize harmless paraphrase or grammatical variation. Record uncertainty and the affected span/proposition. Use `not assessable` only in a separately approved dimension-level form; the existing 0–4 record has no per-dimension or not-assessable field. Pilot the instructions and measure independent agreement before treating these ratings as a validated outcome. Never derive human ratings from BLEU/chrF.

## 5. Split and leakage controls

Identify groups before splitting. Keep source conversations, source families, near-duplicates, paraphrases, repeated templates, generated variants, and repeated ambiguity contexts together. Assign each group wholly to one partition; version and freeze the mapping and its deterministic method/seed. Keep test examples, references, and ratings out of normalization/rule development.

The current readiness checker verifies group consistency and blocks exact normalized-source duplicates within and across splits. It does not discover semantic near-duplicates, source families, or shared templates. Review these manually and document exclusions. Do not place unreviewed illustrative drafts in a train/validation/test split to make readiness pass.

## 6. Exclusions, failures and missing data

Maintain a pre-scoring exclusion log with stable example IDs, reason, reviewer/adjudication reference, and affected analysis population. Exclude records with unresolved source meaning, unsupported rights, invalid references, material annotation conflict, or unresolved leakage. Keep all eligible examples in the operational denominator after the dataset gate; do not drop a record merely because a provider failed. Report failed, unavailable, disabled, missing, invalid, and blocked outcomes separately. Metric scores use only successful, nonblank outputs; paired comparisons additionally require the same eligible example IDs and reference. Never impute failed or missing translations as zero scores.

Do not prescribe a minimum dataset size here. A pilot may establish collection and workflow feasibility; a powered study size requires a defined outcome, target effect, and justified variance assumptions.

## 7. Repeatable validation and promotion checklist

For every candidate release, preserve the previous immutable version and a human-readable change note. Run these commands from the repository root with the intended Python environment:

```powershell
python backend/scripts/validate_dataset.py path/to/candidate.jsonl
python backend/scripts/check_evaluation_readiness.py path/to/candidate.jsonl
python backend/scripts/annotation_workflow.py check-readiness path/to/candidate.jsonl
```

Structural validation must exit 0. Readiness must report `READY` and exit 0 for the full release; inspect every diagnostic and warning rather than relying only on the exit code. The annotation workflow does not set review metadata. It can record a hash-linked revision manifest and export a complete ready file to a new destination; it never filters or repairs a release.

Before promoting a release, verify all of the following:

- [ ] Collection source, rights/permission basis, restrictions, and dataset version are documented.
- [ ] IDs are stable and unique; each source is intact and has the required provenance.
- [ ] Normalized text, tokenization, labels, offsets, and optional linguistic annotations are reviewed.
- [ ] English references and intended meanings were independently prepared/reviewed without condition-output bias.
- [ ] Field-level provenance and actual reviewer metadata match work performed; disagreements are resolved or excluded.
- [ ] Source/reference language scope is recorded in the release record.
- [ ] Group assignments cover duplicate, near-duplicate, template, source-family, and repeated-context risks.
- [ ] Splits are frozen, groups do not cross partitions, and test material was not used for development.
- [ ] Structural validation exits 0; readiness exits 0; diagnostics and warnings are reviewed.
- [ ] A hash-linked revision/release record is retained; the release is immutable once used for a final evaluation.

The validator checks structure and declared metadata. It cannot authenticate consent, licensing, reviewer identity, linguistic truth, or the completeness of human leakage review.
