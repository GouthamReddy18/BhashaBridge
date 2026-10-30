import React, { useState } from 'react';
import { CONDITION_DETAILS } from '../constants';
import { StatusBadge, CoordinateChip } from './ui/Badge';

export function ResearchObservatory({ readiness, onRefresh, loading }) {
  const [selectedDatasetKey, setSelectedDatasetKey] = useState('pilot'); // 'pilot' | 'illustrative'

  // Pick dataset object
  const activeDataset = (selectedDatasetKey === 'pilot' && readiness?.pilot_dataset)
    ? readiness.pilot_dataset
    : readiness?.dataset;

  const isResearchReady = readiness?.research_ready || false;

  return (
    <section id="observatory" className="observatory-section">
      <div className="section-header-block">
        <div className="section-kicker">
          <span className="kicker-index">03</span>
          <span className="kicker-line" />
          <span className="kicker-title">METRIC MONITORING & TELEMETRY</span>
        </div>
        <div className="title-with-action">
          <div>
            <h2 className="section-h2">
              Research Observatory: <span className="text-tint">Live Verification Gates</span>
            </h2>
            <p className="section-sub">
              Live telemetry connected directly to the local backend readiness API. Software readiness
              is reported separately from scientific research eligibility.
            </p>
          </div>
          {onRefresh && (
            <button
              type="button"
              className="btn btn-outline btn-sm refresh-btn"
              onClick={onRefresh}
              disabled={loading}
              title="Poll latest readiness status from backend"
            >
              {loading ? 'Polling API...' : '↻ Refresh Gates'}
            </button>
          )}
        </div>
      </div>

      {/* Main Readiness Status Banner */}
      <div className={`readiness-telemetry-banner ${isResearchReady ? 'state-ready' : 'state-blocked'}`}>
        <div className="banner-left">
          <span className="banner-indicator" />
          <div className="banner-text-group">
            <span className="banner-kicker">RESEARCH EVALUATION GATE STATUS</span>
            <h3 className="banner-state-title">
              {isResearchReady ? 'READY FOR CONTROLLED EVALUATION' : 'RESEARCH EVALUATION IS STRICTLY BLOCKED'}
            </h3>
            <p className="banner-state-desc">
              {isResearchReady
                ? 'All dataset review stages, reference translations, and qualified resources are present.'
                : 'Evaluation readiness checker enforces exit code 1. Benchmarking is blocked until genuine human review and reference translations are supplied.'}
            </p>
          </div>
        </div>
        <div className="banner-right">
          <CoordinateChip>PROTOCOL::STAGE_GATE</CoordinateChip>
        </div>
      </div>

      {/* Observatory Bento Grid */}
      <div className="observatory-grid">
        {/* Card 1: Dataset Status & Blocker Categories */}
        <div className="obs-card dataset-card">
          <div className="obs-card-header">
            <span className="obs-card-title">DATASET READINESS MONITOR</span>
            {activeDataset && <StatusBadge status={activeDataset.evaluation_status} />}
          </div>

          {/* Dataset Switcher */}
          <div className="dataset-switch-bar">
            {readiness?.pilot_dataset && (
              <button
                type="button"
                className={`switch-tab ${selectedDatasetKey === 'pilot' ? 'is-active' : ''}`}
                onClick={() => setSelectedDatasetKey('pilot')}
              >
                Pilot v0.1 ({readiness.pilot_dataset.records_examined} records)
              </button>
            )}
            {readiness?.dataset && (
              <button
                type="button"
                className={`switch-tab ${selectedDatasetKey === 'illustrative' ? 'is-active' : ''}`}
                onClick={() => setSelectedDatasetKey('illustrative')}
              >
                Illustrative Draft ({readiness.dataset.records_examined} records)
              </button>
            )}
          </div>

          {activeDataset ? (
            <div className="dataset-metrics-wrap">
              <div className="dataset-file-info">
                <span className="file-name mono">{activeDataset.name}</span>
                <span className="file-format-badge">
                  Format: {activeDataset.structural_status.toUpperCase()}
                </span>
              </div>

              <div className="count-counters-row">
                <div className="counter-box">
                  <span className="counter-num">{activeDataset.records_examined}</span>
                  <span className="counter-label">Total Records</span>
                </div>
                <div className="counter-box">
                  <span className="counter-num text-success">{activeDataset.structural_errors}</span>
                  <span className="counter-label">Structural Errors</span>
                </div>
                <div className="counter-box counter-blockers">
                  <span className="counter-num text-danger">{activeDataset.blocking_errors}</span>
                  <span className="counter-label">Readiness Blockers</span>
                </div>
              </div>

              <div className="blockers-section">
                <span className="blockers-header">Active Blocker Categories:</span>
                <ul className="blockers-list">
                  {activeDataset.blocker_categories.map((cat, i) => (
                    <li key={i}>
                      <span className="blocker-bullet">✕</span>
                      <span>{cat}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          ) : (
            <div className="card-loading">Connecting to dataset diagnostics...</div>
          )}
        </div>

        {/* Card 2: 4-Condition Cumulative Cascade */}
        <div className="obs-card conditions-card">
          <div className="obs-card-header">
            <span className="obs-card-title">FOUR-CONDITION EVALUATION ARMS</span>
            <CoordinateChip>FOUR_CONDITION.V1</CoordinateChip>
          </div>
          <div className="conditions-track">
            {(readiness?.conditions || [
              { id: 'direct_v1', status: 'blocked', reason: 'Requires an eligible reviewed dataset.' },
              { id: 'normalized_v1', status: 'blocked', reason: 'No qualified linguistic normalizer is registered.' },
              { id: 'transliterated_v1', status: 'blocked', reason: 'Reviewed transliteration resource required.' },
              { id: 'ambiguity_aware_v1', status: 'blocked', reason: 'Contextual transformation rules required.' },
            ]).map((cond, idx) => {
              const meta = CONDITION_DETAILS[cond.id] || {};
              return (
                <div key={cond.id} className="condition-row">
                  <div className="cond-col-id">
                    <span className="cond-seq">0{idx + 1}</span>
                    <strong className="cond-name">{meta.title || cond.id}</strong>
                    <code className="cond-code">{cond.id}</code>
                  </div>
                  <div className="cond-col-reason">
                    <p className="cond-desc">{meta.desc}</p>
                    <span className="cond-block-reason">
                      <strong>Gate Reason:</strong> {cond.reason}
                    </span>
                  </div>
                  <div className="cond-col-status">
                    <StatusBadge status={cond.status} />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Card 3: Linguistic Resource Qualification */}
        <div className="obs-card resources-card">
          <div className="obs-card-header">
            <span className="obs-card-title">TRANSFORMATION RESOURCE INVENTORY</span>
            <span className="obs-meta-pill">UNQUALIFIED</span>
          </div>
          <ul className="resources-inventory">
            {(readiness?.resources || [
              { id: 'normalizer', status: 'missing', detail: 'Whitespace collapsing only; not linguistic normalizer.' },
              { id: 'transliterator', status: 'not_configured', detail: 'Transliteration adapter disabled.' },
              { id: 'contextual_transformer', status: 'illustrative_only', detail: 'English bank rule is a fixture.' },
            ]).map((res) => (
              <li key={res.id} className="resource-item">
                <div className="res-top">
                  <strong className="res-name">{res.id.replaceAll('_', ' ').toUpperCase()}</strong>
                  <StatusBadge status={res.status} />
                </div>
                <p className="res-detail">{res.detail}</p>
              </li>
            ))}
          </ul>
        </div>

        {/* Card 4: Evaluation Reports Integrity */}
        <div className="obs-card reports-card">
          <div className="obs-card-header">
            <span className="obs-card-title">EVALUATION REPORT CATALOG</span>
            <StatusBadge status={readiness?.evaluation_reports?.status || 'not_catalogued'} />
          </div>
          <div className="reports-content">
            <p className="reports-desc">
              {readiness?.evaluation_reports?.detail ||
                'Evaluation artifacts are explicit CLI inputs; no persistent report catalog is configured.'}
            </p>
            <div className="integrity-note">
              <strong>Scientific Verification Policy:</strong>
              <p>
                This observatory renders zero synthetic BLEU-4 or chrF scores. Surface overlap metrics
                are computed exclusively via offline validated CLI scripts once verified human reference
                translations exist.
              </p>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
