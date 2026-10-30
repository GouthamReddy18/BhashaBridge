/**
 * BhashaBridge API client.
 * Connects to FastAPI backend routes:
 * - POST /api/v1/analyze
 * - GET  /api/v1/research/readiness
 */
import { API_BASE } from './constants';

export class ApiError extends Error {
  constructor(message, status = 0, detail = null) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
  }
}

export async function requestJson(path, options = {}) {
  const url = `${API_BASE}${path}`;
  const response = await fetch(url, options);

  if (!response.ok) {
    let message = `Request failed (HTTP ${response.status}).`;
    let detail = null;
    try {
      const body = await response.json();
      detail = body.detail;
      if (Array.isArray(detail)) {
        message = detail.map((d) => d.msg || d).join('; ') || 'Invalid input format.';
      } else if (typeof detail === 'string') {
        message = detail;
      }
    } catch {
      // Non-JSON response body
    }
    throw new ApiError(message, response.status, detail);
  }

  return response.json();
}

export async function analyzeText(text, translate = false, signal = null) {
  return requestJson('/api/v1/analyze', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
    },
    body: JSON.stringify({ text, translate }),
    signal,
  });
}

export async function fetchResearchReadiness(dataset = null, signal = null) {
  const query = dataset ? `?dataset=${encodeURIComponent(dataset)}` : '';
  return requestJson(`/api/v1/research/readiness${query}`, { signal });
}
