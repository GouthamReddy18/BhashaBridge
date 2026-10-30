# BhashaBridge 2.0 — Reviewer Handoff Package (Version 1.0)

**Date prepared:** 2026-10-28
**Dataset version:** pilot_v0.1 (28 draft examples)
**For:** Independent bilingual Telugu–English reviewer

---

## 1. What you are being asked to do

You are an independent reviewer for a research project that studies whether explicit linguistic processing steps can improve the quality of English translations of **Telugu–English mixed-language text**.

Your task is to review each example in the draft dataset and provide:

1. Your assessment of the **intended meaning** of each source utterance in its natural context.
2. An **English reference translation** that accurately conveys that meaning.
3. Corrections to any **draft language labels** that you judge to be wrong.
4. Notes on any **ambiguity**, uncertainty, or examples you think should be excluded.
5. Notes on any words, phrases, or expressions that **must be preserved** (named entities, culturally specific terms).
6. Whether proposed **normalizations** (spelling standardization) would preserve the intended meaning.

> **What you are NOT being asked to do:** You are not being asked to improve the grammar, make the text more formal, or produce a polished English translation. You are being asked to faithfully record what the speaker intended to say.

---

## 2. About the project

The research question is: **Does processing Romanized Telugu–English code-mixed text (normalizing spelling, converting Telugu words to Telugu script, resolving ambiguous words) before translation improve the quality and meaning-fidelity of the English translation?**

The project has four experimental conditions:
- **direct_v1**: translate the original input directly.
- **normalized_v1**: normalize spelling first, then translate.
- **transliterated_v1**: normalize and convert Romanized Telugu to Telugu script, then translate.
- **ambiguity_aware_v1**: additionally resolve context-dependent word meanings, then translate.

Your independently reviewed reference translation will be used to judge how well each condition preserves the original intended meaning.

---

## 3. What is Telugu–English code-mixing?

Code-mixed text combines two languages in the same sentence or phrase. In this dataset, speakers write **Telugu using Roman (Latin) script** — this is called "Romanized Telugu" — mixed with English words and phrases.

**Examples of phenomena you will encounter:**

| Utterance | What's happening |
|---|---|
| `nenu office ki veltunna` | Telugu sentence in Roman script with English word 'office' |
| `project deadline extend cheyyadam possible aa?` | English technical terms with Telugu grammatical frame |
| `smart ga matladutaadu` | English adjective 'smart' + Telugu suffix 'ga' (= 'speaks smartly') |
| `forgottu ayyindi` | English 'forgot' with Telugu vowel added, + Telugu auxiliary |
| `link pampu` | English noun 'link' + Telugu imperative 'pampu' (= 'send the link') |

**Important:** The text is not "broken English" or "bad writing." It is a natural style of informal written communication. Your translation should treat it as a meaningful utterance.

---

## 4. How to read informal Romanized Telugu

There is no single official spelling for Romanized Telugu. Common conventions you will encounter:

| Feature | Example | What it means |
|---|---|---|
| `aa` (long a) | `meeru`, `unnaaru` | Common in Telugu transliteration |
| `ki` | `college ki` | Postposition: 'to' or 'for' |
| `lo` | `canteen lo` | Postposition: 'in' or 'at' |
| `ga` | `happy ga` | Postposition: 'in a way that is' (adverbializer) |
| `cheyyi` / `cheyyadam` | `call cheyyi` | Telugu verb 'to do'; forms imperatives and infinitives |
| `ledu` / `ledhu` | `time ledu` | Negation: 'there isn't' / 'I don't' |
| `undi` / `undi` | `battery lo undi` | Copula: 'is' / 'there is' |
| `ayyindi` | `confirm ayyindi` | Past tense auxiliary: 'it happened' / 'it occurred' |
| `nenu` | — | First person singular: 'I' |
| `meeru` | — | Second person formal: 'you' |
| `vaadu` | — | Third person masculine: 'he' |

If a word is unfamiliar, you may look it up using a Telugu dictionary or your own bilingual knowledge. Record where you consulted a source if you did.

---

## 5. How to record the intended meaning

The **intended meaning** is a short English description of what the speaker meant to communicate — not a word-for-word gloss, but the actual communicative content.

- Include all key propositions (who did what, when, to whom).
- Include negation accurately. If the utterance means "I have not watched this movie," the intended meaning must say so.
- Do not add information that is not in the utterance.
- If the utterance is ambiguous and you genuinely cannot determine the meaning from context, say so and record both possible meanings.
- If you think the utterance is uninterpretable, recommend excluding it.

**Example (for illustration only — not a real record):**

> Source: `nenu office ki veltunna`
> Intended meaning: "The speaker is going to the office."

---

## 6. How to produce the English reference translation

The **reference translation** is the English equivalent of the source utterance, written as a natural English sentence.

**Rules:**

1. **Translate the intended meaning**, not each word.
2. **Preserve named entities**: App names (`WhatsApp`), brand names, company names, and place names should appear in English as-is. Do not translate them.
3. **Preserve kin terms**: `akka` (older sister) should be translated as "sister" or kept as "akka" if there is no natural English equivalent. Do not turn it into a personal name.
4. **Preserve negation**: If the source says "I have not done X," the translation must also say "I have not done X."
5. **Preserve communicative intent**: A question should be translated as a question. A command should be translated as a command.
6. **Do not make the text more formal** than the speaker intended. If it is casual, the translation can be casual.
7. **Do not use the project's system outputs** as the basis for your translation. Write your translation before seeing any system output.
8. If you are uncertain about a translation choice, write your best attempt and add a note explaining the uncertainty.

**Do not use machine translation as your reference.** If you use a machine translation as a starting point, you must revise it based on your own bilingual knowledge and record that you did so.

---

## 7. How to review language labels

Each token (word or punctuation mark) in the draft has been labeled with a language category. The labels are:

| Label | Meaning |
|---|---|
| `TELUGU_ROMANIZED` | A Telugu word written in Roman script |
| `TELUGU_SCRIPT` | A Telugu word written in Telugu script |
| `ENGLISH` | An English word |
| `NUMBER` | A numeric token (digits) |
| `PUNCTUATION` | Punctuation or a symbol |
| `UNKNOWN` | Insufficient evidence to assign a language label |
| `OTHER` | A supported but different language/script category |

**For each token labeled `UNKNOWN`,** assess whether you can assign a more specific label based on your bilingual knowledge. If you can, record the label and your evidence. If you cannot, leave it as `UNKNOWN`.

**For tokens labeled `TELUGU_ROMANIZED` or `ENGLISH`,** confirm or correct the label. Record any disagreement and the reason.

**Important:** Do not label a token `TELUGU_ROMANIZED` simply because it is in Roman script. Many Latin-script tokens in code-mixed text are borrowings, abbreviations, or genuinely ambiguous. Use `UNKNOWN` if in doubt.

---

## 8. How to handle named entities, abbreviations, and technical terms

- **Named entities** (WhatsApp, college names, person names, brand names): Record them as-is. Do not transliterate or translate them. Label them as `ENGLISH` if they are English-origin, or `UNKNOWN` if unclear.
- **Abbreviations** (`plz`, `ASAP`, `clg`): Record the expansion if you are confident of it. Label `UNKNOWN` if the abbreviation's language origin is unclear.
- **Technical terms** (`assignment`, `deadline`, `project`, `battery`): These are often widely borrowed into Telugu usage. If you cannot determine whether a token is English or a Telugu borrowing, label it `UNKNOWN` and note the reason.
- **Numbers**: Leave as `NUMBER`. Do not convert numerals to words.

---

## 9. How to handle ambiguity and contextual meaning

Some utterances in the dataset are **genuinely ambiguous** because no surrounding context is available. The annotation notes for each example will flag these.

For ambiguous utterances:

1. List the **two or more distinct meanings** you identify, each with a brief explanation and any supporting evidence from your bilingual knowledge.
2. If one interpretation is clearly more likely in practice, say so and explain why.
3. If you genuinely cannot determine which meaning was intended without more context, mark the intended meaning as **unresolved** and explain why. Do not guess.
4. **Do not silently choose one interpretation** and omit the others.

**Example of a flagged ambiguity (illustrative):**

> `nenu okay ga unna, worry cheyyu`
>
> - Interpretation A: "I am okay, don't worry" (reassurance; 'worry cheyyu' is an elliptical imperative with implicit negation)
> - Interpretation B: "I am okay, you can worry" (literal imperative)
>
> Evidence: In practice, this phrase almost always signals reassurance in code-mixed speech, but the literal parse supports Interpretation B. Without prosodic or conversational context, resolution is uncertain.

---

## 10. How to record a normalization judgment

For some examples, the annotation notes suggest that a **spelling normalization** (e.g., standardizing `ledhu` → `ledu`) might be performed by the system.

For each such case, record:
- Whether the proposed normalization **preserves the intended meaning** (yes / no / uncertain).
- Whether the normalization would **change a named entity** (if so, it must be rejected).
- Whether the normalization would **change a word boundary** (if so, record this).
- Any meaning or pragmatic nuance that might be lost.

---

## 11. How to record selective transliteration judgments

For examples containing Romanized Telugu tokens, the system may attempt to convert them to Telugu script (transliteration).

For each token where transliteration is relevant, record:
- Whether transliterating this token to Telugu script **preserves the intended meaning** (yes / no / uncertain).
- Whether the token is a **named entity** that should not be transliterated.
- Whether the token is a **borrowed English word** used in a Telugu grammatical role, and whether transliterating it would be misleading.
- When in doubt, recommend **abstaining from transliteration** rather than making a change.

---

## 12. What to do when you want to reject an example

You may recommend that an example be **excluded from the dataset** if:

- The source text is unintelligible or uninterpretable.
- The source text contains personal information that should not appear in a research dataset.
- The source text has a meaning you find objectionable.
- The example is too trivial to test anything meaningful.
- You cannot produce a defensible reference translation.

Record your recommendation and the reason. The project team will make the final exclusion decision.

---

## 13. How to record your review

For each example, complete the columns in the companion CSV template file (`reviewer_annotation_template.csv`).

The CSV template contains 17 columns. Every row corresponds to one pilot example (`pilot-001` through `pilot-028`):

### Per-Example Columns (Rows 1–28)

| Column Header | Status | What to enter | Allowed values / Requirements |
|---|---|---|---|
| `example_id` | **Pre-filled** | Example identifier (e.g., `pilot-001`). | Do not modify. |
| `source_text_confirmation` | **Pre-filled** | Exact original utterance text. | Do not edit or modify. |
| `intended_meaning` | **Required** | Your independent assessment of what the speaker meant. | Non-empty description in English. |
| `reference_translation` | **Required** | Natural English translation conveying the intended meaning. | Non-empty natural English sentence. |
| `ambiguity_status` | **Required** | Whether the utterance has context-dependent ambiguity. | Must be exactly: `none`, `detected`, or `abstained`. |
| `alternative_interpretations` | Optional | If `detected` or `abstained`, note alternative readings. | Text description of alternative interpretations. |
| `label_corrections` | Optional | Corrections to baseline token language labels. | e.g. `nenu: TELUGU_ROMANIZED; veltunna: TELUGU_ROMANIZED`. |
| `reviewer_notes` | Optional | Observations, cultural context, or uncertainties. | Text notes. |
| `protected_entities` | Optional | Tokens/entities that must NOT be normalized or transliterated. | e.g. `WhatsApp`, brand names, person names. |
| `normalization_judgment` | Optional | Whether proposed spelling normalizations preserve meaning. | e.g. `preserves_meaning`, `alters_meaning`, or `n/a`. |
| `transliteration_judgment` | Optional | Whether transliterating Romanized Telugu tokens to Telugu script preserves meaning. | e.g. `appropriate`, `inappropriate`, or `n/a`. |
| `exclude_recommendation` | Optional | Flag if the utterance should be excluded from evaluation. | `yes` if recommending exclusion; otherwise leave blank or `no`. |

### Reviewer Metadata & Declarations (Required on every row, or repeated consistently)

| Column Header | Status | What to enter | Expected Value |
|---|---|---|---|
| `reviewer_id` | **Required** | Stable pseudonymous identifier for the reviewer. | e.g., `rev-te-01` (avoid placeholders like `test` or `tbd`). |
| `language_competency_declaration` | **Required** | Declaration of bilingual Telugu–English proficiency. | e.g., `native Telugu, fluent English` or `yes`. |
| `guideline_version` | **Required** | Version of the annotation guidelines followed. | Must be `1.0`. |
| `saw_system_outputs` | **Required** | Whether the reviewer saw any model/system translation outputs prior to reviewing. | Must be `no` (or `false`) to ensure independent reference generation. |
| `independence_declaration` | **Required** | Declaration that reviewer is independent of system development. | Must be `yes`. |

> **Pseudonyms:** Your `reviewer_id` will appear in the published dataset record and audit trail. Use a pseudonym (e.g., `rev-te-01`) if you prefer not to use your real name.

---

## 14. What you are not being asked to certify

Your review certifies only:
- That you have read the source utterance and produced an honest interpretation.
- That your reference translation represents your best bilingual judgment.

Your review does **not** certify:
- That the source utterance is grammatically correct.
- That the draft language labels are all correct.
- That the research system's outputs are correct or incorrect.
- That the project's conclusions are valid.

---

## 15. Privacy and data handling

- Do not include personal names, phone numbers, email addresses, or other identifying information in your annotations.
- All examples in this dataset are constructed examples composed by the research team. They are not real conversations. No real person's personal data is included.
- Your annotations will be stored in the project's dataset files. Contact the project team if you have concerns.

---

## 16. Contact and questions

If you have questions about any example, cannot determine the meaning, or want to flag a problem, record the question in the **Notes** field and contact the project team before completing your review.

Do not guess or fabricate an interpretation when you are genuinely uncertain. An honest "I cannot determine this" is more valuable than an invented answer.

---

## 17. Post-review processing: adjudication, promotion, and readiness gates

For full research transparency, the workflow following submission of your completed annotations proceeds through explicit, verified gates:

1. **Submission Validation & Merge:**
   * The completed CSV is ingested via `python backend/scripts/import_annotations.py import --pilot data/drafts/pilot_examples.jsonl --csv <reviewer_csv> --output-jsonl <merged_draft_jsonl>`.
   * The importer verifies that source texts are untouched, required fields and declarations are present, and candidate IDs match.
   * Merged records strictly retain `annotation_status: "draft"` and `review_status: "not_reviewed"`. The import tool cannot authenticate review by itself.

2. **Adjudication & Exclusion Documentation (Stage 3):**
   * If a second annotator is available, disagreements in intended meaning, reference translation, or token labels are adjudicated.
   * Any recommended exclusions (`exclude_recommendation: yes`) or label adjustments are explicitly reviewed by the project team.
   * Exclusions and decisions are permanently recorded in `data/pilot_v0.1_manifest.json` under `exclusion_log`.

3. **Formal Promotion (Stage 4):**
   * Only records with verified human review are promoted to `annotation_status: "reviewed"`.
   * Provenance fields (`reference_translation` and `intended_meaning`) are updated with the reviewer's pseudonymous ID, review date, and `review_status: "reviewed"`.
   * Structural dataset validity is re-verified (`validate_dataset.py`).

4. **Split Assignment & Evaluation Readiness Gate (Stage 5 & Stage 6):**
   * Assigning splits and split groups does **not** automatically make a dataset ready.
   * Full research evaluation remains strictly blocked until the independent evaluation-readiness checker passes with zero blockers:
     ```powershell
     python backend/scripts/check_evaluation_readiness.py <promoted_dataset.jsonl>
     ```
   * Until this checker exits 0, no empirical evaluation or translation quality score (BLEU-4 / chrF) may be executed or claimed.

---

*Reviewer Handoff Package prepared for BhashaBridge 2.0, Phase 28 (Finalized for Reviewer Delivery). This package is for independent reviewers only and does not constitute project documentation of a completed review.*
