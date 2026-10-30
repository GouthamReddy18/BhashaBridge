import React, { useState } from 'react';
import { NAV_LINKS } from '../constants';

export function Header({ readiness }) {
  const [menuOpen, setMenuOpen] = useState(false);

  const isBlocked = readiness ? !readiness.research_ready : true;
  const statusLabel = readiness
    ? (readiness.research_ready ? 'Evaluation Ready' : 'Research Gate Blocked')
    : 'Connecting to API...';

  return (
    <header className="observatory-header">
      <div className="header-inner">
        <a href="#hero" className="brand-lockup" aria-label="BhashaBridge Home">
          <div className="brand-mark" aria-hidden="true">
            <span className="mark-node node-a" />
            <span className="mark-vector" />
            <span className="mark-node node-b" />
          </div>
          <div className="brand-text">
            <div className="brand-title">
              <span className="brand-accent">BHASHA</span>
              <span className="brand-main">BRIDGE</span>
            </div>
            <span className="brand-sub">LANGUAGE OBSERVATORY · 2.0</span>
          </div>
        </a>

        <div className="header-status-indicator" title="Current API & Research Evaluation Status">
          <span className={`status-pulse ${isBlocked ? 'pulse-blocked' : 'pulse-ready'}`} />
          <span className="status-label">{statusLabel}</span>
          <span className="status-ref">BB-2.0</span>
        </div>

        <nav id="primary-nav" className={`nav-menu ${menuOpen ? 'is-open' : ''}`} aria-label="Main navigation">
          {NAV_LINKS.map((link) => (
            <a
              key={link.id}
              href={`#${link.id}`}
              className="nav-link"
              onClick={() => setMenuOpen(false)}
            >
              {link.label}
            </a>
          ))}
          <a
            href="#lab"
            className="nav-cta"
            onClick={() => setMenuOpen(false)}
          >
            Launch Lab <span className="cta-arrow" aria-hidden="true">→</span>
          </a>
        </nav>

        <button
          className="mobile-toggle"
          type="button"
          aria-expanded={menuOpen}
          aria-controls="primary-nav"
          onClick={() => setMenuOpen(!menuOpen)}
        >
          <span className="sr-only">{menuOpen ? 'Close navigation' : 'Open navigation'}</span>
          <span className="toggle-icon" aria-hidden="true">{menuOpen ? '✕' : '☰'}</span>
        </button>
      </div>
    </header>
  );
}
