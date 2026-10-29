# Phase 27 — Research Resource Discovery, Qualification, and Dataset Acquisition Planning

**Audit date:** 2026-10-27
**Repository checkpoint:** `d3a4f3a` (local `main`, three commits ahead of `origin/main` at `653fb3b`)
**Status:** Research execution remains blocked. This document completes the evidence-backed resource investigation, acquisition decision, annotation protocol review, linguistic-resource qualification, and translation-provider evaluation that Phase 27 required.

---

## 1. Repository and readiness recovery

### Git state on entry

| Item | Value |
|---|---|
| HEAD | `d3a4f3a` — "docs: clarify verification revision" |
| Local `main` | 3 commits ahead of `origin/main` (`653fb3b`) |
| Uncommitted changes | None (`git diff --stat` empty) |
| Untracked | `.vscode/` only (preserved untouched) |
| `git diff --check` | Exit 0 — no whitespace errors |

The three unpushed commits (`c0b1e70`, `477d6ef`, `d3a4f3a`) add the interactive readiness dashboard, frontend/backend wiring, the academic report outline, and a release-readiness document. They are local engineering work that the prior agent completed before the session was interrupted.

### Verification results on entry

| Check | Command | Exit | Outcome |
|---|---|---:|---|
| Full backend test suite | `PYTHONPATH=backend python -m unittest discover -s backend/tests -v` | 0 | **274 tests passed.** |
| Draft structural validation | `python backend/scripts/validate_dataset.py data/drafts/illustrative_examples.jsonl` | 0 | 16 records, 0 errors, 16 unreviewed-draft warnings. |
| Draft evaluation readiness | `python backend/scripts/check_evaluation_readiness.py data/drafts/illustrative_examples.jsonl` | 1 | `NOT READY`; 144 blocking errors, 16 warnings. Expected; draft was not modified. |
| Report validator | `python backend/scripts/validate_evaluation_report.py --help` | 0 | Usage printed. |
| Four-condition evaluator | `python backend/scripts/evaluate_four_condition_experiment.py --help` | 0 | Usage printed. |
| `git diff --check` | `git diff --check` | 0 | No whitespace errors. |

No frontend build was attempted in this phase (engineering verification complete through Phase 26; no source code changed).

### What Phase 27 inherited

Phase 16 closed concrete fixture-scoring gaps. Phase 17 (documented in `dataset-acquisition-and-review.md`) wrote the annotation protocol, dataset review guide, and promotion checklist. Phases 18–26 implemented four-condition infrastructure, the dataset runner, human-rating workflow, research-report composer, frontend, and the readiness dashboard.

**What was missing at interruption:** No document recorded verified external dataset candidates with licenses, limitations, and acquisition recommendations. No language-resource qualification plan existed for transliteration and normalization. No translation-provider comparison table existed beyond the Google Cloud Translation description. This document supplies that missing evidence.

---

## 2. External dataset candidates — evidence-backed investigation

> **Evidence boundary:** All findings below are based on publicly available academic papers, official repository documentation, and dataset-hosting pages. No dataset was downloaded, redistributed, or committed. Evidence labels: **Verified** (confirmed from primary source), **Plausible-unconfirmed** (secondary-source only), **Unresolved** (inconclusive).

---

### 2.1 Candidate A — ICON 2016 POS/LID Shared Task: Telugu–English Code-Mixed Corpus

**Exact name (verified):** "Code Mixed Dataset for Hindi, Bengali and Telugu — ICON 2016 Shared Task" (formally: "Task Report: Tool Contest on POS Tagging for Code-Mixed Indian Social Media Text @ ICON 2016")
**Authors/Organizers:** Anupam Jamatia, Amitava Das; data collected via LTRC IIIT Hyderabad / NLPAI.
**Year:** 2016. ICON 2016, IIT (BHU) Varanasi.
**Authoritative source:** LTRC portal `http://ltrc.iiit.ac.in/icon2016/` (may be archived); indexed in the AI4Bharat IndicNLP Catalog at `https://github.com/AI4Bharat/indicnlp_catalog`.
**Downstream paper (verified):** Gundapu and Mamidi (2018), "Word Level Language Identification in English Telugu Code Mixed Data," PACLIC 32. ACL Anthology ID: Y18-1021. URL: `https://aclanthology.org/Y18-1021/`. CRF model F1=0.91 on this corpus.
**Language pair:** Telugu–English.
**Script:** Mixed — social-media text uses both Romanized (Latin) Telugu and native Telugu script alongside English. Romanized Telugu is a first-class label class.
**Genuinely code-mixed:** Yes — intra-sentential code-switching from Facebook, Twitter, and WhatsApp posts.
**Romanized Telugu:** Yes — primary form of Telugu in social-media data.
**Sentence-level English references:** No. Corpus provides per-token dual annotation: language-identification tags (te/en/ne/univ/mixed) and POS tags. A LID corpus is not a translation benchmark.
**Dataset size (verified via secondary sources citing the task report):**
- Total sentences: **1,979** (Facebook: ~743; Twitter: ~743; WhatsApp: ~493)
- Total tokens: **29,471** (Facebook: 10,037; Twitter: 12,013; WhatsApp: 7,421)
- Telugu/native-script tokens: ~8,813
**Annotation method:** Manual token-level annotation by contest annotators. POS and language-identification labels both present.
**License:** Described as for "non-commercial research and academic use" with attribution required to task organizers. No formal license text confirmed.
**Access:** Email LTRC IIIT Hyderabad (`ltrc@iiit.ac.in`) or check AI4Bharat IndicNLP Catalog. Some preprocessed mirrors exist on GitHub. No stable public direct-download URL found.
**Known limitations:**
- Per-token language labels only; no sentence-level English reference translations.
- BLEU and chrF evaluation requires adding independent human reference translations (full review protocol applies).
- License is academic/non-commercial only; redistribution unconfirmed.
- Access may require direct contact with LTRC IIIT Hyderabad.

**Suitability for the four conditions:** Not directly usable as a translation benchmark. Could provide code-mixed source text if rights are confirmed and independent human reference translations are subsequently added via the full review protocol (Section 4).

---

### 2.2 Candidate B — UD_Telugu_English-TECT (Romanized Code-Mixed Treebank)

**Exact name (verified):** UD_Telugu_English-TECT
**Author:** Anishka Vissamsetty
**Year:** UD v2.14 (2024)
**Language code:** `qte`
**Authoritative source:** Universal Dependencies. Official page: `https://universaldependencies.org/treebanks/qte_tect/`. GitHub: `https://github.com/UniversalDependencies/UD_Telugu_English-TECT`.
**Language pair:** Telugu–English code-mixed.
**Script:** All text in Latin (Roman) script — this is a Romanized Telugu–English code-switched treebank.
**Genuinely code-mixed:** Yes — every sentence contains at least one code-switch between Telugu and English. Per-token language tags (te/en/univ) are present in the MISC column.
**Romanized Telugu:** Yes — explicit design requirement; all text uses Latin script.
**Data sources used:** (1) UD Telugu treebank (Rama and Vajjala, 2021); (2) grammar book sentences; (3) MASSIVE dataset (FitzGerald et al., 2022).
**Sentence-level English references:** Unresolved. Not confirmed in sources. Some sentences may derive from MASSIVE (which has English originals), but the treebank itself is not structured as a parallel corpus with usable evaluation references.
**Dataset size (verified):**
- Total sentences: **97** (Train: 61; Test: 36)
- Total tokens: **456** (Train: 290; Test: 166)
**Annotation method:** Universal Dependencies syntactic annotation (POS, dependency relations) plus per-token language identification.
**License:** CC BY-SA 4.0 (verified). Attribution required; derivative works must use the same license.
**Access:** Freely downloadable from GitHub and UD release archives. No registration required.
**Known limitations:**
- Very small: 97 sentences, 456 tokens. Too small for a statistically informative evaluation.
- Does not include sentence-level English reference translations; annotation is syntactic, not parallel.
- CC BY-SA 4.0 ShareAlike applies to derivative works.
- Source sentences from grammar-book and spoken examples may not represent typical social-media code-mixed text.

> **Note on UD_Telugu-MTG:** This is a separate, monolingual Telugu treebank in **native script** (tel_Telu), not Romanized, not code-mixed. 1,328 sentences, 6,465 tokens. CC BY-SA 4.0. It is the source for some UD_Telugu_English-TECT sentences but is not itself a code-mixed resource.

**Suitability for the four conditions:** Provides Romanized Telugu–English code-mixed source text with verified CC BY-SA 4.0 licensing. Too small for a powered evaluation. Could serve as development or qualitative analysis examples after independent human reference translations are added via the full review protocol (Section 4).

---

### 2.3 Candidate C — AI4Bharat IndicCMix (Synthetically Generated Code-Mixed Corpus)

**Exact name (verified):** IndicCMix
**Organization:** AI4Bharat
**Year:** 2025 (approximate)
**Authoritative source:** HuggingFace: `https://huggingface.co/datasets/ai4bharat/IndicCMix`.
**Language pair:** Telugu–English (one of 11 Indic languages covered).
**Script:** Multiple columns — native Telugu script, Romanized/WhatsApp-style, and code-mixed variants are all represented.
**Genuinely code-mixed:** Yes — structured as synthetic code-mixing where English content words are embedded into Telugu matrix structure.
**Romanized Telugu:** Yes — one column is explicitly a Romanized (WhatsApp-style) variant.
**Sentence-level English references:** Yes — each entry has an English source sentence. The corpus is structured as parallel: English → code-mixed Telugu variants. This distinguishes it from the LID corpora above.
**Dataset size (verified):**
- Total rows across all languages: ~1,152,750
- Telugu (`te`) rows: ~104,796 sentences
**Annotation method:** Algorithmic/rule-based synthetic generation; not human-reviewed at the sentence level.
**License:** MIT License (verified in the HuggingFace dataset card).
**Access:** Gated on HuggingFace — requires agreeing to share HuggingFace profile; no fee.
**Generation methodology:** Rule-based plus translation-based. Whether Matrix Language Frame (MLF) theory was used as the syntactic constraint is **unresolved**; the public dataset card does not specify.

> **GCM Toolkit (related):** Rizvi et al. (2021), "GCM: A Toolkit for Generating Synthetic Code-Mixed Text," EACL 2021 System Demonstrations. ACL Anthology ID: 2021.eacl-demos.24. URL: `https://aclanthology.org/2021.eacl-demos.24/`. GitHub: `https://github.com/microsoft/CodeMixed-Text-Generator`. MIT license. This is an MLF-grounded generation tool, not a pre-built corpus. It requires a Telugu–English parallel corpus as input to produce a synthetic corpus.

**Known limitations:**
- Synthetically generated — not naturally occurring code-mixed text.
- No human review of individual sentences.
- **Synthetic records are explicitly excluded from research scoring** by the BhashaBridge evaluator and readiness checker.
- The generation method may not replicate natural code-switching constraints.
- English source sentences may not represent code-mixed social-media usage.

**Suitability for the four conditions:** Not suitable as a held-out benchmark (synthetic records excluded from scoring by the evaluation protocol). Could serve as a resource for developing and testing normalization and transliteration rules on a training portion — subject to the MIT license and the strict condition that no test-set reference translations are seen during development.

---

### 2.4 Additional verified candidates

| Corpus | Authors / Org | Year | Size | Romanized Te | Code-mixed | En Reference | License | Access |
|---|---|---|---|---|---|---|---|---|
| ICON 2016 POS/LID (Candidate A) | Jamatia, Das / LTRC | 2016 | 1,979 sents / 29,471 tokens | Yes | Yes | **No** | Academic non-commercial | Request LTRC |
| UD_Telugu_English-TECT (Candidate B) | Vissamsetty | 2024 | 97 sents / 456 tokens | Yes | Yes | Unresolved | CC BY-SA 4.0 | GitHub (free) |
| AI4Bharat IndicCMix (Candidate C) | AI4Bharat | 2025 | ~104,796 Te rows | Yes | Yes (synthetic) | **Yes** | MIT | HuggingFace (gated) |
| CMTET Sentiment | Kusampudi et al. / IIIT-H | 2021 | Unconfirmed | Yes | Yes | No | Academic | GitHub / request |
| Telugu–English NER | Srirangam et al. | 2019 | ~13,909 NE tokens | Yes | Yes | No | Academic | ACL Anthology + request |
| IndicTalk | LingoIITGN / IIT Gandhinagar | Recent | ~147,076 Te conversations | Yes | Yes | Unresolved | CC BY 4.0 | HuggingFace |
| UD_Telugu-MTG | Rama, Vajjala | 2021 | 1,328 sents | **No** (native script) | **No** | No | CC BY-SA 4.0 | GitHub (free) |

**CMTET (ACL Anthology ID: 2021.ranlp-1.86):** Telugu–English code-mixed social media text with sentiment labels and word-level language tags. No sentence-level English references. Access: GitHub or contact IIIT-H authors. Not a translation corpus.

**Telugu–English NER (ACL Anthology ID: P19-2025):** First annotated Telugu–English code-mixed Twitter corpus for named entity recognition. Verified NE token counts: B-Loc 5,429; B-Per 4,888; B-Org 2,257. No sentence-level English references. Not a translation corpus.

**IndicTalk (HuggingFace: `LingoIITGN/IndicTalk`):** ~102,069 native-script + ~45,007 Romanized Telugu conversational instances. CC BY 4.0. Whether parallel English references are available for each entry is unresolved.

**Not found / clarified:**
- **GLUECoS** covers Hindi–English and Spanish–English only. No Telugu.
- **CALCS workshops** (2014–2023) cover Spanish–English and Hindi–English. No Telugu.
- **FIRE Dravidian-CodeMix** tasks covered Tamil–English and Malayalam–English. No Telugu track confirmed.
- **Molina et al. 2016** covers Spanish–English and MSA–Arabic only. Not applicable.
- **Vyas et al. 2014** covers Hindi–English (Hinglish) only. Not applicable.

**Summary:** No publicly available, freely licensed Telugu–English code-mixed corpus with sentence-level **human-reviewed** English reference translations was identified. This is a genuine gap. IndicCMix (MIT) provides English source sentences but is synthetically generated; UD_Telugu_English-TECT (CC BY-SA 4.0) provides Romanized code-mixed text but is tiny (97 sentences) and lacks reference translations; ICON 2016 is the largest verified corpus but has unresolved licensing and no references.

---

## 3. Acquisition decision

### 3.1 Comparison of three strategies

| Strategy | Scientific defensibility | Licensing risk | Annotation effort | Leakage risk | Timeline |
|---|---|---|---|---|---|
| **A. Public dataset** | Low: no confirmed public corpus has sentence-level English references for BLEU/chrF. LID corpora require additional annotation. | Unresolved for most candidates | Low for existing labels; high for adding references | High: test references must not contaminate development | Blocked until a suitable corpus is identified and licensed |
| **B. Original human-reviewed dataset** | Highest: full provenance, consent, and license control | Minimal: original creation | Very high: collection, annotation, review, adjudication | Controlled if done correctly | Months of work; not feasible within a semester |
| **C. Hybrid: dev from available sources + original test set** | Moderate: test set provenance is clean; development data provenance must be documented | Mixed: development data may have unclear rights; test set is original | Moderate: full review effort on test set only | Controlled if test references never used in development | Most practical for a semester project |

### 3.2 Recommendation

**For a second-year undergraduate project: Strategy C — Hybrid.**

**Rationale:**

1. **No suitable public dataset exists for direct evaluation.** No confirmed public Telugu–English code-mixed corpus with sentence-level English reference translations under a permissive license was found. Strategy A is blocked.

2. **A pure original dataset (Strategy B) is not feasible within a semester.** Collecting, annotating, reviewing, and adjudicating a sufficiently sized corpus with the inter-annotator agreement and provenance controls the evaluation protocol requires is not realistic for a small project team.

3. **A small hybrid approach is scientifically defensible.** The test set must be:
   - **Original examples** composed by the project team or consented contributors, clearly labeled as project-authored.
   - **Human-reviewed** by a qualified reviewer independent of the system developers.
   - **Small but carefully annotated:** even 20–30 reviewed examples support qualitative analysis and demonstrate the methodology. Statistically powered effect estimation is not claimed.
   - **Strictly separate** from normalization rule development, transliteration resource development, and any system prompt tuning.

4. **Development data:** Available sources (IndicCMix training portion, UD_Telugu_English-TECT training split, or project-composed examples) can be used for developing normalization and transliteration rules — but must not enter the test set and must not carry reference translations seen by developers.

**Scientific, licensing, annotation, time, and leakage implications:**
- **Scientific:** Claims must be scoped: "in this small sample of N reviewed examples…". No population-level generalization, significance test, or causal-improvement claim is warranted.
- **Licensing:** Project-authored examples are the clearest provenance case. Any adapted published text requires the source license to permit derivative annotation works.
- **Annotation:** All test examples require independent reference translation and intended-meaning annotation by a reviewer who has not seen system outputs. See Section 4.
- **Time:** A realistic scope is 20–40 carefully reviewed test examples — sufficient to demonstrate the workflow, not a powered study.
- **Leakage:** References must be prepared before any condition runs. Test examples must not be used to develop normalization, transliteration, or disambiguation resources.

**If no hybrid strategy is feasible:** Present the work as software and methodology infrastructure, not an empirical research finding. This is honest and academically acceptable.

---

## 4. Annotation protocol (complete)

The [Dataset Acquisition and Review Guide](dataset-acquisition-and-review.md) documents the full workflow. This section provides concrete operational guidance.

### 4.1 Example drafting

1. **Source:** Compose short code-mixed utterances (2–15 tokens) containing at least one TELUGU_ROMANIZED and one ENGLISH token. Represent realistic usage: casual social-media sentences, conversational statements, simple requests. Avoid examples designed to favor any one condition.
2. **Record exactly:** Preserve the source utterance byte-for-byte in `text`. Compute `normalized_text` as `" ".join(text.split())`. Use the backend tokenizer for token boundaries and Python Unicode code-point offsets.
3. **Assign a stable ID:** Use a systematic prefix such as `pilot-test-001`, `pilot-test-002`, etc. No personal identifiers.
4. **Record provenance:** Mark `source_type` as `project_authored`, `user_contributed` (with consent), or `adapted_published` (with source documented). Record the collection method in `annotation_provenance.details`.

### 4.2 Reference translation and intended meaning

1. **Assign a reviewer** who has not been involved in system development, normalization rule writing, or transliteration resource development. Ideally a Telugu–English bilingual person unaffiliated with system development.
2. **Prepare the reference before running any condition.** The reviewer reads the source utterance and writes an English translation that captures the intended meaning, without seeing any system output.
3. **Record `reference_translation` and `intended_meaning`** with `field_review_status: reviewed`, `reviewer_id`, `review_date`, and `source_reference` pointing to an entry in the offline annotation log.
4. **No machine suggestions as references.** A machine-translated string is not a reference translation. It may be used as a draft aid only if a human subsequently reviews, corrects, and approves it — and provenance must record this origin.
5. **Disagreements:** Record both alternatives and the adjudicator's decision. If unresolvable, mark `disputed` and exclude from evaluation.

### 4.3 Review and approval

Each draft must pass the full checklist in the [Dataset Acquisition and Review Guide](dataset-acquisition-and-review.md#7-repeatable-validation-and-promotion-checklist). Key checks:
- Source text exact and unmodified.
- `normalized_text` matches `" ".join(text.split())`.
- Token boundaries and offsets match the backend tokenizer.
- Language labels are evidence-based and independently defensible.
- Reference translation and intended meaning are independent of system outputs.
- Reviewer metadata is actual, not fabricated.

### 4.4 Split and group assignment

1. Assign all examples to a `split_group` before assigning splits. Related examples share one group.
2. Assign the entire group to one split (train, validation, or test). No group spans partitions.
3. The test split must contain all evaluation examples. Resources must be developed on training/validation examples only.
4. Record the split assignment algorithm (deterministic method, seed) outside the JSONL file.

### 4.5 Promotion checklist

```powershell
python backend/scripts/validate_dataset.py path/to/candidate.jsonl
python backend/scripts/check_evaluation_readiness.py path/to/candidate.jsonl
python backend/scripts/annotation_workflow.py check-readiness path/to/candidate.jsonl
```
All three must exit 0. Inspect every diagnostic before promoting.

### 4.6 Exclusion log

Maintain an offline exclusion log recording: record ID, exclusion reason (source rights unresolved; reference missing; annotation conflict; leakage detected; etc.), reviewer/adjudicator reference, and affected evaluation populations.

### 4.7 Do not
- Mark synthetic records as reviewed.
- Fabricate annotators, review dates, or provenance.
- Use system outputs as reference translations.
- Use test-set references during rule or resource development.
- Place unreviewed drafts in benchmark splits.

---

## 5. Linguistic-resource qualification

### 5.1 Current implementation status

| Resource | Type | Status |
|---|---|---|
| Whitespace normalization (`" ".join(text.split())`) | Implemented behavior | Implemented and tested. Formatting normalization only; not linguistic normalization of code-mixed text. |
| Token-level LID (heuristics) | Implemented behavior | Implemented: Unicode category rules, Telugu block detection, small seed lists. Accuracy on real code-mixed text unvalidated. |
| IndicLID (optional FastText adapter) | External resource — not configured | MIT license claimed by source repository. Token-level use is an unvalidated adaptation of a sentence-level model. No weights bundled or downloaded. See `docs/references.md`. |
| Selective transliteration engine | Protocol seam — no engine configured | Service interface implemented in `transliteration.py`. No engine configured, bundled, or downloaded. Quality unvalidated. |
| Linguistic resource manifest (normalization/contextual rules) | Schema and validator implemented — no reviewed resource | `validate_linguistic_resource.py` validates a manifest JSON. No reviewed Telugu–English rule resource is bundled. The only rule is the illustrative English `bank` fixture (test-only). |
| Contextual ambiguity resolution | Illustrative fixture only | The `bank` fixture tests the mechanism; it is not a validated Telugu–English disambiguation rule. No reviewed resource. |

### 5.2 Pilot qualification procedure

Before using any linguistic resource in an evaluated condition, complete this procedure:

**Step 1 — Document the resource:** Name, version, authors, source URL, access date, license, language/script coverage, annotation method.

**Step 2 — Define coverage:** Which token types, scripts, and language labels the resource handles; known gaps (short Romanized words, named entities, neologisms).

**Step 3 — Preservation tests (offline, not on test data):** Run the resource on a development set containing: named entities (verify no incorrect normalization/transliteration), spelling variants (verify consistent handling), ambiguous expressions (verify abstention when evidence insufficient), English tokens (verify no incorrect modification), and edge cases. Record input, expected output, actual output, acceptability, and failures.

**Step 4 — Meaning preservation check (human-reviewed):** For each rule that modifies token text, a Telugu–English bilingual reviewer confirms: the substitution preserves meaning in code-mixed context; does not alter named entities; is appropriate for the intended-meaning dimension.

**Step 5 — Abstention verification:** Confirm the resource abstains rather than guessing when evidence is insufficient. The existing `match_rule` function in `linguistic_resources.py` is fail-closed and abstains unless `applicable=True` and `entity_preserved=True` are explicitly supplied by the caller.

**Step 6 — Declare in a manifest:** Create a `LinguisticResourceManifest` JSON with `review_status: reviewed` for each rule only after Steps 3–5 are complete. Validate with:
```powershell
python backend/scripts/validate_linguistic_resource.py path/to/manifest.json
```
The manifest declares review; it does not authenticate the reviewer.

**Step 7 — Keep test data separate:** All development and qualification must use only training or development examples. Test-set examples and references must not be used in any resource development step.

### 5.3 IndicXlit (AI4Bharat) as a transliteration candidate

**Name:** IndicXlit
**Source:** AI4Bharat, `https://github.com/AI4Bharat/IndicXlit`
**Claimed coverage:** Romanized → native-script transliteration for 21 Indian languages including Telugu.
**License:** MIT (claimed in repository; verify before use).
**Known limitations:**
- Processes word-level inputs; not sentence-level or mixed-script.
- Evaluated on standard romanization patterns; code-mixed social-media spelling variations are an unvalidated use case.
- Requires downloading model weights (not bundled); no automatic download in BhashaBridge.
- A wrapper could be supplied to the `TransliterationEngine` seam in `transliteration.py`, but must be validated per Steps 3–5 before research use.
**Status:** Unverified for this project's use case. Requires qualification per Section 5.2 before being eligible for any evaluated condition.

### 5.4 Actions requiring authorization before proceeding

The following require explicit authorization from the project supervisor or user:
- Downloading IndicXlit model weights or any other model weights.
- Installing additional Python packages beyond `backend/requirements.txt`.
- Sending project text to any external API for normalization or transliteration.

---

## 6. Translation-provider qualification

### 6.1 Implemented provider

**Provider:** Google Cloud Translation Basic v2
**Provider ID in system:** `google.cloud.translation.basic.v2`
**Implementation:** `backend/app/services/google_translation.py`
**Status:** Adapter implemented; disabled and unconfigured. No API key configured. No real call made.

**Provider behavior as implemented:**
- POST to `https://translation.googleapis.com/language/translate/v2`; requests `target: en`, `model: nmt`, `format: text`.
- Bounded timeout (default 10 s; configurable up to 120 s).
- Safe failure categories: `provider_auth_error`, `provider_quota_error`, `provider_timeout`, `provider_request_error`, `provider_error`, `provider_response_error`.
- Records `confirmed_model` from API response when present.
- No retry logic. No credential logging.

### 6.2 Provider comparison

| Option | Language support | Code-mixed handling | Terms / privacy | Reproducibility | Cost | Provider ID |
|---|---|---|---|---|---|---|
| **Google Cloud Translation Basic v2** | Telugu supported; Romanized code-mixed quality unestablished | Unknown; not documented | Google Cloud ToS; data may be used by Google; no self-hosting | Provider-side nondeterminism; model version not guaranteed | Pay-per-use; free tier available | `google.cloud.translation.basic.v2` — registered |
| Google Cloud Translation Advanced (v3) | Same as Basic | Same as Basic | Same; supports glossaries | Better version control | Higher cost | Not implemented |
| DeepL API | Telugu: **not supported** as of 2024 | N/A | DeepL API Terms | Provider-side nondeterminism | Pay-per-use | Not implemented |
| Azure Translator | Telugu supported | Unknown for code-mixed | Microsoft Terms | Provider-side nondeterminism | Pay-per-use | Not implemented |
| Local model (e.g., Helsinki-NLP OPUS-MT tel→en) | tel→en models exist; code-mixed quality unestablished | No special code-mixed support | Typically MIT/CC; self-hosted | Fully reproducible; version locked | Infrastructure only; no per-query cost | Not implemented |
| No provider (current state) | N/A | N/A | N/A | Fully deterministic | Zero | Current state |

**Recommendation:** Google Cloud Translation Basic v2 (already implemented) is the most practical option given the project's state. Before enabling:

1. **Romanized Telugu code-mixed quality is unestablished.** The provider may treat Romanized Telugu as English, transliterate before translating, or fail silently. This is unknown without a pilot.
2. **Data transmission requires authorization.** Sending project text to Google requires explicit consent and compliance with applicable data-protection regulations. **This action requires the project supervisor's or user's explicit authorization.**
3. **Charges are usage-based.** Any API calls or billing decisions require the user's explicit authorization.
4. **Provider nondeterminism.** The Basic API does not guarantee a fixed model version or deterministic output.

**Actions requiring authorization (translation provider):**
- Enable `BHASHABRIDGE_GOOGLE_TRANSLATE_ENABLED=true`
- Configure `BHASHABRIDGE_GOOGLE_TRANSLATE_API_KEY`
- Make any real API call that sends project text to Google
- Incur any API charges

No translation API call was made in this phase.

---

## 7. Four-condition experimental validity review

### 7.1 Conditions and current eligibility

| Condition | Contract | Resource required | Current status |
|---|---|---|---|
| `direct_v1` | Exact original source text sent to provider | None (beyond provider) | Blocked: no provider configured; no eligible dataset. |
| `normalized_v1` | Cumulative: whitespace normalization + reviewed linguistic normalization | Reviewed normalization resource | Blocked: no qualified resource. Whitespace collapse does not satisfy this condition. |
| `transliterated_v1` | Cumulative: `normalized_v1` + reviewed selective transliteration of TELUGU_ROMANIZED tokens | Reviewed transliteration engine/resource | Blocked: no qualified resource, and `normalized_v1` is blocked. |
| `ambiguity_aware_v1` | Cumulative: `transliterated_v1` + reviewed contextual transformation for eligible tokens | Reviewed contextual rule resource | Blocked: no eligible resources; all prerequisite conditions are blocked. |

### 7.2 Scientific safeguards verified as implemented

- **Ineligible outputs excluded:** The evaluator unconditionally excludes mock, fixture, test-only, invalid, failed, unavailable, disabled, and missing outputs from metric scoring. Verified in Phase 16 (`four_condition_evaluation.py`).
- **Provider identity check:** Only the registered Google adapter ID is accepted as scorable. Unknown/fake providers cannot enter scoring or human-rating task generation.
- **Separate denominators:** Each condition's available-output population and each pairwise comparison's matched-ID population are reported separately. A missing output is never imputed as zero.
- **BLEU and chrF are proxies:** The evaluation protocol explicitly states that BLEU-4 and chrF measure reference-based surface overlap and **do not independently prove semantic equivalence.** Human semantic ratings are a separate required outcome.
- **No eligibility weakening:** Readiness checks have not been relaxed. The 144 blocking errors for the 16-record draft are expected and have not been modified.

### 7.3 Scientific weaknesses requiring disclosure

1. **Reference quality is unvalidated.** Once references exist, their quality has not been established through inter-annotator agreement.
2. **BLEU and chrF are not semantic measures.** A fluent but semantically incorrect output can outscore an awkward but correct one.
3. **Small sample size.** A pilot of 20–30 examples produces unstable corpus-level BLEU/chrF estimates. No power calculation has been performed.
4. **Provider nondeterminism.** The Basic API does not guarantee fixed output across runs.
5. **Single provider.** Results from one provider cannot be generalized.
6. **Human rating instrument is unvalidated.** The 0–4 rubric has not been piloted; inter-rater agreement has not been measured.
7. **Romanized Telugu code-mixed quality is unknown.** The provider's handling of Romanized Telugu–English input is undocumented.

---

## 8. Staged roadmap with prerequisites and exit criteria

### Stage 1 — Data collection and review (prerequisite for everything)

**Prerequisites:** Team availability.
**Actions:** (1) Compose 20–40 code-mixed utterances. (2) Assign stable IDs and document provenance. (3) Have a bilingual reviewer independently write reference translations and intended meanings before any condition runs. (4) Run the promotion checklist. (5) Assign leakage-safe group and split metadata.
**Exit criteria:** At least 20 records pass structural validation and readiness checks with reviewed references; test references not seen by developers; splits frozen.

### Stage 2 — Normalization and transliteration resource qualification

**Prerequisites:** Stage 1 training/validation examples only.
**Actions:** (1) Document a candidate normalization approach. (2) If IndicXlit is chosen: verify license, download weights with authorization, run qualification procedure on development examples only. (3) Create and validate a `LinguisticResourceManifest`.
**Exit criteria:** Each resource to be used has a validated manifest with `review_status: reviewed`. Resource validator exits 0. No test-set examples used.

### Stage 3 — Provider setup and pilot

**Prerequisites:** User authorization; Google Cloud account and API key.
**Actions:** (1) Obtain explicit supervisor authorization. (2) Configure environment variables. (3) Run a small pilot (5–10 development examples). (4) Document pilot results, model metadata, failure modes.
**Exit criteria:** Provider returns non-empty responses for code-mixed input; failure behavior documented; authorization on record.

### Stage 4 — Experiment execution

**Prerequisites:** Stages 1–3 complete; test set not seen by developers.
**Actions:** Run `run_four_condition_experiment.py`, `evaluate_four_condition_experiment.py`, `validate_four_condition_report.py` on the test split.
**Exit criteria:** Runner exits 0; report validates; per-condition outcome counts and denominators documented.

### Stage 5 — Human semantic ratings

**Prerequisites:** Stage 4 outputs; independent raters.
**Actions:** Create blinded tasks with `human_rating_workflow.py create-tasks`; collect at least two independent 0–4 ratings per output; report inter-rater agreement (Krippendorff's α or Cohen's κ) before aggregating.
**Exit criteria:** At least two independent ratings per output; agreement reported; no ratings derived from BLEU/chrF.

### Stage 6 — Research report

**Prerequisites:** Stages 1–5 complete.
**Actions:** Compose with `build_research_report.py`; report descriptive results; disclose all limitations from Section 7.3.

---

## 9. Remaining blockers

### Data
- No reviewed dataset. Stage 1 has not been executed. **Critical blocker for all evaluation.**
- No rights-cleared external corpus for the stated evaluation population has been identified.

### Licensing
- ICON 2016 dataset: license status unresolved. Cannot be committed or redistributed without confirmed rights.
- Any adapted published text: source license must permit derivative annotation works.

### Annotation
- No reviewed reference translations or intended meanings.
- No qualified annotator or reviewer has been identified.
- No adjudication process has been executed.

### Linguistic resources
- No reviewed normalization resource beyond whitespace collapse.
- No qualified transliteration engine configured or validated.
- No reviewed contextual disambiguation rules for Telugu–English.
- IndicXlit download and qualification require authorization and human review.

### Provider setup
- Google Cloud Translation disabled and unconfigured.
- No API key configured.
- No production API calls made.
- Enabling the provider requires explicit authorization.

### Human evaluation
- No semantic ratings.
- No rater pool identified.
- The 0–4 rating rubric has not been piloted.

### Engineering
- No current defects. 274 tests pass. `git diff --check` exits 0.
- Browser/device visual QA not available in this environment; remains outstanding.

---

## 10. Recommended next action

**Compose a small set of original Telugu–English code-mixed examples and begin the annotation and review workflow.**

This unblocks all other research gates:
1. Write 20–30 short Telugu–English code-mixed utterances covering Romanized Telugu tokens, code-switching points, and ambiguity contexts.
2. Have a bilingual Telugu–English reviewer (independent of system development) write English reference translations and intended meanings before any condition is run.
3. Run the structural validator and readiness checker; address all blocking errors.
4. Assign stable group IDs and frozen split assignments.

Normalization qualification, transliteration qualification, provider setup, experiment execution, human ratings, and reporting are all blocked until Stage 1 is complete.

---

## Files changed in Phase 27

| File | Change | Reason |
|---|---|---|
| `docs/phase27-resource-audit.md` | **[NEW]** This document | Completes the evidence-backed resource investigation, acquisition decision, annotation protocol, linguistic-resource qualification plan, translation-provider comparison, experimental-validity review, and roadmap that Phase 27 required. |
| `docs/project_status.md` | Updated — Phase 27 checkpoint added at top | Records Phase 27 verification results, research summary, and recommended next action. |

No source code, test files, draft data, schema files, or `.vscode/` were modified. No commits were staged or made. No external data was downloaded or transmitted.
