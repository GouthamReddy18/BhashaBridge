import React, { useState } from 'react';
import { PIPELINE_STAGES } from '../constants';
import { StatusBadge, CoordinateChip } from './ui/Badge';

export function PipelineExplorer() {
  const [activeStageIndex, setActiveStageIndex] = useState(0);
  const activeStage = PIPELINE_STAGES[activeStageIndex];

  return (
    <section id="pipeline" className="pipeline-section">
      <div className="section-header-block">
        <div className="section-kicker">
          <span className="kicker-index">02</span>
          <span className="kicker-line" />
          <span className="kicker-title">ARCHITECTURAL BLUEPRINT</span>
        </div>
        <h2 className="section-h2">
          Interactive Processing Pipeline: <span className="text-tint">8 Traceable Stages</span>
        </h2>
        <p className="section-sub">
          Explore the modular transformation pipeline. Every linguistic step preserves original
          evidence, tracks applied operations, and enforces strict abstention boundaries.
        </p>
      </div>

      <div className="pipeline-layout">
        {/* Stages Timeline Navigation */}
        <div className="pipeline-timeline" role="tablist" aria-label="Pipeline Stages">
          {PIPELINE_STAGES.map((stage, idx) => {
            const isActive = activeStageIndex === idx;
            return (
              <button
                key={stage.index}
                role="tab"
                aria-selected={isActive}
                className={`timeline-node ${isActive ? 'is-active' : ''}`}
                onClick={() => setActiveStageIndex(idx)}
              >
                <div className="node-marker">
                  <span className="node-num">{stage.index}</span>
                  <span className={`node-dot dot-${stage.status}`} />
                </div>
                <div className="node-info">
                  <span className="node-category">{stage.category}</span>
                  <strong className="node-name">{stage.name}</strong>
                  <span className="node-status-text">{stage.statusLabel}</span>
                </div>
              </button>
            );
          })}
        </div>

        {/* Detailed Stage Inspector Panel */}
        <div className="pipeline-detail-card" role="tabpanel">
          <div className="stage-detail-header">
            <div className="stage-title-wrap">
              <CoordinateChip>STAGE::{activeStage.index}</CoordinateChip>
              <h3 className="stage-title">{activeStage.name}</h3>
              <span className="stage-cat-tag">{activeStage.category}</span>
            </div>
            <StatusBadge status={activeStage.status} label={activeStage.statusLabel} />
          </div>

          <div className="stage-detail-body">
            <div className="detail-segment">
              <h4>Linguistic & Computational Function</h4>
              <p>{activeStage.description}</p>
            </div>

            <div className="detail-segment safeguard-segment">
              <h4>
                <span className="shield-icon" aria-hidden="true">⛊</span>
                Research Integrity & Invariant Safeguards
              </h4>
              <p>{activeStage.safeguards}</p>
            </div>

            <div className="stage-state-breakdown">
              <div className="breakdown-card">
                <span className="breakdown-title">Operational Contract</span>
                <span className="breakdown-value">
                  {activeStage.status === 'active' && 'Verified in backend test suite (315 tests passing)'}
                  {activeStage.status === 'optional' && 'Decoupled compatibility seam; lazy initialization only'}
                  {activeStage.status === 'fixture' && 'Deterministic test fixture; non-generalizing heuristic'}
                  {activeStage.status === 'opt_in' && 'Protected by explicit caller opt-in flag and auth key'}
                  {activeStage.status === 'blocked' && 'Readiness gate strictly enforced (exits code 1 when unreviewed)'}
                </span>
              </div>
            </div>
          </div>

          <div className="stage-detail-footer">
            <div className="stage-nav-controls">
              <button
                type="button"
                className="btn btn-outline btn-sm"
                disabled={activeStageIndex === 0}
                onClick={() => setActiveStageIndex((prev) => Math.max(0, prev - 1))}
              >
                ← Previous Stage
              </button>
              <span className="stage-counter">
                {activeStageIndex + 1} of {PIPELINE_STAGES.length}
              </span>
              <button
                type="button"
                className="btn btn-outline btn-sm"
                disabled={activeStageIndex === PIPELINE_STAGES.length - 1}
                onClick={() => setActiveStageIndex((prev) => Math.min(PIPELINE_STAGES.length - 1, prev + 1))}
              >
                Next Stage →
              </button>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
