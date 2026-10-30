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
        <a href="#hero" className="brand-lockup" aria-label="LipiPrism Home">
          <div className="brand-mark prism-mark" aria-hidden="true">
            <svg
              width="24"
              height="24"
              viewBox="0 0 24 24"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
              className="prism-svg"
            >
              <path d="M2 13L8 12" stroke="#E8E9DB" strokeWidth="1.6" strokeLinecap="round" />
              <polygon
                points="12,4 5.5,19 18.5,19"
                stroke="#82C9C0"
                strokeWidth="1.6"
                fill="rgba(130, 201, 192, 0.12)"
                strokeLinejoin="round"
              />
              <path d="M14 11.5L22 7.5" stroke="#D5F36A" strokeWidth="1.6" strokeLinecap="round" />
              <path d="M14.5 13.5L22 13.5" stroke="#82C9C0" strokeWidth="1.6" strokeLinecap="round" />
              <path d="M14 15.5L22 19.5" stroke="#FF7856" strokeWidth="1.6" strokeLinecap="round" />
            </svg>
          </div>
          <div className="brand-text">
            <div className="brand-title">
              <span className="brand-accent">LIPI</span>
              <span className="brand-main">PRISM</span>
            </div>
            <span className="brand-sub">THE LANGUAGE OBSERVATORY</span>
          </div>
        </a>

        <div className="header-status-indicator" title="Current API & Research Evaluation Status">
          <span className={`status-pulse ${isBlocked ? 'pulse-blocked' : 'pulse-ready'}`} />
          <span className="status-label">{statusLabel}</span>
          <span className="status-ref">LP-OBS</span>
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
