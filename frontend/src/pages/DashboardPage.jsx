/**
 * DashboardPage — main workspace canvas.
 * Assembles: KPI row → (ForecastChart + AnomalyTable) → AssistantPanel
 * Fetches live data from Phase 3 endpoints.
 */
import React, { useState, useEffect, useCallback } from 'react';
import {
  fetchAnomalies,
  fetchForecast,
  fetchInvoiceIssues,
  fetchDatasets,
  runAnalysis,
} from '../api/client';
import Sidebar         from '../components/Sidebar';
import TopNav          from '../components/TopNav';
import KpiCard         from '../components/KpiCard';
import ForecastChart   from '../components/ForecastChart';
import AnomalyTable    from '../components/AnomalyTable';
import AssistantPanel  from '../components/AssistantPanel';

function fmt(n, opts = {}) {
  if (n == null || isNaN(n)) return '—';
  return n.toLocaleString('en-US', { minimumFractionDigits: opts.decimals ?? 0, maximumFractionDigits: opts.decimals ?? 0, ...opts });
}
function fmtMoney(n) {
  if (n == null) return '—';
  const abs = Math.abs(n);
  if (abs >= 1_000_000) return `$${(n / 1_000_000).toFixed(2)}M`;
  if (abs >= 1_000)     return `$${(n / 1_000).toFixed(1)}k`;
  return `$${n.toFixed(2)}`;
}

export default function DashboardPage() {
  const [anomalies,     setAnomalies]     = useState([]);
  const [forecast,      setForecast]      = useState({});
  const [invoiceIssues, setInvoiceIssues] = useState([]);
  const [loadingData,   setLoadingData]   = useState(true);
  const [runningAnalysis, setRunningAnalysis] = useState(false);
  const [error,         setError]         = useState(null);
  // Dataset switcher state
  const [datasets,      setDatasets]      = useState([]);
  const [activeDataset, setActiveDataset] = useState(null); // null = default/current data

  const loadDashboardData = useCallback(async () => {
    setLoadingData(true);
    setError(null);
    try {
      const [an, fc, inv] = await Promise.all([
        fetchAnomalies(),
        fetchForecast(),
        fetchInvoiceIssues(),
      ]);
      // /api/anomalies returns a direct array
      setAnomalies(Array.isArray(an) ? an : (an?.anomalies ?? []));
      setForecast(fc ?? {});
      // /api/invoices/issues returns a direct array
      setInvoiceIssues(Array.isArray(inv) ? inv : (inv?.issues ?? []));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoadingData(false);
    }
  }, []);

  // Load dataset registry on mount
  useEffect(() => {
    fetchDatasets()
      .then(res => setDatasets(res?.datasets ?? []))
      .catch(() => {}); // non-fatal
  }, []);

  // Auto-load on mount
  useEffect(() => { loadDashboardData(); }, [loadDashboardData]);

  const handleRunAnalysis = async (datasetId = null) => {
    setRunningAnalysis(true);
    setError(null);
    try {
      await runAnalysis(datasetId);
      if (datasetId) setActiveDataset(datasetId);
      await loadDashboardData();
    } catch (err) {
      setError(err.message);
    } finally {
      setRunningAnalysis(false);
    }
  };

  // ── KPI computed values ──────────────────────────────────────
  const flaggedCount    = anomalies.length;
  const flaggedAmount   = anomalies.reduce((s, a) => s + (a.amount ?? 0), 0);
  const netPosition     = (() => {
    const fc = forecast?.forecast;
    if (!fc?.length) return null;
    const last = [...fc].reverse().find(d => d.predicted_net_flow != null);
    return last?.predicted_net_flow;
  })();
  const invoiceCount    = invoiceIssues.length;
  const dupCount        = invoiceIssues.filter(i => i.issue_type === 'DUPLICATE_INVOICE').length;
  const missingPoCount  = invoiceIssues.filter(i => i.issue_type === 'MISSING_PO_REFERENCE').length;

  const kpiLoading = loadingData;

  return (
    <div style={{ display: 'flex', width: '100%', minHeight: '100vh' }}>
      <Sidebar />

      {/* Main wrapper — offset by sidebar width */}
      <div style={{ paddingLeft: 64, width: '100%', display: 'flex', flexDirection: 'column', minWidth: 0 }}>
        <TopNav
          onRunAnalysis={handleRunAnalysis}
          running={runningAnalysis}
          datasets={datasets}
          activeDataset={activeDataset ?? (datasets[0]?.id ?? null)}
        />

        {/* Sub-navigation tab bar */}
        <div style={{
          height: 40,
          background: '#F4F0EA',
          borderBottom: '2.5px solid #000',
          display: 'flex', alignItems: 'center',
          padding: '0 20px', gap: 8,
        }}>
          <nav style={{ display: 'flex', alignItems: 'center', height: '100%', gap: 8 }}>
            {['Intelligence & Overview', 'Anomaly Inspector', 'Forecast Engine', 'Audit Trail'].map((tab, i) => (
              <a
                key={tab}
                href="#"
                onClick={e => e.preventDefault()}
                style={{
                  display: 'flex', alignItems: 'center',
                  height: 28, padding: '0 14px',
                  fontFamily: 'JetBrains Mono, monospace',
                  fontSize: 11, fontWeight: i === 0 ? 900 : 700,
                  background: i === 0 ? '#FFE600' : '#F4F0EA',
                  color: '#000',
                  border: '2px solid #000',
                  boxShadow: '2px 2px 0px #000',
                  textDecoration: 'none',
                  whiteSpace: 'nowrap',
                }}
              >{tab}</a>
            ))}
          </nav>
        </div>

        {/* Error banner */}
        {error && (
          <div style={{
            padding: '10px 20px',
            background: '#FF4365', color: '#fff',
            borderBottom: '2px solid #000',
            fontFamily: 'JetBrains Mono, monospace',
            fontSize: 12, fontWeight: 700,
            display: 'flex', alignItems: 'center', gap: 10,
          }}>
            <span className="material-symbols-outlined" style={{ fontSize: 18 }}>error</span>
            {error}
            <button
              onClick={() => setError(null)}
              style={{ marginLeft: 'auto', background: '#fff', color: '#FF4365', border: '1px solid #fff', padding: '2px 10px', boxShadow: 'none' }}
            >Dismiss</button>
          </div>
        )}

        {/* Main canvas */}
        <main style={{ flex: 1, padding: 20, paddingBottom: 40, display: 'flex', flexDirection: 'column', gap: 20 }}>

          {/* ── 1. KPI Row ── */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
            gap: 16,
          }}>
            <KpiCard
              accentColor="#FF4365"
              iconName="warning"
              iconBg="#FFE600"
              label="Flagged Anomalies"
              value={kpiLoading ? '…' : String(flaggedCount)}
              loading={kpiLoading}
              subLeft={`Critical: ${anomalies.filter(a => a.risk_score >= 0.85).length}`}
              subRight={
                <span style={{ background: '#FFE600', color: '#000', padding: '1px 8px', border: '1px solid #000', boxShadow: '1px 1px 0px #000', fontWeight: 900, fontFamily: 'JetBrains Mono, monospace', fontSize: 10 }}>
                  Warning: {anomalies.filter(a => a.risk_score >= 0.6 && a.risk_score < 0.85).length}
                </span>
              }
            />
            <KpiCard
              accentColor="#FFE600"
              iconName="crisis_alert"
              iconBg="#FF4365"
              label="Flagged Amount"
              value={kpiLoading ? '…' : fmtMoney(flaggedAmount)}
              loading={kpiLoading}
              subLeft={`Across ${anomalies.length} transactions`}
              subRight={null}
            />
            <KpiCard
              accentColor="#00E599"
              iconName="stacked_line_chart"
              iconBg="#00E599"
              label="30-Day Forecast Net"
              value={kpiLoading ? '…' : (netPosition != null ? fmtMoney(netPosition) : '—')}
              loading={kpiLoading}
              subLeft={forecast?.trend_summary ? forecast.trend_summary.slice(0, 40) + '…' : 'Run analysis for forecast'}
              subRight={null}
            />
            <KpiCard
              accentColor="#38BDF8"
              iconName="receipt_long"
              iconBg="#38BDF8"
              label="Invoice Issues"
              value={kpiLoading ? '…' : String(invoiceCount)}
              loading={kpiLoading}
              subLeft={`Duplicates: ${dupCount} · Missing PO: ${missingPoCount}`}
              subRight={null}
            />
          </div>

          {/* ── 2. Chart + Table row ── */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: '1fr',
            gap: 16,
          }}>
            {/* Cash Flow Chart — full width on smaller, 7/12 on xl */}
            <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0,7fr) minmax(0,5fr)', gap: 16 }}
              className="chart-table-grid">
              <ForecastChart
                forecast={forecast}
                trendSummary={forecast?.trend_summary}
                loading={loadingData}
              />
              <AnomalyTable
                anomalies={anomalies}
                loading={loadingData}
              />
            </div>
          </div>

          {/* ── 3. Assistant Panel ── */}
          <AssistantPanel />

        </main>

        {/* Footer */}
        <footer style={{
          height: 28,
          background: '#fff',
          borderTop: '2.5px solid #000',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '0 20px',
          fontFamily: 'JetBrains Mono, monospace',
          fontSize: 11, fontWeight: 700,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <span>Branch: <span style={{ background: '#FFE600', padding: '1px 6px', border: '1px solid #000', fontWeight: 900 }}>main</span></span>
            <span style={{ color: '#888' }}>|</span>
            <span>UTF-8</span>
            <span style={{ color: '#888' }}>|</span>
            <span>Models: <span style={{ background: '#00E599', padding: '1px 6px', border: '1px solid #000', fontWeight: 900 }}>Groq 70B Active</span></span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <span>Anomalies: <strong>{flaggedCount}</strong></span>
            <span style={{ color: '#888' }}>|</span>
            <span>Invoices Flagged: <strong>{invoiceCount}</strong></span>
          </div>
        </footer>

        {/* Responsive grid style */}
        <style>{`
          @media (max-width: 1100px) {
            .chart-table-grid {
              grid-template-columns: 1fr !important;
            }
          }
        `}</style>
      </div>
    </div>
  );
}
