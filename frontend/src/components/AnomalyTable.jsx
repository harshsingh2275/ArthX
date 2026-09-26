/**
 * AnomalyTable — Risk Evaluation Queue.
 * Shows anomalies with risk score badge, vendor, amount, explanation inline.
 * Data: GET /api/anomalies
 */
import React, { useState } from 'react';

function RiskBadge({ score }) {
  const pct = Math.round(score * 100);
  let bg, color;
  if (pct >= 85)      { bg = '#FF4365'; color = '#fff'; }
  else if (pct >= 60) { bg = '#FFE600'; color = '#000'; }
  else                { bg = '#00E599'; color = '#000'; }

  return (
    <span style={{
      fontFamily: 'JetBrains Mono, monospace',
      fontSize: 12, fontWeight: 900,
      background: bg, color,
      border: '2px solid #000',
      padding: '2px 8px',
      boxShadow: '2px 2px 0px #000',
      display: 'inline-block',
    }}>{pct}</span>
  );
}

function RiskDot({ score }) {
  const pct = score * 100;
  let bg;
  if (pct >= 85)      bg = '#FF4365';
  else if (pct >= 60) bg = '#FFE600';
  else                bg = '#00E599';
  return (
    <span style={{
      display: 'inline-block', width: 10, height: 10,
      background: bg, border: '1px solid #000',
      flexShrink: 0,
    }} />
  );
}

function fmt(n) {
  return '$' + Number(n).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export default function AnomalyTable({ anomalies = [], loading }) {
  const [expanded, setExpanded] = useState(null);

  const high   = anomalies.filter(a => a.risk_score >= 0.85).length;
  const medium = anomalies.filter(a => a.risk_score >= 0.60 && a.risk_score < 0.85).length;

  return (
    <div style={{
      background: '#fff',
      border: '2.5px solid #000',
      boxShadow: '4px 4px 0px #000',
      display: 'flex', flexDirection: 'column',
      minHeight: 340,
    }}>
      {/* Header */}
      <div style={{
        height: 44, padding: '0 16px',
        borderBottom: '2px solid #000',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        background: '#F4F0EA',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span className="material-symbols-outlined" style={{ fontSize: 19, color: '#FF4365', fontWeight: 700 }}>
            shield_with_heart
          </span>
          <span style={{
            fontFamily: 'Space Grotesk, sans-serif',
            fontSize: 11, fontWeight: 900, textTransform: 'uppercase', letterSpacing: '0.06em',
          }}>Risk Evaluation Queue</span>
          <span style={{
            fontFamily: 'JetBrains Mono, monospace',
            fontSize: 11, fontWeight: 900,
            background: '#000', color: '#FFE600',
            padding: '2px 8px',
            boxShadow: '1px 1px 0px #000',
          }}>{loading ? '…' : `${anomalies.length} items`}</span>
        </div>
      </div>

      {/* Table */}
      <div style={{ flex: 1, overflowX: 'auto', overflowY: 'auto' }}>
        {loading ? (
          <div style={{ padding: 24, textAlign: 'center', fontFamily: 'JetBrains Mono, monospace', fontSize: 12, color: '#666' }}>
            Loading anomalies…
          </div>
        ) : anomalies.length === 0 ? (
          <div style={{ padding: 24, textAlign: 'center', fontFamily: 'JetBrains Mono, monospace', fontSize: 12, color: '#666' }}>
            No anomalies detected. Run analysis first.
          </div>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
            <thead>
              <tr style={{ background: '#000', color: '#fff', fontFamily: 'Space Grotesk, sans-serif', fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                <th style={{ padding: '8px 12px', fontWeight: 900 }}>Vendor / Entity</th>
                <th style={{ padding: '8px 8px', fontWeight: 900, textAlign: 'right' }}>Amount</th>
                <th style={{ padding: '8px 8px', fontWeight: 900, textAlign: 'center' }}>Score</th>
                <th style={{ padding: '8px 12px', fontWeight: 900 }}>Context &amp; Explanation</th>
              </tr>
            </thead>
            <tbody>
              {anomalies.map((a, i) => (
                <React.Fragment key={a.transaction_id ?? i}>
                  <tr
                    style={{
                      borderBottom: '2px solid #000',
                      cursor: 'pointer',
                      background: expanded === i ? '#FFFDE6' : '#fff',
                    }}
                    onMouseEnter={e => { if (expanded !== i) e.currentTarget.style.background = '#FFFDE6'; }}
                    onMouseLeave={e => { if (expanded !== i) e.currentTarget.style.background = '#fff'; }}
                    onClick={() => setExpanded(expanded === i ? null : i)}
                  >
                    {/* Vendor */}
                    <td style={{ padding: '10px 12px', fontWeight: 700, whiteSpace: 'nowrap' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <RiskDot score={a.risk_score} />
                        <span style={{ fontFamily: 'Space Grotesk, sans-serif', fontSize: 12.5, fontWeight: 800 }}>
                          {a.vendor}
                        </span>
                      </div>
                      <div style={{
                        fontFamily: 'JetBrains Mono, monospace', fontSize: 10,
                        color: '#444', fontWeight: 500, paddingLeft: 18, marginTop: 2,
                      }}>
                        ID: #{a.transaction_id}
                      </div>
                    </td>
                    {/* Amount */}
                    <td style={{
                      padding: '10px 8px',
                      fontFamily: 'JetBrains Mono, monospace',
                      fontSize: 12, fontWeight: 900,
                      textAlign: 'right', whiteSpace: 'nowrap',
                    }}>
                      {a.amount != null ? fmt(a.amount) : '—'}
                    </td>
                    {/* Score badge */}
                    <td style={{ padding: '10px 8px', textAlign: 'center', whiteSpace: 'nowrap' }}>
                      <RiskBadge score={a.risk_score} />
                    </td>
                    {/* Explanation */}
                    <td style={{
                      padding: '10px 12px',
                      fontFamily: 'Space Grotesk, sans-serif',
                      fontSize: 11, fontWeight: 500, lineHeight: 1.4,
                      maxWidth: 280,
                    }}>
                      <div style={{ fontWeight: 700, fontSize: 10, color: '#555', marginBottom: 2, fontFamily: 'JetBrains Mono, monospace', letterSpacing: '0.06em' }}>
                        {a.reason_code}
                      </div>
                      <div>{a.explanation || a.trigger_metric || '—'}</div>
                    </td>
                  </tr>
                  {/* Expanded row: full explanation + impact */}
                  {expanded === i && (
                    <tr style={{ background: '#FFFDE6', borderBottom: '2px solid #000' }}>
                      <td colSpan={4} style={{ padding: '12px 20px' }}>
                        <div style={{
                          borderLeft: '3px solid #FFE600',
                          paddingLeft: 12,
                          fontFamily: 'Space Grotesk, sans-serif',
                          fontSize: 12,
                        }}>
                          <div style={{ fontWeight: 700, marginBottom: 4, fontFamily: 'JetBrains Mono, monospace', fontSize: 10, letterSpacing: '0.06em' }}>
                            TRIGGER METRIC
                          </div>
                          <div style={{ marginBottom: 8 }}>{a.trigger_metric || '—'}</div>
                          {a.explanation && (
                            <>
                              <div style={{ fontWeight: 700, marginBottom: 4, fontFamily: 'JetBrains Mono, monospace', fontSize: 10, letterSpacing: '0.06em' }}>
                                AI EXPLANATION
                              </div>
                              <div style={{ color: '#222', lineHeight: 1.5 }}>{a.explanation}</div>
                            </>
                          )}
                          {a.impact_on_30d_forecast != null && (
                            <div style={{
                              marginTop: 12, padding: '8px 12px',
                              background: '#000', color: '#FFE600',
                              fontFamily: 'JetBrains Mono, monospace',
                              fontSize: 11, fontWeight: 900,
                              display: 'inline-block',
                              boxShadow: '2px 2px 0px #FF4365',
                            }}>
                              ⚡ Excluding this transaction shifts the 30-day forecast by{' '}
                              {a.impact_on_30d_forecast >= 0 ? '+' : ''}
                              {fmt(a.impact_on_30d_forecast)}
                            </div>
                          )}
                        </div>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Footer */}
      <div style={{
        height: 36, padding: '0 16px',
        borderTop: '2px solid #000',
        background: '#F4F0EA',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        fontFamily: 'JetBrains Mono, monospace', fontSize: 11, fontWeight: 700,
      }}>
        <span>Critical: <span style={{ background: '#FF4365', color: '#fff', padding: '1px 8px', border: '1px solid #000', boxShadow: '1px 1px 0px #000', fontWeight: 900 }}>{high}</span></span>
        <span style={{ fontWeight: 900, color: '#555' }}>|</span>
        <span>Warning: <span style={{ background: '#FFE600', color: '#000', padding: '1px 8px', border: '1px solid #000', boxShadow: '1px 1px 0px #000', fontWeight: 900 }}>{medium}</span></span>
      </div>
    </div>
  );
}
