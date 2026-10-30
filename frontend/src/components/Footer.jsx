import React from 'react';

export function Footer() {
  return (
    <footer className="observatory-footer">
      <div className="footer-inner">
        <div className="footer-col-main">
          <div className="footer-brand">
            <span className="brand-accent">LIPI</span>
            <span className="brand-main">PRISM</span>
            <span className="brand-tag">THE LANGUAGE OBSERVATORY</span>
          </div>
          <p className="footer-tagline">
            One utterance. Multiple linguistic dimensions. Explainable NLP research for Romanized Telugu–English code-mixed communication.
          </p>
          <p className="footer-integrity-caveat">
            <strong>Scientific Integrity Statement:</strong> Engineering readiness is not empirical research evidence.
            All reported scores require verified human-reviewed reference translations and genuine provider execution.
          </p>
        </div>

        <div className="footer-col-nav">
          <span className="col-heading">OBSERVATORY</span>
          <ul>
            <li><a href="#lab">Interactive Language Lab</a></li>
            <li><a href="#pipeline">Linguistic Pipeline</a></li>
            <li><a href="#observatory">Research Gates Monitor</a></li>
            <li><a href="#methodology">Scientific Methodology</a></li>
          </ul>
        </div>

        <div className="footer-col-telemetry">
          <span className="col-heading">TELEMETRY & SPECS</span>
          <div className="telemetry-specs-list">
            <div><span>API:</span> <code>FastAPI v0.3.0</code></div>
            <div><span>FRONTEND:</span> <code>Vite v8 + React 19</code></div>
            <div><span>TEST SUITE:</span> <code>315 Passed (Snapshot)</code></div>
            <div><span>READINESS:</span> <code>NOT READY (Gate Intact)</code></div>
          </div>
          <a href="#hero" className="back-top-link">
            Back to Top ↑
          </a>
        </div>
      </div>

      <div className="footer-bottom-bar">
        <span>© 2026 LipiPrism Research Team (formerly BhashaBridge) · Open Source NLP Framework</span>
        <span>Coordinates: 17.3850° N, 78.4867° E // Hyderabad, India</span>
      </div>
    </footer>
  );
}
