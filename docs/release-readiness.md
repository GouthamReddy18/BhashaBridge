# Engineering release readiness — Phase 26

Verification recorded 2026-10-22 at HEAD `653fb3b33f56e572545fcbbf36c5de8bd23fa8e5`. This checkpoint records software verification separately from research readiness.

## Scope

- Four-condition experiment infrastructure, offline evaluators, report validation, human-rating workflow, and the analysis frontend were audited as existing repository components.
- The frontend includes an additive read-only `GET /api/v1/research/readiness` endpoint/dashboard. This endpoint does not execute evaluation or contact a translation provider.
- The sample dataset remains a synthetic illustrative draft. No research output or human rating is represented as a result.

## Research gates

Research execution remains blocked pending a licensed and human-reviewed benchmark, qualified linguistic resources for the applicable conditions, authorized provider configuration and real outputs, and human semantic ratings. These gates cannot be satisfied by software tests or frontend smoke checks.

## Verification record

Commands below were run from the repository root except the frontend build (from `frontend/`).

| Check | Exit | Result |
|---|---:|---|
| Full backend `unittest` suite | 0 | 274 tests passed. Includes labeled synthetic evaluator CLI test; fixture report remains test-only and validates structurally. |
| Draft structural validation | 0 | 16 records, 0 structural errors, 16 unreviewed-draft warnings. |
| Draft evaluation-readiness check | 1 | Expected blocked status: 144 readiness errors and 16 warnings. Dataset was not modified. |
| Four-condition evaluator `--help` | 0 | Required arguments and no-overwrite output behavior printed. |
| Four-condition labeled synthetic CLI smoke | 1 expected | The suite's dedicated synthetic JSONL CLI test confirms no score is produced and report validation exits 0. A test-only report is not research evidence. |
| Frontend production build | 0 | Vite 8.3.5 built 15 modules. Initial sandboxed attempt exited 1 on system Node path access; the authorized local retry exited 0. |
| Local API/frontend smoke | 0 | Vite page HTTP 200; readiness returned `not_ready`, 16 records, 144 blockers; analyze returned 4 tokens and `translation=disabled`. |
| `git diff --check` | 0 | No whitespace errors at the time of the final review; rerun after this edit before delivery. |

## Remaining engineering limitations

Real-browser visual and device QA was not available in the current environment. The worktree's `.vscode/` directory is unrelated and must remain untracked. No dataset or model was downloaded, no provider call was made, and no evaluation score or human rating was generated from project data. Record the final Git branch/upstream relationship and commit status separately from this verification checkpoint.

