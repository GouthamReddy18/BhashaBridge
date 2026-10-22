# Academic report and presentation outline

This outline separates verified software facts from pending empirical work. It is not a completed research report and contains no project-specific results. Replace every pending section only after the stated evidence exists.

## Written report

1. **Title and authorship** — Use the approved project title and institution-required author/supervisor details.
2. **Abstract** — Pending: research question, eligible sample size, method, observed metric and human-rating results, uncertainty, and conclusion. Do not draft result claims before evaluation.
3. **Introduction** — Motivate Telugu–English code-mixed text and Romanized Telugu. Define semantic preservation and the research question; distinguish motivation from evidence.
4. **Related work** — Summarize primary sources in `references.md` and add verified citations for any further claims. Record versions and access dates for mutable sources.
5. **System and resource inventory** — Describe normalization, tokenization, LID, transliteration, ambiguity fixture, translation adapter, and four condition contracts. Mark each resource as implemented, configured, qualified, or research eligible; these states are not equivalent.
6. **Dataset and annotation** — Pending: legally usable source data, inclusion criteria, human review/adjudication, provenance, references, intended meanings, group/split assignment, and leakage audit. The illustrative draft is not a study dataset.
7. **Methods** — State the cumulative conditions (`direct_v1`, `normalized_v1`, `transliterated_v1`, `ambiguity_aware_v1`), provider/model/configuration, run order, exclusions, failures, missingness, and reproducibility metadata. Explain that blocked conditions have no outputs and are not scored as zero.
8. **Measures** — Report the exact project-versioned BLEU-4 and chrF configurations from `evaluation_protocol.md`. Include per-condition available-output denominators separately from matched-ID paired contrast denominators. Include human semantic ratings only after actual independent review; report coverage and missingness.
9. **Results** — Pending eligible artifacts. Provide counts and denominators before scores, and describe exclusions. No score, rating, significance test, or improvement is currently available.
10. **Discussion and limitations** — Interpret only observed data; discuss metric/reference limits, annotator and provider uncertainty, resource coverage, confounds, and generalizability.
11. **Conclusion** — Pending valid results. If readiness gates remain unmet, present the work as software and methodology infrastructure, not evidence of improvement.
12. **Artifacts and ethics** — Cite the dataset license/provenance, annotation protocol, resource manifests, validated report, code revision, and data-handling approvals when available.

## Presentation outline

1. Research question and why meaning preservation matters.
2. Architecture: analyze endpoint and transparent token-level evidence.
3. Four cumulative conditions and prerequisite gates.
4. Dataset review workflow and why the illustrative draft is ineligible.
5. Metric definitions and separate output/paired denominators.
6. Live demo using only explicitly illustrative inputs; label them on screen.
7. Readiness dashboard: show the actual blockers and empty report catalog.
8. Results slide — leave as **pending** until a valid evaluation artifact and human ratings exist.
9. Limitations, ethics, and the concrete next research steps.

## Demo handling

Use the frontend's built-in examples or other clearly labeled synthetic text. Do not enable translation during a demo unless external transmission is authorized and intended. Do not describe token labels or the English ambiguity fixture as validated linguistic behavior. Do not display test fixture scores as research results.

