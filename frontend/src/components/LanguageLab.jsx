import React, { useState } from 'react';
import { MAX_INPUT_CHARS, EXAMPLE_UTTERANCES } from '../constants';
import { analyzeText } from '../api';
import { StatusBadge, ScriptBadge, CoordinateChip } from './ui/Badge';

export function LanguageLab({ onNotify }) {
  const [text, setText] = useState('nenu office ki veltunna');
  const [translate, setTranslate] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState(null);
  const [selectedTokenIndex, setSelectedTokenIndex] = useState(0);
  const [activeTab, setActiveTab] = useState('tokens'); // 'tokens' | 'diff' | 'ambiguity' | 'modules' | 'translation'

  const charCount = Array.from(text).length;
  const isOverLimit = charCount > MAX_INPUT_CHARS;

  async function handleAnalyze(e) {
    if (e) e.preventDefault();
    if (!text.trim()) {
      setError('Please enter a sentence to analyze.');
      return;
    }
    if (isOverLimit) {
      setError(`Input exceeds maximum length of ${MAX_INPUT_CHARS} characters.`);
      return;
    }

    setError('');
    setLoading(true);
    setResult(null);
    setSelectedTokenIndex(0);

    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 20000);

    try {
      const data = await analyzeText(text, translate, controller.signal);
      setResult(data);
      setActiveTab('tokens');
    } catch (err) {
      if (err.name === 'AbortError') {
        setError('Request timed out. The local backend took too long to respond.');
      } else if (err.message && err.message.includes('Failed to fetch')) {
        setError('Cannot reach LipiPrism API at http://127.0.0.1:8000. Ensure the backend is running.');
      } else {
        setError(err.message || 'Analysis failed.');
      }
    } finally {
      clearTimeout(timeout);
      setLoading(false);
    }
  }

  function handleKeyDown(e) {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      e.preventDefault();
      handleAnalyze();
    }
  }

  function selectExample(ex) {
    setText(ex.text);
    setError('');
    if (onNotify) onNotify(`Loaded example: ${ex.label}`);
  }

  function copyToClipboard(val, label) {
    navigator.clipboard.writeText(val).then(
      () => onNotify && onNotify(`${label} copied to clipboard`),
      () => onNotify && onNotify('Clipboard access denied.')
    );
  }

  // Lookup transliteration record for token
  const translitMap = new Map((result?.transliterations || []).map((t) => [t.token_index, t]));
  // Lookup ambiguity record for token
  const ambMap = new Map((result?.ambiguities || []).map((a) => [a.token_index, a]));

  const selectedToken = result?.tokens?.[selectedTokenIndex] || null;
  const selectedTranslit = selectedToken ? translitMap.get(selectedToken.index) : null;
  const selectedAmb = selectedToken ? ambMap.get(selectedToken.index) : null;

  const whitespaceChanged = result ? result.original_text !== result.normalized_text : false;

  return (
    <section id="lab" className="lab-section">
      <div className="section-header-block">
        <div className="section-kicker">
          <span className="kicker-index">01</span>
          <span className="kicker-line" />
          <span className="kicker-title">INTERACTIVE WORKSTATION</span>
        </div>
        <h2 className="section-h2">
          Language Lab: <span className="text-tint">Analyze Code-Mixed Text</span>
        </h2>
        <p className="section-sub">
          Inspect conservative language identification, exact Unicode offsets, selective
          transliteration candidates, and context-dependent disambiguation traces in real time.
        </p>
      </div>

      <div className="lab-grid">
        {/* Left Column: Input Console */}
        <div className="lab-console-card">
          <div className="console-topbar">
            <span className="console-title">UTTERANCE CONSOLE</span>
            <span className="console-shortcut">Press Ctrl+Enter to analyze</span>
          </div>

          <form onSubmit={handleAnalyze} className="console-form">
            <div className="textarea-wrapper">
              <label htmlFor="utterance-input" className="sr-only">
                Telugu–English code-mixed sentence
              </label>
              <textarea
                id="utterance-input"
                className="console-textarea"
                rows={4}
                value={text}
                onChange={(e) => setText(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Enter Romanized Telugu / English mixed sentence..."
                maxLength={MAX_INPUT_CHARS + 50}
              />
              <div className="textarea-meta">
                <span className={`char-meter ${isOverLimit ? 'over-limit' : ''}`}>
                  {charCount} / {MAX_INPUT_CHARS} chars
                </span>
                {text && (
                  <button
                    type="button"
                    className="clear-btn"
                    onClick={() => { setText(''); setResult(null); }}
                  >
                    Clear
                  </button>
                )}
              </div>
            </div>

            {/* Example Presets */}
            <div className="example-presets">
              <span className="presets-label">EXEMPLAR PHENOMENA:</span>
              <div className="preset-chips">
                {EXAMPLE_UTTERANCES.map((ex) => (
                  <button
                    key={ex.id}
                    type="button"
                    className={`preset-chip ${text === ex.text ? 'is-active' : ''}`}
                    onClick={() => selectExample(ex)}
                    title={ex.notes}
                  >
                    <span className="preset-tag">{ex.tag}</span>
                    <span className="preset-name">{ex.label}</span>
                  </button>
                ))}
              </div>
            </div>

            {/* Translation Opt-in Checkbox */}
            <div className="optin-panel">
              <label className="checkbox-control" htmlFor="translate-optin">
                <input
                  id="translate-optin"
                  type="checkbox"
                  checked={translate}
                  onChange={(e) => setTranslate(e.target.checked)}
                />
                <span className="checkbox-custom" />
                <span className="checkbox-label">
                  <strong>Request Machine Translation</strong>
                  <small>
                    Optional seam. If an external provider is configured, sentence text will be
                    transmitted externally and may incur API billing.
                  </small>
                </span>
              </label>
            </div>

            {/* Actions Bar */}
            <div className="console-actions">
              <button
                type="submit"
                className="btn btn-primary btn-analyze"
                disabled={loading || !text.trim() || isOverLimit}
              >
                {loading ? (
                  <>
                    <span className="spin-indicator" aria-hidden="true">◌</span>
                    Analyzing Utterance...
                  </>
                ) : (
                  <>
                    Run Linguistic Analysis <span aria-hidden="true">→</span>
                  </>
                )}
              </button>
            </div>

            {error && (
              <div className="lab-alert alert-error" role="alert">
                <span className="alert-icon">!</span>
                <span className="alert-text">{error}</span>
              </div>
            )}
          </form>
        </div>

        {/* Right Column: Processing Flow Summary */}
        <div className="lab-aside-card">
          <div className="aside-header">
            <span className="aside-title">LAB PROTOCOL</span>
            <CoordinateChip>STAGE_A</CoordinateChip>
          </div>
          <ol className="protocol-steps">
            <li>
              <span className="step-num">01</span>
              <div className="step-content">
                <strong>Immutable Source</strong>
                <p>Preserves exact Unicode text and indices.</p>
              </div>
            </li>
            <li>
              <span className="step-num">02</span>
              <div className="step-content">
                <strong>Whitespace Normalization</strong>
                <p>Collapses redundant spacing; never alters orthography.</p>
              </div>
            </li>
            <li>
              <span className="step-num">03</span>
              <div className="step-content">
                <strong>Conservative LID</strong>
                <p>Labels tokens; explicitly abstains on UNKNOWN words.</p>
              </div>
            </li>
            <li>
              <span className="step-num">04</span>
              <div className="step-content">
                <strong>Context & Ambiguity</strong>
                <p>Evaluates local syntax and lexical anchor rules.</p>
              </div>
            </li>
          </ol>
          <div className="aside-caveat">
            <span className="caveat-badge">HONEST RESEARCH</span>
            <p>
              Rule fixtures and seed lexicons demonstrate software mechanics. They do not claim broad
              corpus statistical validation.
            </p>
          </div>
        </div>
      </div>

      {/* Results Workspace */}
      {result && (
        <div className="results-container">
          <div className="results-topbar">
            <div className="results-heading">
              <span className="pulse-dot" />
              <h3>Analysis Trace // Utterance Evaluated</h3>
            </div>
            <div className="results-tabs" role="tablist">
              <button
                role="tab"
                aria-selected={activeTab === 'tokens'}
                className={`tab-btn ${activeTab === 'tokens' ? 'is-active' : ''}`}
                onClick={() => setActiveTab('tokens')}
              >
                Token Stream ({result.tokens.length})
              </button>
              <button
                role="tab"
                aria-selected={activeTab === 'diff'}
                className={`tab-btn ${activeTab === 'diff' ? 'is-active' : ''}`}
                onClick={() => setActiveTab('diff')}
              >
                Normalization {whitespaceChanged && <span className="diff-pill">MODIFIED</span>}
              </button>
              <button
                role="tab"
                aria-selected={activeTab === 'ambiguity'}
                className={`tab-btn ${activeTab === 'ambiguity' ? 'is-active' : ''}`}
                onClick={() => setActiveTab('ambiguity')}
              >
                Ambiguity ({result.ambiguities.length})
              </button>
              <button
                role="tab"
                aria-selected={activeTab === 'modules'}
                className={`tab-btn ${activeTab === 'modules' ? 'is-active' : ''}`}
                onClick={() => setActiveTab('modules')}
              >
                Module Health ({result.modules.length})
              </button>
              <button
                role="tab"
                aria-selected={activeTab === 'translation'}
                className={`tab-btn ${activeTab === 'translation' ? 'is-active' : ''}`}
                onClick={() => setActiveTab('translation')}
              >
                Translation ({result.translation.status})
              </button>
            </div>
          </div>

          <div className="results-body">
            {/* View 1: Interactive Token Stream */}
            {activeTab === 'tokens' && (
              <div className="tokens-layout">
                <div className="token-chips-panel">
                  <div className="panel-hint">
                    Select any token below to inspect its linguistic evidence and boundary offsets:
                  </div>
                  <div className="token-stream-flex">
                    {result.tokens.map((token, idx) => {
                      const isSelected = selectedTokenIndex === idx;
                      const translit = translitMap.get(token.index);
                      const hasAmbiguity = ambMap.has(token.index);

                      return (
                        <button
                          key={`${token.index}-${token.start}`}
                          type="button"
                          className={`token-item-btn ${isSelected ? 'is-selected' : ''}`}
                          onClick={() => setSelectedTokenIndex(idx)}
                        >
                          <span className="token-idx-tag">T{token.index + 1}</span>
                          <span className="token-surface" lang={token.language.label === 'TELUGU_SCRIPT' ? 'te' : undefined}>
                            {token.text}
                          </span>
                          <ScriptBadge label={token.language.label} />
                          {translit?.candidate && (
                            <span className="token-script-preview" lang="te">{translit.candidate}</span>
                          )}
                          {hasAmbiguity && <span className="token-amb-pip" title="Ambiguity detected" />}
                        </button>
                      );
                    })}
                  </div>
                </div>

                {/* Detailed Token Inspector Card */}
                {selectedToken && (
                  <div className="token-inspect-card">
                    <div className="inspect-header">
                      <div className="inspect-title-group">
                        <span className="inspect-chip">TOKEN #{selectedToken.index + 1}</span>
                        <h4 className="inspect-surface">{selectedToken.text}</h4>
                      </div>
                      <ScriptBadge label={selectedToken.language.label} />
                    </div>

                    <div className="inspect-props-grid">
                      <div className="prop-row">
                        <span className="prop-key">Category</span>
                        <span className="prop-val">{selectedToken.kind.toUpperCase()}</span>
                      </div>
                      <div className="prop-row">
                        <span className="prop-key">Unicode Offsets</span>
                        <span className="prop-val mono">
                          [{selectedToken.start} : {selectedToken.end}]
                        </span>
                      </div>
                      <div className="prop-row">
                        <span className="prop-key">Identification Method</span>
                        <span className="prop-val mono">{selectedToken.language.method}</span>
                      </div>
                      <div className="prop-row">
                        <span className="prop-key">Linguistic Evidence</span>
                        <span className="prop-val">{selectedToken.language.evidence}</span>
                      </div>
                      {selectedToken.language.confidence !== null && (
                        <div className="prop-row">
                          <span className="prop-key">Model Confidence</span>
                          <span className="prop-val mono">
                            {(selectedToken.language.confidence * 100).toFixed(1)}%
                          </span>
                        </div>
                      )}
                      {selectedTranslit && (
                        <div className="prop-row translit-row">
                          <span className="prop-key">Transliteration</span>
                          <span className="prop-val">
                            <StatusBadge status={selectedTranslit.status} />
                            {selectedTranslit.candidate ? (
                              <strong className="cand-glyph" lang="te"> {selectedTranslit.candidate}</strong>
                            ) : (
                              <small className="cand-reason"> {selectedTranslit.reason}</small>
                            )}
                          </span>
                        </div>
                      )}
                      {selectedAmb && (
                        <div className="prop-row amb-row">
                          <span className="prop-key">Ambiguity Status</span>
                          <span className="prop-val">
                            <StatusBadge status={selectedAmb.status} />
                            <small className="amb-rule"> Rule: {selectedAmb.rule_id}</small>
                          </span>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* View 2: Normalization Comparison */}
            {activeTab === 'diff' && (
              <div className="diff-panel">
                <div className="diff-grid">
                  <div className="diff-box">
                    <div className="diff-box-header">
                      <span className="diff-tag">ORIGINAL SOURCE</span>
                      <button
                        type="button"
                        className="copy-btn"
                        onClick={() => copyToClipboard(result.original_text, 'Original text')}
                      >
                        Copy
                      </button>
                    </div>
                    <p className="diff-text mono">{result.original_text}</p>
                  </div>

                  <div className="diff-box">
                    <div className="diff-box-header">
                      <span className="diff-tag">NORMALIZED TEXT</span>
                      <button
                        type="button"
                        className="copy-btn"
                        onClick={() => copyToClipboard(result.normalized_text, 'Normalized text')}
                      >
                        Copy
                      </button>
                    </div>
                    <p className="diff-text mono">{result.normalized_text}</p>
                  </div>
                </div>
                <div className="diff-footer">
                  <span className="diff-status-badge">
                    {whitespaceChanged ? 'Whitespace altered (collapsed)' : 'No whitespace alterations required'}
                  </span>
                  <p className="diff-desc">
                    Normalization strictly applies whitespace collapsing (`" ".join(text.split())`). It does
                    not alter colloquial spellings or inject unverified character substitutions.
                  </p>
                </div>
              </div>
            )}

            {/* View 3: Ambiguity Inspector */}
            {activeTab === 'ambiguity' && (
              <div className="ambiguity-panel">
                {result.ambiguities.length > 0 ? (
                  result.ambiguities.map((item, i) => (
                    <article className="ambiguity-card" key={`${item.token_index}-${i}`}>
                      <div className="amb-header">
                        <span className="amb-token-tag">TOKEN #{item.token_index + 1}</span>
                        <h4 className="amb-surface">"{item.surface}"</h4>
                        <StatusBadge status={item.status} />
                      </div>
                      <p className="amb-evidence"><strong>Evidence:</strong> {item.evidence}</p>
                      <div className="amb-meta-line">
                        <span className="amb-rule-id">Rule ID: <code>{item.rule_id}</code></span>
                        {item.selected_candidate && (
                          <span className="amb-selected">
                            Selected Sense: <strong>{item.selected_candidate}</strong>
                          </span>
                        )}
                      </div>
                      <div className="amb-candidates-list">
                        <h5>Evaluated Candidate Senses:</h5>
                        <ul>
                          {item.candidates.map((c) => (
                            <li
                              key={c.candidate_id}
                              className={item.selected_candidate === c.candidate_id ? 'is-selected-sense' : ''}
                            >
                              <strong>{c.description}</strong>
                              <span className="cand-source">Source: {c.source}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    </article>
                  ))
                ) : (
                  <div className="empty-panel">
                    <span className="empty-icon" aria-hidden="true">∅</span>
                    <h4>No Contextual Ambiguities Flagged</h4>
                    <p>
                      The input did not trigger active ambiguity rules. (Note: Only deterministic
                      illustrative fixtures such as the English 'bank' context rule are currently registered).
                    </p>
                  </div>
                )}
              </div>
            )}

            {/* View 4: System Modules */}
            {activeTab === 'modules' && (
              <div className="modules-panel">
                <div className="modules-grid">
                  {result.modules.map((m) => (
                    <div className="module-card" key={m.name}>
                      <div className="module-card-top">
                        <strong className="module-name">{m.name.replaceAll('_', ' ')}</strong>
                        <StatusBadge status={m.status} />
                      </div>
                      <p className="module-detail">{m.detail}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* View 5: Translation */}
            {activeTab === 'translation' && (
              <div className="translation-panel">
                <div className="trans-status-banner">
                  <StatusBadge status={result.translation.status} />
                  <span className="trans-status-label">
                    Provider Seam State: <strong>{result.translation.status.toUpperCase()}</strong>
                  </span>
                </div>

                {result.translation.status === 'disabled' && (
                  <div className="trans-box">
                    <p className="trans-intro">
                      Translation was not requested. Analysis was conducted locally within the LipiPrism
                      API boundary with zero external network transmission.
                    </p>
                  </div>
                )}

                {result.translation.status === 'unavailable' && (
                  <div className="trans-box">
                    <p className="trans-intro">
                      Translation was requested, but no translation provider is configured in this local
                      environment (Google Cloud Translation Basic v2 is disabled by default).
                    </p>
                    <p className="trans-detail">
                      Error Code: <code>{result.translation.error_code || 'provider_not_configured'}</code>
                    </p>
                  </div>
                )}

                {result.translation.status === 'failed' && (
                  <div className="trans-box trans-failed">
                    <p className="trans-error">
                      Translation provider request failed ({result.translation.error_code}).
                    </p>
                  </div>
                )}

                {result.translation.status === 'success' && (
                  <div className="trans-box trans-success">
                    <div className="trans-provider-meta">
                      <span>Provider: <code>{result.translation.provider_id}</code></span>
                      {result.translation.provider_model && (
                        <span>Model: <code>{result.translation.provider_model}</code></span>
                      )}
                    </div>
                    <blockquote className="trans-quote">
                      {result.translation.translated_text}
                    </blockquote>
                    <p className="trans-caveat">
                      Provider output is machine-generated and unreviewed; it does not constitute validated research ground truth.
                    </p>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </section>
  );
}
