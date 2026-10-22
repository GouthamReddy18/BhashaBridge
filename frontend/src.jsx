import { useState } from 'react';
import { createRoot } from 'react-dom/client';
import './style.css';

const API_BASE = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '');
const MAX_INPUT_CHARS = 2000;

function App() {
  const [text, setText] = useState('');
  const [translate, setTranslate] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState(null);
  const characterCount = Array.from(text).length;

  async function analyze(event) {
    event.preventDefault();
    setError('');
    setResult(null);
    if (!text.trim()) {
      setError('Enter a sentence before analyzing.');
      return;
    }
    if (characterCount > MAX_INPUT_CHARS) {
      setError(`Input must be ${MAX_INPUT_CHARS} characters or fewer.`);
      return;
    }
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/api/v1/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
        body: JSON.stringify({ text, translate }),
      });
      if (!response.ok) {
        let message = `Analysis request failed (HTTP ${response.status}).`;
        try {
          const body = await response.json();
          if (Array.isArray(body.detail)) message = 'The server rejected the input. Check its length and format.';
          else if (typeof body.detail === 'string') message = body.detail;
        } catch { /* Keep the safe HTTP status message. */ }
        throw new Error(message);
      }
      setResult(await response.json());
    } catch (cause) {
      setError(cause instanceof TypeError
        ? 'Could not reach the BhashaBridge API. Start the backend or check its configured URL.'
        : (cause.message || 'Analysis failed.'));
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="shell">
      <header className="hero">
        <p className="eyebrow">TELUGU · ENGLISH · CODE-MIXED TEXT</p>
        <h1>BhashaBridge <span>2.0</span></h1>
        <p className="intro">Inspect token-level language labels and the analysis decisions behind a sentence.</p>
      </header>

      <section className="panel" aria-labelledby="analyze-heading">
        <h2 id="analyze-heading">Analyze a sentence</h2>
        <form onSubmit={analyze}>
          <label htmlFor="sentence">Code-mixed sentence</label>
          <textarea
            id="sentence"
            value={text}
            onChange={(event) => setText(event.target.value)}
            placeholder="Example: nenu college ki vellanu"
            aria-describedby="input-help input-count"
          />
          <div className="input-meta">
            <span id="input-help">Up to {MAX_INPUT_CHARS} characters. Text is sent to your configured BhashaBridge API.</span>
            <span id="input-count" aria-live="polite">{characterCount}/{MAX_INPUT_CHARS}</span>
          </div>
          <label className="check-row">
            <input type="checkbox" checked={translate} onChange={(event) => setTranslate(event.target.checked)} />
            <span><strong>Also request translation</strong><small>Opt-in: if a provider is configured, the sentence is sent to that provider and may incur charges.</small></span>
          </label>
          <button type="submit" disabled={loading || !text.trim()}>{loading ? 'Analyzing…' : 'Analyze sentence'}</button>
        </form>
        {error && <p className="notice error" role="alert">{error}</p>}
        {loading && <p className="notice" role="status">Waiting for the analysis API…</p>}
      </section>

      {result && <Results result={result} />}
      <footer>Conservative research prototype. Language labels and the illustrative ambiguity rule are not validated translation or research conclusions.</footer>
    </main>
  );
}

function Results({ result }) {
  const transliterations = new Map(result.transliterations.map((item) => [item.token_index, item]));
  return (
    <div className="results" aria-live="polite">
      <section className="panel" aria-labelledby="tokens-heading">
        <div className="section-heading"><div><p className="eyebrow">TEXT ANALYSIS</p><h2 id="tokens-heading">Tokens and language labels</h2></div><span className="badge">{result.tokens.length} tokens</span></div>
        <p className="subtle">Original text is preserved. Normalization only collapses whitespace.</p>
        <div className="text-pair"><div><h3>Original</h3><p>{result.original_text}</p></div><div><h3>Normalized</h3><p>{result.normalized_text}</p></div></div>
        {result.tokens.length > 0 ? <div className="token-list">{result.tokens.map((token) => {
          const transliteration = transliterations.get(token.index);
          return <article className="token" key={`${token.index}-${token.start}`}>
            <div className="token-top"><span className="token-word">{token.text}</span><span className="badge">{token.language.label}</span></div>
            <p className="subtle">{token.language.method} · {token.language.evidence} · characters {token.start}–{token.end}</p>
            {transliteration && <p className="subtle">Transliteration: {transliteration.status}{transliteration.candidate ? ` · ${transliteration.candidate}` : ` · ${transliteration.reason}`}</p>}
          </article>;
        })}</div> : <p className="subtle">No tokens were returned.</p>}
      </section>

      <section className="panel" aria-labelledby="ambiguity-heading">
        <p className="eyebrow">EXPLAINABLE DECISIONS</p><h2 id="ambiguity-heading">Ambiguity analysis</h2>
        {result.ambiguities.length === 0 ? <p className="subtle">No ambiguity candidates were reported for this input.</p> : result.ambiguities.map((item, index) => <article className="decision" key={`${item.token_index}-${index}`}>
          <div className="token-top"><strong>{item.surface}</strong><span className={`badge ${item.status}`}>{item.status}</span></div>
          <p>{item.evidence}</p><p className="subtle">Rule: {item.rule_id}{item.selected_candidate ? ` · Selected: ${item.selected_candidate}` : ''}</p>
          <ul>{item.candidates.map((candidate) => <li key={candidate.candidate_id}>{candidate.description} <span className="subtle">({candidate.source})</span></li>)}</ul>
        </article>)}
        <p className="caveat">The current ambiguity rule is a narrow illustrative fixture, not general Telugu-English disambiguation.</p>
      </section>

      <section className="panel" aria-labelledby="translation-heading">
        <p className="eyebrow">OPTIONAL CAPABILITY</p><h2 id="translation-heading">Translation</h2>
        <p className="status-line"><span className={`status-dot ${result.translation.status}`} />{translationLabel(result.translation.status)}</p>
        {result.translation.status === 'success' && <><p className="subtle">Provider: {result.translation.provider_id}{result.translation.provider_model ? ` · model: ${result.translation.provider_model}` : ''}</p><blockquote>{result.translation.translated_text}</blockquote><p className="caveat">Provider output is unreviewed and is not research evidence.</p></>}
        {result.translation.status === 'failed' && <p className="notice error">Translation failed ({result.translation.error_code}). Analysis results are still available.</p>}
        {result.translation.status === 'unavailable' && <p className="subtle">No translation provider is configured. Analysis did not send text to a provider.</p>}
        {result.translation.status === 'disabled' && <p className="subtle">Translation was not requested.</p>}
      </section>

      <section className="panel" aria-labelledby="modules-heading">
        <p className="eyebrow">RUNTIME STATUS</p><h2 id="modules-heading">Analysis modules</h2>
        <ul className="module-list">{result.modules.map((module) => <li key={module.name}><div className="token-top"><strong>{module.name.replaceAll('_', ' ')}</strong><span className={`badge ${module.status}`}>{module.status.replaceAll('_', ' ')}</span></div><p className="subtle">{module.detail}</p></li>)}</ul>
      </section>
    </div>
  );
}

function translationLabel(status) {
  return ({ disabled: 'Not requested', unavailable: 'Unavailable', success: 'Translation received', failed: 'Translation failed' })[status] || 'Unknown status';
}

createRoot(document.getElementById('root')).render(<App />);
