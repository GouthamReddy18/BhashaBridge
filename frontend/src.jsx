import { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import './style.css';

const API_BASE = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '');
const MAX_INPUT_CHARS = 2000;
const EXAMPLES = [
  { label: 'Romanized Telugu · illustrative', text: 'nenu college ki vellanu' },
  { label: 'English · ambiguity fixture', text: 'The bank account is open' },
];
const NAV_ITEMS = [['workspace', 'Analyze'], ['conditions', 'Conditions'], ['readiness', 'Readiness'], ['method', 'Method']];

async function requestJson(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, options);
  if (!response.ok) {
    let message = `Request failed (HTTP ${response.status}).`;
    try {
      const body = await response.json();
      if (Array.isArray(body.detail)) message = 'The server rejected the input. Check its length and format.';
      else if (typeof body.detail === 'string') message = body.detail;
    } catch { /* Keep a safe status message when the body is not JSON. */ }
    throw new Error(message);
  }
  return response.json();
}

function App() {
  const [text, setText] = useState('');
  const [translate, setTranslate] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState(null);
  const [activeView, setActiveView] = useState('tokens');
  const [readiness, setReadiness] = useState(null);
  const [readinessError, setReadinessError] = useState('');
  const [menuOpen, setMenuOpen] = useState(false);
  const [notice, setNotice] = useState('');
  const characterCount = Array.from(text).length;
  const overLimit = characterCount > MAX_INPUT_CHARS;

  useEffect(() => {
    const controller = new AbortController();
    requestJson('/api/v1/research/readiness', { signal: controller.signal })
      .then(setReadiness)
      .catch((cause) => {
        if (cause.name !== 'AbortError') setReadinessError('Readiness information is unavailable. The API may be offline.');
      });
    return () => controller.abort();
  }, []);

  async function analyze(event) {
    event.preventDefault();
    setError('');
    setResult(null);
    if (!text.trim()) return setError('Enter a sentence before analyzing.');
    if (overLimit) return setError(`Input must be ${MAX_INPUT_CHARS} characters or fewer.`);
    setLoading(true);
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), 20000);
    try {
      const payload = await requestJson('/api/v1/analyze', {
        method: 'POST', headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
        body: JSON.stringify({ text, translate }), signal: controller.signal,
      });
      setResult(payload);
      setActiveView('tokens');
    } catch (cause) {
      setError(cause.name === 'AbortError'
        ? 'The request timed out. Check that the backend is responding and try again.'
        : cause instanceof TypeError
          ? 'Could not reach the BhashaBridge API. Start the backend or check its configured URL.'
          : (cause.message || 'Analysis failed.'));
    } finally {
      window.clearTimeout(timeout);
      setLoading(false);
    }
  }

  async function copyText(value, label) {
    try {
      await navigator.clipboard.writeText(value);
      setNotice(`${label} copied.`);
    } catch {
      setNotice('Clipboard access is unavailable in this browser.');
    }
    window.setTimeout(() => setNotice(''), 2600);
  }

  return (
    <>
      <a className="skip-link" href="#main">Skip to content</a>
      <header className="site-header">
        <a className="brand" href="#home" aria-label="BhashaBridge home">
          <span className="brand-mark" aria-hidden="true"><i /><i /><i /></span>
          <span>Bhasha<span className="brand-light">Bridge</span><small>RESEARCH LAB · 2.0</small></span>
        </a>
        <button className="menu-toggle" type="button" aria-expanded={menuOpen} aria-controls="primary-nav" onClick={() => setMenuOpen(!menuOpen)}>
          <span className="sr-only">{menuOpen ? 'Close' : 'Open'} navigation</span><span aria-hidden="true">{menuOpen ? '×' : '☰'}</span>
        </button>
        <nav id="primary-nav" className={menuOpen ? 'primary-nav is-open' : 'primary-nav'} aria-label="Main navigation">
          {NAV_ITEMS.map(([id, label]) => <a key={id} href={`#${id}`} onClick={() => setMenuOpen(false)}>{label}</a>)}
          <a className="nav-cta" href="#workspace" onClick={() => setMenuOpen(false)}>Open workspace <span aria-hidden="true">↗</span></a>
        </nav>
      </header>

      <main id="main">
        <section id="home" className="hero">
          <div className="hero-grid" aria-hidden="true" />
          <div className="hero-content">
            <p className="eyebrow light-eyebrow"><span className="eyebrow-dot" /> EXPLAINABLE NLP FOR CODE-MIXED LANGUAGE</p>
            <h1>Where Telugu<br />meets <em>meaning.</em></h1>
            <p className="hero-intro">Explore how Romanized Telugu and English can be analyzed with transparent linguistic decisions, careful resource boundaries, and an honest research process.</p>
            <div className="hero-actions"><a className="button button-primary" href="#workspace">Analyze text <span aria-hidden="true">↓</span></a><a className="text-link light-link" href="#method">Explore the methodology <span aria-hidden="true">→</span></a></div>
            <div className="hero-note"><span className="note-rule" /> Research infrastructure is ready to inspect. Research evidence is not yet available.</div>
          </div>
          <div className="hero-visual" aria-label="Illustration of two language streams joining">
            <div className="orbit orbit-one" /><div className="orbit orbit-two" />
            <div className="language-chip chip-telugu" lang="te">తెలుగు</div><div className="language-chip chip-english">English</div>
            <div className="bridge-core"><span>భాష</span><b>↔</b><span>meaning</span></div>
            <span className="orbit-caption caption-top">LANGUAGE</span><span className="orbit-caption caption-bottom">CONTEXT</span>
          </div>
          <div className="hero-bottom"><span>01 / ANALYZE</span><span>LANGUAGE · CONTEXT · MEANING</span><span>↓ SCROLL TO EXPLORE</span></div>
        </section>

        <section className="readiness-ribbon" aria-label="Current research readiness">
          <div className="ribbon-label"><span className="status-pip blocked" /> CURRENT RESEARCH STATUS</div>
          <div className="ribbon-main">{readiness ? (readiness.research_ready ? 'Ready for evaluation' : 'Research evaluation is blocked') : readinessError || 'Checking research readiness…'}</div>
          <div className="ribbon-detail">{readiness ? `${readiness.dataset.records_examined} illustrative records · ${readiness.dataset.blocking_errors} readiness blockers · no eligible resources` : 'Readiness comes from the local API.'}</div>
          <a href="#readiness" className="ribbon-link">See what is needed <span aria-hidden="true">→</span></a>
        </section>

        <section id="workspace" className="section workspace-section">
          <SectionHeader number="01" kicker="INTERACTIVE WORKSPACE" title={<>Read the text,<br /><em>not just the label.</em></>} description="Send a sentence to the local analysis API and inspect the actual token, normalization, transliteration, and ambiguity traces it returns." />
          <div className="workspace-layout">
            <form className="editor-panel" onSubmit={analyze}>
              <div className="panel-topline"><span className="step-label">INPUT TEXT</span><span className="local-chip"><i /> LOCAL ANALYSIS</span></div>
              <label htmlFor="sentence">Telugu–English code-mixed sentence</label>
              <textarea id="sentence" value={text} onChange={(event) => setText(event.target.value)} placeholder="Type or paste a sentence to explore…" aria-describedby="input-hint input-count" />
              <div className="input-toolbar"><div className="sample-group" aria-label="Illustrative examples"><span className="toolbar-label">TRY AN EXAMPLE</span>{EXAMPLES.map((example) => <button className="sample-button" type="button" key={example.label} onClick={() => { setText(example.text); setError(''); }}>{example.label}</button>)}</div><span id="input-count" className={overLimit ? 'char-count is-over' : 'char-count'} aria-live="polite">{characterCount}<span> / {MAX_INPUT_CHARS}</span></span></div>
              <p id="input-hint" className="field-hint">Original spelling and spacing are preserved. Character count uses Unicode code points.</p>
              <label className="transmission-option" htmlFor="translate"><input id="translate" type="checkbox" checked={translate} onChange={(event) => setTranslate(event.target.checked)} /><span className="custom-check" aria-hidden="true" /><span><strong>Request an English translation</strong><small>Optional. If configured, your text is sent to the selected provider and may incur charges.</small></span></label>
              <button className="button analyze-button" type="submit" disabled={loading || !text.trim() || overLimit}>{loading ? <><span className="spinner" aria-hidden="true" /> Analyzing…</> : <>Analyze sentence <span aria-hidden="true">→</span></>}</button>
              {error && <p className="inline-alert" role="alert"><span aria-hidden="true">!</span>{error}</p>}
              {loading && <p className="loading-note" role="status">Waiting for a response from the analysis API…</p>}
              <p className="editor-footnote"><span aria-hidden="true">⌁</span> Analysis requests stay within the configured BhashaBridge API. Provider transmission happens only when translation is explicitly selected.</p>
            </form>
            <div className="workspace-aside"><div className="aside-index">A / ANALYSIS FLOW</div><ol className="flow-list">
              <li><span className="flow-number">01</span><div><strong>Preserve</strong><p>Keep the exact source text as received.</p></div></li>
              <li><span className="flow-number">02</span><div><strong>Normalize</strong><p>Collapse whitespace; do not infer a spelling correction.</p></div></li>
              <li><span className="flow-number">03</span><div><strong>Identify</strong><p>Label tokens conservatively and abstain when evidence is weak.</p></div></li>
              <li><span className="flow-number">04</span><div><strong>Explain</strong><p>Inspect rule evidence, uncertainty, and module status.</p></div></li>
            </ol><div className="aside-callout"><span className="callout-icon" aria-hidden="true">i</span><p><strong>Illustrative inputs only.</strong><br />Examples help explore software behavior. They are not validated language data or research evidence.</p></div></div>
          </div>
          {notice && <p className="toast" role="status">{notice}</p>}
          {result && <AnalysisResults result={result} activeView={activeView} setActiveView={setActiveView} copyText={copyText} />}
        </section>

        <section id="conditions" className="section conditions-section">
          <SectionHeader number="02" kicker="CONTROLLED EXPERIMENT DESIGN" title={<>Four stages.<br /><em>One cumulative question.</em></>} description="Each condition adds a defined stage. A downstream condition stays blocked when a required resource or its prerequisite is absent." />
          {readiness ? <div className="condition-track" aria-label="Cumulative four-condition experiment">{readiness.conditions.map((condition, index) => <ConditionCard key={condition.id} condition={condition} index={index} />)}</div> : <div className="empty-panel" role="status">Condition status is unavailable. Check that the local API is running.</div>}
          <div className="condition-footnote"><span className="status-pip blocked" /> A blocked condition has no translation output or metric. It is not assigned a zero score.</div>
        </section>

        <section id="readiness" className="section readiness-section">
          <SectionHeader number="03" kicker="RESEARCH READINESS" title={<>Infrastructure exists.<br /><em>Evidence comes later.</em></>} description="The local readiness endpoint checks the illustrative dataset and provider configuration. Resource availability is reported separately from research eligibility." />
          {readiness ? <ReadinessDashboard readiness={readiness} /> : <div className="empty-panel" role="status">{readinessError || 'Checking the current project state…'}</div>}
        </section>

        <section id="method" className="section method-section">
          <SectionHeader number="04" kicker="METHOD & LIMITS" title={<>A careful measure<br /><em>of a complex question.</em></>} description="Automatic similarity can compare words with a reference. It cannot establish that meaning survived." />
          <div className="method-grid">
            <article className="method-card method-dark"><span className="card-index">01 — DESIGN</span><h3>Cumulative conditions</h3><p>Compare exact source, reviewed normalization, selective transliteration, and authorized contextual transformations. Keep each added stage traceable.</p><a href="https://github.com/GouthamReddy18/BhashaBridge/blob/main/docs/evaluation_protocol.md" target="_blank" rel="noreferrer">Read the protocol <span aria-hidden="true">↗</span></a></article>
            <article className="method-card"><span className="card-index">02 — METRICS</span><h3>BLEU-4 + chrF</h3><p>Versioned corpus metrics compare each output with a reviewed English reference. They are proxies for surface similarity, not human semantic judgment.</p><a href="https://github.com/GouthamReddy18/BhashaBridge/blob/main/docs/evaluation_protocol.md#phase-6d2-metric-implementation" target="_blank" rel="noreferrer">See configurations <span aria-hidden="true">↗</span></a></article>
            <article className="method-card"><span className="card-index">03 — HUMAN REVIEW</span><h3>Meaning needs people</h3><p>Human assessment is a separate, pending workflow. No ratings exist. The proposed 0–4 rubric still needs piloting before use as a validated outcome.</p><a href="https://github.com/GouthamReddy18/BhashaBridge/blob/main/docs/dataset-acquisition-and-review.md" target="_blank" rel="noreferrer">Annotation guide <span aria-hidden="true">↗</span></a></article>
          </div>
          <p className="method-disclaimer"><span aria-hidden="true">✳</span> No research scores, improvement claims, or human ratings are available in this project.</p>
        </section>
      </main>

      <footer className="site-footer"><a className="brand footer-brand" href="#home"><span className="brand-mark" aria-hidden="true"><i /><i /><i /></span><span>Bhasha<span className="brand-light">Bridge</span><small>RESEARCH LAB · 2.0</small></span></a><p>Explainable analysis for Telugu–English code-mixed text.<br />Software readiness is not research evidence.</p><a className="back-top" href="#home">Back to top ↑</a></footer>
    </>
  );
}

function SectionHeader({ number, kicker, title, description }) {
  return <div className="section-header"><div className="section-number">{number}<span> / 04</span></div><div className="section-heading-content"><p className="eyebrow">{kicker}</p><h2>{title}</h2></div><p className="section-description">{description}</p></div>;
}

function AnalysisResults({ result, activeView, setActiveView, copyText }) {
  const transliterations = new Map((result.transliterations || []).map((item) => [item.token_index, item]));
  const views = [['tokens', 'Tokens', result.tokens.length], ['ambiguity', 'Ambiguity', result.ambiguities.length], ['modules', 'Modules', result.modules.length], ['translation', 'Translation', null]];
  const normalizationChanged = result.original_text !== result.normalized_text;
  return <section className="analysis-output" aria-labelledby="analysis-output-title">
    <div className="output-header"><div><p className="eyebrow">LIVE API RESPONSE</p><h3 id="analysis-output-title">Analysis trace</h3></div><span className="output-ready"><i /> Response received</span></div>
    <div className="text-comparison"><div><div className="comparison-label">ORIGINAL <button type="button" className="copy-button" onClick={() => copyText(result.original_text, 'Original text')}>Copy</button></div><p>{result.original_text}</p></div><div><div className="comparison-label">NORMALIZED <span className={normalizationChanged ? 'change-tag' : 'same-tag'}>{normalizationChanged ? 'WHITESPACE CHANGED' : 'UNCHANGED'}</span><button type="button" className="copy-button" onClick={() => copyText(result.normalized_text, 'Normalized text')}>Copy</button></div><p>{result.normalized_text}</p></div></div>
    <div className="result-tabs" role="group" aria-label="Analysis result views">{views.map(([id, label, count]) => <button type="button" key={id} className={activeView === id ? 'result-tab active' : 'result-tab'} aria-pressed={activeView === id} onClick={() => setActiveView(id)}>{label}{count !== null && <span>{count}</span>}</button>)}</div>
    <div className="result-pane">
      {activeView === 'tokens' && <><p className="pane-intro">Offsets use Python Unicode code points in normalized text; start is inclusive and end is exclusive.</p>{result.tokens.length ? <div className="analysis-token-grid">{result.tokens.map((token) => {
        const transliteration = transliterations.get(token.index);
        return <details className="analysis-token" key={`${token.index}-${token.start}`}><summary><span className="token-index">{String(token.index + 1).padStart(2, '0')}</span><span className="token-text" lang={token.language.label === 'TELUGU_SCRIPT' ? 'te' : undefined}>{token.text}</span><span className="token-label">{token.language.label.replaceAll('_', ' ')}</span><span className="expand-mark" aria-hidden="true">+</span></summary><div className="token-evidence"><p><strong>Evidence</strong>{token.language.evidence}</p><p><strong>Method</strong>{token.language.method}</p><p><strong>Offset</strong>{token.start}–{token.end}</p>{transliteration && <p><strong>Transliteration</strong>{transliteration.status}{transliteration.candidate ? ` · ${transliteration.candidate}` : ` · ${transliteration.reason}`}</p>}</div></details>;
      })}</div> : <EmptyState title="No tokens returned" body="The API returned an empty token list for this input." />}</>}
      {activeView === 'ambiguity' && <>{result.ambiguities.length ? result.ambiguities.map((item, index) => <article className="ambiguity-item" key={`${item.token_index}-${index}`}><div className="ambiguity-title"><span className="token-index">{String(item.token_index + 1).padStart(2, '0')}</span><strong>{item.surface}</strong><StatusBadge status={item.status} /></div><p>{item.evidence}</p><p className="detail-line">Rule <code>{item.rule_id}</code>{item.selected_candidate && <> · Selected <strong>{item.selected_candidate}</strong></>}</p><ul>{item.candidates.map((candidate) => <li key={candidate.candidate_id}><strong>{candidate.description}</strong><span>{candidate.source}</span></li>)}</ul></article>) : <EmptyState title="No ambiguity candidates" body="The API did not report an ambiguity for this input. This is not proof that the sentence has only one possible meaning." />}<p className="caveat-note">The active bank rule is an illustrative fixture, not a validated Telugu-English resource.</p></>}
      {activeView === 'modules' && <ul className="module-status-list">{result.modules.map((module) => <li key={module.name}><div><strong>{module.name.replaceAll('_', ' ')}</strong><StatusBadge status={module.status} /></div><p>{module.detail}</p></li>)}</ul>}
      {activeView === 'translation' && <TranslationResultPanel translation={result.translation} />}
    </div>
  </section>;
}

function TranslationResultPanel({ translation }) {
  const labels = { disabled: 'Not requested', unavailable: 'Unavailable', success: 'Translation received', failed: 'Translation failed' };
  return <div className="translation-result"><div className="translation-state"><StatusBadge status={translation.status} /><strong>{labels[translation.status] || 'Unknown status'}</strong></div>
    {translation.status === 'success' && <><p className="provider-line">Provider <code>{translation.provider_id}</code>{translation.provider_model && <> · model <code>{translation.provider_model}</code></>}</p><blockquote>{translation.translated_text}</blockquote><p className="caveat-note">Provider output is unreviewed and is not research evidence.</p></>}
    {translation.status === 'failed' && <p className="inline-alert">Translation failed ({translation.error_code}). Analysis results remain available.</p>}
    {translation.status === 'unavailable' && <p className="pane-intro">No translation provider is configured. The sentence was not sent to a provider.</p>}
    {translation.status === 'disabled' && <p className="pane-intro">Translation was not requested.</p>}
  </div>;
}

function ConditionCard({ condition, index }) {
  const stageNames = [['Exact source'], ['Reviewed normalization'], ['Normalization', 'Selective transliteration'], ['Normalization', 'Selective transliteration', 'Contextual transformation']][index];
  const titles = ['Direct', 'Normalized', 'Transliterated', 'Ambiguity-aware'];
  const purposes = ['Send the source exactly as received.', 'Apply an eligible linguistic normalizer.', 'Add reviewed selective transliteration.', 'Add an authorized contextual transformation.'];
  return <article className={`condition-card condition-${index + 1}`}><div className="condition-top"><span className="condition-number">0{index + 1}</span><StatusBadge status={condition.status} /></div><p className="condition-id">{condition.id}</p><h3>{titles[index]}</h3><p className="condition-purpose">{purposes[index]}</p><div className="condition-stages"><span>REQUIRES</span>{stageNames.map((stage) => <span key={stage} className="stage-chip">{stage}</span>)}</div><p className="condition-reason">{condition.reason}</p><div className="condition-output"><span>TRANSLATION OUTPUT</span><strong>Not available</strong></div></article>;
}

function ReadinessDashboard({ readiness }) {
  return <div className="readiness-grid">
    <article className="readiness-card dataset-readiness"><div className="readiness-card-top"><span className="readiness-icon" aria-hidden="true">▤</span><StatusBadge status={readiness.dataset.evaluation_status} /></div><p className="card-index">DATASET · {readiness.dataset.name}</p><h3>{readiness.dataset.structural_status === 'valid' ? 'Format checks pass.' : 'Dataset structure needs review.'}</h3><p className="card-copy">The illustrative file has {readiness.dataset.records_examined} records, {readiness.dataset.structural_errors} structural errors, and {readiness.dataset.warnings} draft warnings.</p><div className="readiness-count"><strong>{readiness.dataset.blocking_errors}</strong><span>readiness blockers</span></div><ul className="blocker-list">{readiness.dataset.blocker_categories.map((item) => <li key={item}>{item}</li>)}</ul></article>
    <article className="readiness-card provider-readiness"><div className="readiness-card-top"><span className="readiness-icon" aria-hidden="true">⇄</span><StatusBadge status={readiness.provider.status} /></div><p className="card-index">TRANSLATION PROVIDER</p><h3>External translation stays opt-in.</h3><p className="card-copy">{readiness.provider.detail}</p><p className="provider-code">{readiness.provider.provider_id}</p><p className="caveat-note">Romanized Telugu suitability has not been established. No provider call is made by this readiness check.</p></article>
    <article className="readiness-card resource-readiness"><div className="readiness-card-top"><span className="readiness-icon" aria-hidden="true">⌘</span><span className="status-pill">RESOURCE INVENTORY</span></div><p className="card-index">LINGUISTIC RESOURCES</p><h3>No research-qualified transformation set.</h3><ul className="resource-list">{readiness.resources.map((resource) => <li key={resource.id}><div><strong>{resource.id.replaceAll('_', ' ')}</strong><StatusBadge status={resource.status} /></div><p>{resource.detail}</p></li>)}</ul></article>
    <article className="readiness-card reports-readiness"><div className="readiness-card-top"><span className="readiness-icon" aria-hidden="true">⌁</span><StatusBadge status={readiness.evaluation_reports.status} /></div><p className="card-index">EVALUATION REPORTS</p><h3>No report catalog is connected.</h3><p className="card-copy">{readiness.evaluation_reports.detail}</p><p className="empty-explanation">This dashboard does not display generated or synthetic scores. Load a validated artifact through the offline CLI when eligible research outputs exist.</p></article>
  </div>;
}

function StatusBadge({ status }) {
  const label = String(status || 'unknown').replaceAll('_', ' ');
  const tone = ['ready', 'available', 'success', 'configured', 'resolved'].includes(status) ? 'positive' : ['failed', 'invalid', 'blocked', 'not_ready'].includes(status) ? 'negative' : 'caution';
  return <span className={`status-badge ${tone}`}><i aria-hidden="true" />{label}</span>;
}

function EmptyState({ title, body }) {
  return <div className="empty-state"><span aria-hidden="true">∅</span><div><strong>{title}</strong><p>{body}</p></div></div>;
}

createRoot(document.getElementById('root')).render(<App />);
