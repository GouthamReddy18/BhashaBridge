import React from 'react';

export function StatusBadge({ status, label = null }) {
  const normStatus = String(status || 'unknown').toLowerCase();
  const text = label || normStatus.replaceAll('_', ' ');

  let tone = 'caution';
  if (['ready', 'available', 'success', 'configured', 'resolved', 'active'].includes(normStatus)) {
    tone = 'positive';
  } else if (['failed', 'invalid', 'blocked', 'not_ready', 'disabled'].includes(normStatus)) {
    tone = 'negative';
  } else if (['optional', 'fixture', 'opt_in', 'unreviewed', 'degraded'].includes(normStatus)) {
    tone = 'caution';
  }

  return (
    <span className={`status-badge tone-${tone}`}>
      <span className="badge-dot" aria-hidden="true" />
      <span className="badge-text">{text}</span>
    </span>
  );
}

export function ScriptBadge({ label }) {
  const norm = String(label || 'UNKNOWN').toUpperCase();
  let type = 'unknown';
  if (norm.includes('ROMANIZED')) type = 'romanized';
  else if (norm.includes('SCRIPT')) type = 'script';
  else if (norm.includes('ENGLISH')) type = 'english';
  else if (norm.includes('PUNCTUATION') || norm.includes('NUMBER')) type = 'syntax';

  return (
    <span className={`script-badge type-${type}`}>
      {norm.replaceAll('_', ' ')}
    </span>
  );
}

export function CoordinateChip({ children }) {
  return (
    <span className="coordinate-chip">
      <span className="coord-bracket">[</span>
      {children}
      <span className="coord-bracket">]</span>
    </span>
  );
}
