# Project engineering status

**Status checked:** 2026-10-22\
**Checkpoint:** Phase 6D.3, `e59234b` (`feat: add evaluation report integrity validation`)\
**Roadmap note:** No independent master implementation roadmap was found in the repository. The later phase labels in the continuation prompt are proposed engineering stages, not verified original roadmap labels.

## Current readiness

| Requirement | Status | Evidence and remaining work |
|---|---|---|
| Core analysis API | Implemented and verified | FastAPI health, readiness, and analysis endpoints; the 211-test backend suite passes. Rule-based labels and the narrow ambiguity example are not measured linguistic models. |
| Annotation format and structural validation | Implemented and verified | Version 1.0 JSON Schema, annotation guidance, and read-only JSONL validator. Structural validity does not establish linguistic accuracy, permission to use a source, or actual review. |
| Dataset eligibility | Implemented; real reviewed data unavailable | Readiness checks require completed human review, human-contributed field provenance, references, intended meaning, and group-aware split metadata. The 16 illustrative drafts are structurally valid but not eligible. |
| Annotation and review workflow | Requires human contribution; workflow preparation pending | The schema and guidance describe draft and review metadata, but there is no safe draft/edit/review/export CLI workflow or audit history. A person must supply and attest to each review; software must not mark records reviewed on their behalf. |
| Dataset quality safeguards | Partly implemented; real-data validation pending | Structural checks cover duplicate IDs, malformed and duplicate-key JSON, tokenizer spans, field provenance consistency, and value constraints. Readiness detects split-group conflicts and exact normalized-source duplicates across splits. Paraphrase, shared-template, source-family, and semantic leakage still need human review and explicit group assignment. |
| English reference translations and intended meanings | Requires human contribution | The schema and readiness checker support them. No eligible reviewed examples are present. Machine suggestions are not references or reviewed meanings. |
| Dataset provenance and licensing | Requires human contribution | Provenance fields and guidance exist, but claims are not independently authenticated and source permissions have not been established for an evaluation corpus. |
| Paired experiment orchestration | Implemented and tested with fixtures; real execution unavailable | Stable direct/assisted arm identity, execution order, and per-arm outcomes are represented. The default assisted path has no verified linguistic replacements. There is no persistence or genuine eligible dataset to execute. |
| Translation provider | Optional and unavailable | A provider-independent text seam exists; the default app has no provider. The seam cannot pass target-language or generation settings, and synchronous calls have no explicit timeout/cancellation boundary. No credentials or provider configuration are present. |
| Verified linguistic transformations | Blocked on reviewed resources | Rule tracing and opt-in synthetic fixtures exist. Production substitutions are disabled; no reviewed Telugu-English transformation resource is available. |
| BLEU and chrF | Implemented and verified as software; empirical use pending | Phase 6D.2 implements project-versioned corpus metrics and a report CLI. Scores require eligible human-reviewed references and genuine provider outputs. These proxies do not measure semantic preservation by themselves. |
| Evaluation report integrity | Implemented and tested; provenance is not authenticated | Phase 6D.3 checks schema and internal consistency for saved reports. It does not authenticate source artifacts, independently recompute scores, or establish that provider output is genuine. |
| Human semantic-preservation judgments | Requires human contribution; workflow pending | There are no ratings, rubric data, rating-entry or aggregation workflow, or inter-rater agreement results. BLEU/chrF must not be substituted for human judgments. |
| Statistical analysis and research conclusions | Deferred until genuine evidence exists | No eligible benchmark, paired real-provider outputs, or human judgments are available. No significance or causal-improvement claim is supported. |
| Frontend | Implemented for supported analysis only | React/Vite frontend is present. It must not imply that unavailable provider, experiment, or research-report capabilities are operational. Frontend build verification remains for integration QA or any frontend change. |

## Baseline verification at this checkpoint

Commands were run from the repository root on 2026-10-22:

| Command | Result |
|---|---|
| `python -m unittest discover -s backend/tests -v` with `PYTHONPATH=backend` and bytecode disabled | Exit 0; 211 tests passed. |
| `python backend/scripts/validate_dataset.py data/drafts/illustrative_examples.jsonl` | Exit 0; 16 records, 0 errors, 16 warnings that records are unreviewed drafts. |
| `python backend/scripts/check_evaluation_readiness.py data/drafts/illustrative_examples.jsonl` | Exit 1; `NOT READY`, 144 blocking errors, 16 draft warnings. This is expected; the draft dataset was not changed. |
| `python backend/scripts/validate_evaluation_report.py --help` | Exit 0. |
| `git diff --check` | Exit 0. |

## Engineering sequence

The following sequence is proposed from the actual repository state and the supplied continuation prompt:

1. **6E.1 Research readiness audit:** recorded here.
2. **6E.2 Annotation workflow:** provide safe draft validation and eligible-record export without assigning review metadata.
3. **6E.3 Dataset quality safeguards:** close verified gaps in deterministic duplicate, split, group, and provenance diagnostics without rewriting annotations.
4. **Phase 7 Provider adapter:** prepare a backward-compatible isolated adapter and mock-based tests; do not make external calls without explicit authorization.
5. **Phase 8 Verified linguistic assistance:** implement provenance-aware resource infrastructure; production substitutions stay blocked until reviewed resources exist.
6. **Phase 9 Reproducible experiment artifacts:** persist controlled runs only after eligibility and artifact safety requirements are met.
7. **Phase 10 Human ratings:** create an explicit pending-review workflow; never generate ratings.
8. **Phase 11 Research reporting:** report only validated eligible artifacts and avoid unsupported inference.
9. **Phase 12 Frontend completion:** expose only supported backend capabilities.
10. **Phase 13 Integration QA and Phase 14 delivery docs:** perform after the preceding engineering stages.

## Research status

The project has functioning evaluation software but no genuine eligible benchmark, verified linguistic transformation resource, real provider outputs, or human semantic-preservation judgments. Engineering verification is not empirical validation. Any research conclusion remains pending those inputs and the corresponding human review.
