import React from 'react';
import { CoordinateChip } from './ui/Badge';

export function MethodologySection() {
  return (
    <section id="methodology" className="methodology-section">
      <div className="section-header-block">
        <div className="section-kicker">
          <span className="kicker-index">04</span>
          <span className="kicker-line" />
          <span className="kicker-title">SCIENTIFIC FOUNDATIONS</span>
        </div>
        <h2 className="section-h2">
          Methodology & Limits: <span className="text-tint">Honest Computational Linguistics</span>
        </h2>
        <p className="section-sub">
          BhashaBridge enforces explicit methodological boundaries. We treat automatic metrics
          as surface-overlap approximations rather than definitive semantic validation.
        </p>
      </div>

      <div className="method-cards-grid">
        {/* Card 1: Research Question */}
        <article className="method-article-card">
          <div className="card-topline">
            <span className="card-num">01</span>
            <CoordinateChip>HYPOTHESIS</CoordinateChip>
          </div>
          <h3>The Code-Mixed Research Question</h3>
          <p>
            Informal Romanized Telugu (Telugu written in Latin script) lacks standardized spelling,
            mixes English technical nouns and verbs, and relies heavily on contextual postpositions
            (<em>-ki, -lo, -ga, -aa?</em>).
          </p>
          <p>
            Standard translation engines trained predominantly on native Telugu script often fail or
            hallucinate on code-mixed Romanized sentences. BhashaBridge evaluates whether explicit,
            transparent linguistic transformations improve translation fidelity.
          </p>
        </article>

        {/* Card 2: Metrics vs Semantic Preservation */}
        <article className="method-article-card">
          <div className="card-topline">
            <span className="card-num">02</span>
            <CoordinateChip>METRICS_LIMIT</CoordinateChip>
          </div>
          <h3>Surface Overlap vs. Semantic Truth</h3>
          <p>
            The project computes versioned corpus <strong>BLEU-4</strong> and <strong>chrF</strong>{' '}
            scores against independent human reference translations.
          </p>
          <div className="scientific-distinction-box">
            <strong>Critical Scientific Distinction:</strong>
            <p>
              BLEU and chrF are surface n-gram overlap metrics. They measure textual similarity to a
              reference string; they do <em>not</em> prove semantic preservation or factual truth. Human
              bilingual qualitative assessment remains indispensable.
            </p>
          </div>
        </article>

        {/* Card 3: 5-Stage Human Promotion Gate */}
        <article className="method-article-card">
          <div className="card-topline">
            <span className="card-num">03</span>
            <CoordinateChip>PROVENANCE</CoordinateChip>
          </div>
          <h3>Staged Promotion & Leakage Controls</h3>
          <p>
            Draft utterances authored by researchers are never automatically treated as ground truth:
          </p>
          <ul className="checklist-flow">
            <li><strong>Stage 1:</strong> Automated draft validation (structural exit 0).</li>
            <li><strong>Stage 2:</strong> Independent bilingual reviewer writes reference & meaning.</li>
            <li><strong>Stage 3:</strong> Disagreement adjudication & exclusion logging.</li>
            <li><strong>Stage 4:</strong> Formal promotion with reviewer provenance.</li>
            <li><strong>Stage 5:</strong> Group-aware split partitioning (leakage prevention).</li>
            <li><strong>Stage 6:</strong> Evaluation readiness gate verified.</li>
          </ul>
        </article>

        {/* Card 4: Known Limitations */}
        <article className="method-article-card">
          <div className="card-topline">
            <span className="card-num">04</span>
            <CoordinateChip>LIMITATIONS</CoordinateChip>
          </div>
          <h3>Known Engineering & Linguistic Limits</h3>
          <ul className="limits-list">
            <li>
              <strong>Pilot Corpus Size:</strong> 28 researcher-composed examples calibrate workflows;
              they cannot support broad statistical superiority claims.
            </li>
            <li>
              <strong>No Generalized NER:</strong> Entity protection relies on documented rules and seed
              lexicons; generalized Telugu-English NER is not implemented.
            </li>
            <li>
              <strong>External Provider Seam:</strong> Translation adapter requires explicit user credentials;
              native Telugu API support does not guarantee Romanized code-mixed quality.
            </li>
          </ul>
        </article>
      </div>

      <div className="method-footer-strip">
        <div className="repo-link-wrap">
          <span className="repo-label">OPEN RESEARCH REPOSITORY:</span>
          <a
            href="https://github.com/GouthamReddy18/BhashaBridge.git"
            target="_blank"
            rel="noopener noreferrer"
            className="repo-link"
          >
            github.com/GouthamReddy18/BhashaBridge <span aria-hidden="true">↗</span>
          </a>
        </div>
        <div className="doc-links">
          <a href="https://github.com/GouthamReddy18/BhashaBridge/blob/main/docs/architecture.md" target="_blank" rel="noopener noreferrer">
            Architecture Spec
          </a>
          <span className="doc-sep">·</span>
          <a href="https://github.com/GouthamReddy18/BhashaBridge/blob/main/docs/evaluation_protocol.md" target="_blank" rel="noopener noreferrer">
            Evaluation Protocol
          </a>
          <span className="doc-sep">·</span>
          <a href="https://github.com/GouthamReddy18/BhashaBridge/blob/main/data/guidelines/reviewer_handoff.md" target="_blank" rel="noopener noreferrer">
            Reviewer Guidelines
          </a>
        </div>
      </div>
    </section>
  );
}
