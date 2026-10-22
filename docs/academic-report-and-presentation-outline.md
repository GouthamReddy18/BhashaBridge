# Academic report and presentation outline

This outline separates verified software facts from pending empirical work. It is not a completed research report and contains no project-specific results. Replace every pending section only after the stated evidence exists.

## Written report

1. **Title and authorship** — Use the approved project title and institution-required author/supervisor details.
2. **Abstract** — Pending: research question, eligible sample size, method, observed metric and human-rating results, uncertainty, and conclusion. Do not draft result claims before evaluation.
3. **Introduction and motivation** — Motivate Telugu–English code-mixed text and Romanized Telugu. Define semantic preservation and separate motivation from evidence.
4. **Research problem and objectives** — State the controlled question and objectives: compare direct translation with the cumulative approved interventions, measure reference similarity, and separately assess preservation of intended meaning.
5. **Related work and cited sources** — Summarize primary sources listed in [`references.md`](references.md), including the cited IndicLID paper, and add verified sources before making further literature claims. Record versions and access dates for mutable sources.
6. **Proposed methodology** — Define population, eligibility, annotation, controls, outcomes, exclusions, missingness, and analysis boundaries before inspecting results.
7. **System architecture** — Describe the analysis API, four-condition contracts, resource gates, provider adapter, evaluator, report validator, and human-rating workflow. Distinguish implemented software from configured or qualified resources.
8. **Dataset and annotation procedure** — Pending: legally usable source data, inclusion criteria, human review/adjudication, provenance, references, intended meanings, group/split assignment, and leakage audit. The illustrative draft is not a study dataset.
9. **Linguistic resource design** — Describe resource manifest format, provenance/evidence requirements, coverage, applicability, entity-preservation review, qualification process, and actual resource status. Do not treat the illustrative ambiguity fixture or whitespace collapsing as a qualified resource.
10. **Experimental design** — State the cumulative conditions (`direct_v1`, `normalized_v1`, `transliterated_v1`, `ambiguity_aware_v1`), provider/model/configuration, run order, failure handling, and reproducibility metadata. Blocked conditions have no output and are not scored as zero.
11. **Evaluation metrics** — Report exact project-versioned BLEU-4 and chrF configurations from `evaluation_protocol.md`. Separate per-condition available-output denominators from matched-ID paired contrast denominators. Add human semantic ratings only after actual independent review, with coverage and missingness.
12. **Results** — Pending eligible artifacts. Provide counts and denominators before scores and describe exclusions. No score, rating, significance test, or improvement is currently available.
13. **Error analysis** — Pending genuine outputs and reviewed labels. Plan qualitative analysis by language/script pattern, resource application, provider failure, and semantic-preservation error, while protecting source data.
14. **Limitations and threats to validity** — Interpret only observed data; discuss metric/reference limits, annotator and provider uncertainty, resource coverage, confounds, and generalizability.
15. **Conclusion and future work** — Pending valid results. If readiness gates remain unmet, present the work as software and methodology infrastructure, not evidence of improvement.
16. **Reproducibility details** — Record code revision, environment/dependency versions, dataset and resource versions/hashes, provider/model settings, exact inputs, command lines, report schema/metric versions, and authorization/ethics decisions when available.

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

