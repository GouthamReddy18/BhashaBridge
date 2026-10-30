import React, { useState, useEffect } from 'react';
import { CoordinateChip } from './ui/Badge';

const BILINGUAL_PAIRS = [
  { roman: 'nenu', script: 'నేను', en: 'I', label: '1st person pronoun' },
  { roman: 'office ki', script: 'ఆఫీస్ కి', en: 'to the office', label: 'borrowed noun + dative' },
  { roman: 'veltunna', script: 'వెళ్తున్నా', en: 'am going', label: 'present continuous verb' },
  { roman: 'smart ga', script: 'స్మార్ట్ గా', en: 'smartly', label: 'English adj + Telugu suffix' },
];

export function Hero({ readiness }) {
  const [activePairIndex, setActivePairIndex] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setActivePairIndex((prev) => (prev + 1) % BILINGUAL_PAIRS.length);
    }, 3200);
    return () => clearInterval(timer);
  }, []);

  const activePair = BILINGUAL_PAIRS[activePairIndex];

  return (
    <section id="hero" className="observatory-hero">
      {/* Background scientific grid & telemetry lines */}
      <div className="hero-grid-overlay" aria-hidden="true" />
      <div className="hero-crosshair crosshair-tl" aria-hidden="true">+</div>
      <div className="hero-crosshair crosshair-tr" aria-hidden="true">+</div>
      <div className="hero-crosshair crosshair-bl" aria-hidden="true">+</div>
      <div className="hero-crosshair crosshair-br" aria-hidden="true">+</div>

      <div className="hero-container">
        <div className="hero-telemetry">
          <CoordinateChip>SYS_STATUS: ACTIVE // EXPERIMENT_ARM: 4-CONDITION</CoordinateChip>
          <span className="telemetry-divider">/</span>
          <span className="telemetry-spec">ROMANIZED TELUGU · NLP RESEARCH LAB</span>
        </div>

        <div className="hero-split">
          <div className="hero-lead">
            <h1 className="hero-headline">
              <span className="hero-glyph" lang="te" aria-label="Bhasha Vantena">భాషా వంతెన</span>
              <span className="hero-main-title">
                Bridging code-mixed Telugu to <em className="glow-em">computational meaning.</em>
              </span>
            </h1>

            <p className="hero-description">
              An explainable NLP research framework investigating whether explicit linguistic
              normalization, selective transliteration, and contextual ambiguity resolution preserve
              authentic meaning when translating Romanized Telugu–English text.
            </p>

            <div className="hero-actions">
              <a href="#lab" className="btn btn-primary">
                Explore Language Lab <span className="btn-arrow" aria-hidden="true">↓</span>
              </a>
              <a href="#observatory" className="btn btn-outline">
                Inspect Research Readiness <span className="btn-arrow" aria-hidden="true">→</span>
              </a>
            </div>
          </div>

          <div className="hero-visual-card">
            <div className="card-header-bar">
              <span className="card-dot dot-red" />
              <span className="card-dot dot-yellow" />
              <span className="card-dot dot-green" />
              <span className="card-label">ILLUSTRATIVE VISUAL SPECIMEN // NOT LIVE RESULT</span>
            </div>

            <div className="bilingual-display">
              <div className="display-stream stream-roman">
                <span className="stream-type">ROMANIZED INPUT</span>
                <span className="stream-text" key={`roman-${activePairIndex}`}>
                  {activePair.roman}
                </span>
              </div>

              <div className="stream-connector" aria-hidden="true">
                <span className="connector-line" />
                <span className="connector-pill">TRANSFORM</span>
                <span className="connector-line" />
              </div>

              <div className="display-stream stream-script">
                <span className="stream-type">TELUGU SCRIPT</span>
                <span className="stream-text glyph-te" lang="te" key={`script-${activePairIndex}`}>
                  {activePair.script}
                </span>
              </div>

              <div className="stream-connector" aria-hidden="true">
                <span className="connector-line" />
                <span className="connector-pill">MEANING</span>
                <span className="connector-line" />
              </div>

              <div className="display-stream stream-meaning">
                <span className="stream-type">ENGLISH TRANSLATION</span>
                <span className="stream-text text-meaning" key={`en-${activePairIndex}`}>
                  "{activePair.en}"
                </span>
              </div>

              <div className="stream-footer">
                <span className="footer-phenomenon">{activePair.label}</span>
                <span className="footer-status">ILLUSTRATIVE TRACE</span>
              </div>
            </div>
          </div>
        </div>

        {/* Scientific metrics bar */}
        <div className="hero-stats-band">
          <div className="stat-node">
            <span className="stat-val">315</span>
            <span className="stat-label">Verified Tests (Snapshot)</span>
          </div>
          <div className="stat-node">
            <span className="stat-val">28</span>
            <span className="stat-label">Pilot Drafts (15 Phenomena)</span>
          </div>
          <div className="stat-node">
            <span className="stat-val">4</span>
            <span className="stat-label">Controlled Conditions</span>
          </div>
          <div className="stat-node stat-highlight">
            <span className="stat-val">0</span>
            <span className="stat-label">Fabricated Scores (Honest Gate)</span>
          </div>
        </div>
      </div>
    </section>
  );
}
