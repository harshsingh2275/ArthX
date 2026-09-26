/**
 * ArthX API Client — all backend endpoints
 */
const RAW_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';
// Strip trailing slashes to prevent invalid double-slash paths (e.g. host//api/...)
const API_BASE = RAW_BASE.replace(/\/+$/, '');

async function request(path, options = {}) {
  const cleanPath = path.startsWith('/') ? path : `/${path}`;
  const res = await fetch(`${API_BASE}${cleanPath}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(`[${res.status}] ${cleanPath}: ${text}`);
  }
  return res.json();
}

// ── Dataset registry ─────────────────────────────────────────
export const fetchDatasets = () => request('/api/datasets');

// ── Analysis pipeline ────────────────────────────────────────
export const runAnalysis = (datasetId = null) => {
  const qs = datasetId ? `?dataset=${encodeURIComponent(datasetId)}` : '';
  return request(`/api/analysis/run${qs}`, { method: 'POST' });
};

// ── Dashboard read endpoints ─────────────────────────────────
export const fetchAnomalies     = () => request('/api/anomalies');
export const fetchForecast      = () => request('/api/forecast');
export const fetchInvoiceIssues = () => request('/api/invoices/issues');

// ── Assistant ────────────────────────────────────────────────
export const queryAssistant = (question) =>
  request('/api/assistant/query', {
    method: 'POST',
    body: JSON.stringify({ question }),
  });
