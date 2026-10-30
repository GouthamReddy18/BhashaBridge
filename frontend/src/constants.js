/**
 * LipiPrism — The Language Observatory
 * One utterance. Multiple linguistic dimensions.
 * Constants, Phenomenon presets, and Pipeline specifications.
 *
 * Component Design Inspiration:
 * - Retro Grid, Animated Border & Text Morph patterns adapted from React Bits (MIT) & Magic UI (MIT).
 * - Bento Grid & Card Primitives adapted from shadcn/ui (MIT).
 */

export const API_BASE = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '');
export const MAX_INPUT_CHARS = 2000;

export const NAV_LINKS = [
  { id: 'lab', label: 'Language Lab' },
  { id: 'pipeline', label: 'Linguistic Pipeline' },
  { id: 'observatory', label: 'Research Observatory' },
  { id: 'methodology', label: 'Methodology' },
];

export const EXAMPLE_UTTERANCES = [
  {
    id: 'pilot-001',
    label: 'Basic Code-Mixing',
    tag: 'Pilot v0.1',
    text: 'nenu office ki veltunna',
    notes: 'First-person Telugu subject + English noun "office" + dative postposition "ki" + inflected verb.',
  },
  {
    id: 'pilot-004',
    label: 'Technical Borrowing',
    tag: 'Pilot v0.1',
    text: 'project deadline extend cheyyadam possible aa?',
    notes: 'English technical terms framed in Telugu verbal noun "cheyyadam" and question clitic "aa?".',
  },
  {
    id: 'pilot-005',
    label: 'Adverbialized Adjective',
    tag: 'Pilot v0.1',
    text: 'vaadu chala smart ga matladutaadu',
    notes: 'English adjective "smart" adverbialized with Telugu suffix "-ga" followed by inflected verb.',
  },
  {
    id: 'pilot-007',
    label: 'Spelling Variation',
    tag: 'Pilot v0.1',
    text: 'idi cheyyadam ledhu, time ledu',
    notes: 'Colloquial variation between aspirated "ledhu" and standard "ledu" in the same utterance.',
  },
  {
    id: 'pilot-021',
    label: 'Protected Entity',
    tag: 'Pilot v0.1',
    text: 'WhatsApp lo message pampanu, chusuko',
    notes: 'Protected app name "WhatsApp" must not be translated or transliterated.',
  },
  {
    id: 'illustrative-bank',
    label: 'Contextual Ambiguity',
    tag: 'Illustrative Fixture',
    text: 'The bank account is open',
    notes: 'English ambiguity fixture: immediate anchor "account" resolves "bank" to financial sense.',
  },
  {
    id: 'illustrative-telugu',
    label: 'Romanized Baseline',
    tag: 'Illustrative',
    text: 'nenu college ki vellanu',
    notes: 'Romanized Telugu with English noun "college" and past tense verb.',
  },
];

export const PIPELINE_STAGES = [
  {
    index: '01',
    name: 'Raw Utterance Ingestion',
    category: 'Preservation',
    status: 'active',
    statusLabel: 'Active & Verified',
    description: 'Exact Unicode source text is preserved immutably. Character offsets use Python Unicode code points.',
    safeguards: 'No silent spelling alteration, whitespace stripping, or casing changes.',
  },
  {
    index: '02',
    name: 'Whitespace Normalization',
    category: 'Normalization',
    status: 'active',
    statusLabel: 'Active & Verified',
    description: 'Collapses redundant whitespace while maintaining token boundary offsets and tracking alterations.',
    safeguards: 'Does not correct spelling or infer word boundaries; strictly collapses spaces.',
  },
  {
    index: '03',
    name: 'Unicode Tokenization',
    category: 'Morphosyntax',
    status: 'active',
    statusLabel: 'Active & Verified',
    description: 'Segments text into words and punctuation with start-inclusive, end-exclusive Unicode offsets.',
    safeguards: 'Emoji, punctuation, and multi-word boundaries isolated deterministically.',
  },
  {
    index: '04',
    name: 'Conservative Token LID',
    category: 'Language ID',
    status: 'active',
    statusLabel: 'Active & Verified',
    description: 'Assigns TELUGU_SCRIPT, TELUGU_ROMANIZED, ENGLISH, NUMBER, PUNCTUATION, or UNKNOWN.',
    safeguards: 'Strict abstention policy: unknown Latin tokens are marked UNKNOWN rather than guessed.',
  },
  {
    index: '05',
    name: 'Selective Transliteration',
    category: 'Script Conversion',
    status: 'optional',
    statusLabel: 'Seam Ready (Disabled by Default)',
    description: 'Converts eligible TELUGU_ROMANIZED tokens to Telugu script. Adapter supports optional IndicXlit.',
    safeguards: 'Protected entities, English tokens, and unverified engines are strictly skipped.',
  },
  {
    index: '06',
    name: 'Contextual Disambiguation',
    category: 'Semantics',
    status: 'fixture',
    statusLabel: 'Deterministic Fixture Active',
    description: 'Evaluates immediate context anchors around ambiguous tokens. Currently includes bank fixture.',
    safeguards: 'Abstains if contextual anchors are absent or conflicting; does not fabricate meaning.',
  },
  {
    index: '07',
    name: 'Provider Translation Seam',
    category: 'Translation',
    status: 'opt_in',
    statusLabel: 'Opt-In Seam (Disabled)',
    description: 'Decoupled translation seam supporting Google Cloud Translation v2. Strictly requires opt-in.',
    safeguards: 'Zero transmission without explicit request flag and configured API authorization.',
  },
  {
    index: '08',
    name: 'Four-Condition Evaluation',
    category: 'Metrics & Protocol',
    status: 'blocked',
    statusLabel: 'Evaluation Blocked (Gate Intact)',
    description: 'Measures BLEU-4 and chrF surface overlap against human reference translations.',
    safeguards: 'Evaluation is strictly blocked until independent bilingual review is completed.',
  },
];

export const CONDITION_DETAILS = {
  direct_v1: {
    title: 'Direct Baseline',
    desc: 'Translates raw code-mixed text as received without any preprocessing or assistance.',
    stage: 'Raw Input',
  },
  normalized_v1: {
    title: 'Linguistic Normalization',
    desc: 'Applies qualified Telugu-English linguistic normalizer before translation.',
    stage: 'Normalization',
  },
  transliterated_v1: {
    title: 'Selective Transliteration',
    desc: 'Applies normalization + selective conversion of Romanized Telugu to Telugu script.',
    stage: 'Transliteration',
  },
  ambiguity_aware_v1: {
    title: 'Contextual Disambiguation',
    desc: 'Applies all prior transformations + context-driven ambiguity resolution.',
    stage: 'Ambiguity Resolution',
  },
};
