/**
 * ForecastChart — Cash Flow Velocity & Horizon Forecast.
 * Uses Recharts: forecast line + confidence band.
 * Data: GET /api/forecast — all points are forward-looking forecast data.
 */
import React, { useMemo } from 'react';
import {
  ComposedChart, Line, Area, XAxis, YAxis,
  CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from 'recharts';

function fmtMoney(v) {
  if (v == null || isNaN(v)) return '';
  const abs = Math.abs(v);
  if (abs >= 1_000_000) return `$${(v / 1_000_000).toFixed(1)}M`;
  if (abs >= 1_000)     return `$${(v / 1_000).toFixed(0)}k`;
  return `$${v.toFixed(0)}`;
}

function fmtDate(d) {
  if (!d) return '';
  const dt = new Date(d);
  return dt.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  // Filter to only real data keys
  const entries = payload.filter(p => p.value != null && p.dataKey !== 'upper');
  return (
    <div style={{
      background: '#fff',
      border: '2.5px solid #000',
      boxShadow: '3px 3px 0px #000',
      padding: '10px 14px',
      fontFamily: 'JetBrains Mono, monospace',
      fontSize: 11,
      minWidth: 200,
      borderRadius: 0,
    }}>
      <div style={{ fontWeight: 900, marginBottom: 6, borderBottom: '1px solid #000', paddingBottom: 4 }}>
        {fmtDate(label)}
      </div>
      {entries.map(p => (
        <div key={p.dataKey} style={{ display: 'flex', justifyContent: 'space-between', gap: 16, marginTop: 3 }}>
          <span style={{ color: p.color || '#000', fontWeight: 700 }}>{p.name}</span>
          <span style={{ fontWeight: 900 }}>{fmtMoney(p.value)}</span>
        </div>
      ))}
      {/* Confidence band info from upper/lower */}
      {payload.find(p => p.dataKey === 'upper') && payload.find(p => p.dataKey === 'lower') && (
        <div style={{ marginTop: 4, fontSize: 10, color: '#0041C9', fontWeight: 700 }}>
          Band: {fmtMoney(payload.find(p => p.dataKey === 'lower')?.value)} → {fmtMoney(payload.find(p => p.dataKey === 'upper')?.value)}
        </div>
      )}
    </div>
  );
};

export default function ForecastChart({ forecast = {}, trendSummary, loading }) {
  const chartData = useMemo(() => {
    const pts = forecast?.forecast;
    if (!pts?.length) return [];
    return pts.map(d => ({
      date: d.date,
      forecast: d.predicted_net_flow,
      lower: d.lower,
      upper: d.upper,
    }));
  }, [forecast]);

  const netPosition = useMemo(() => {
    if (!chartData.length) return null;
    return chartData[chartData.length - 1]?.forecast;
  }, [chartData]);

  return (
    <div style={{
      background: '#fff',
      border: '2.5px solid #000',
      boxShadow: '4px 4px 0px #000',
      display: 'flex', flexDirection: 'column',
    }}>
      {/* Header */}
      <div style={{
        height: 44, padding: '0 16px',
        borderBottom: '2px solid #000',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        background: '#F4F0EA', flexShrink: 0,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span className="material-symbols-outlined" style={{ fontSize: 18, fontWeight: 700 }}>timeline</span>
          <span style={{
            fontFamily: 'Space Grotesk, sans-serif',
            fontSize: 11, fontWeight: 900, textTransform: 'uppercase', letterSpacing: '0.06em',
          }}>Cash Flow Velocity &amp; Horizon Forecast</span>
          <span style={{
            fontFamily: 'JetBrains Mono, monospace',
            fontSize: 10, fontWeight: 900,
            background: '#FFE600',
            border: '2px solid #000',
            padding: '2px 8px',
            boxShadow: '1px 1px 0px #000',
          }}>{forecast?.horizon_days ? `${forecast.horizon_days}D HORIZON` : '30D HORIZON'}</span>
        </div>
        <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 11, fontWeight: 700, color: '#333' }}>
          {netPosition != null && !loading && (
            <span>End position: <strong style={{ color: netPosition >= 0 ? '#008a5f' : '#FF4365' }}>{fmtMoney(netPosition)}</strong></span>
          )}
        </div>
      </div>

      {/* Trend summary */}
      {trendSummary && !loading && (
        <div style={{
          padding: '8px 16px',
          borderBottom: '1px solid #e2e8f0',
          fontFamily: 'Space Grotesk, sans-serif',
          fontSize: 12, fontWeight: 500, color: '#333',
          background: '#FAFAFA', flexShrink: 0,
        }}>
          <span style={{
            fontWeight: 700,
            fontFamily: 'JetBrains Mono, monospace',
            fontSize: 10, letterSpacing: '0.06em',
          }}>TREND: </span>
          {trendSummary}
        </div>
      )}

      {/* Chart */}
      <div style={{ padding: '16px 8px 8px 0', flex: 1, minHeight: 280 }}>
        {loading ? (
          <div style={{ height: 260, display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: 'JetBrains Mono, monospace', fontSize: 12, color: '#888' }}>
            Loading forecast…
          </div>
        ) : chartData.length === 0 ? (
          <div style={{
            height: 260, display: 'flex', flexDirection: 'column',
            alignItems: 'center', justifyContent: 'center',
            fontFamily: 'JetBrains Mono, monospace', fontSize: 12, color: '#888', gap: 8,
          }}>
            <span className="material-symbols-outlined" style={{ fontSize: 32, color: '#ccc' }}>ssid_chart</span>
            No forecast data. Click Re-Analyze to run the pipeline.
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={260}>
            <ComposedChart data={chartData} margin={{ top: 8, right: 24, left: 8, bottom: 0 }}>
              <CartesianGrid strokeDasharray="2 6" stroke="#E2E8F0" strokeWidth={1.5} />
              <XAxis
                dataKey="date"
                tickFormatter={fmtDate}
                tick={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, fontWeight: 700, fill: '#000' }}
                tickLine={false}
                axisLine={{ stroke: '#000', strokeWidth: 2 }}
                interval="preserveStartEnd"
              />
              <YAxis
                tickFormatter={fmtMoney}
                tick={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, fontWeight: 700, fill: '#000' }}
                tickLine={false}
                axisLine={{ stroke: '#000', strokeWidth: 2 }}
                width={68}
              />
              <Tooltip content={<CustomTooltip />} />
              {/* Confidence upper band (upper fills to upper, lower fills back to white) */}
              <Area
                type="monotone"
                dataKey="upper"
                stroke="#0041C9"
                strokeDasharray="3 3"
                strokeWidth={1.5}
                fill="#E0F2FE"
                fillOpacity={0.6}
                name="Upper (90%)"
                legendType="none"
              />
              <Area
                type="monotone"
                dataKey="lower"
                stroke="#0041C9"
                strokeDasharray="3 3"
                strokeWidth={1.5}
                fill="#fff"
                fillOpacity={1}
                name="Lower (90%)"
                legendType="none"
              />
              {/* Forecast line */}
              <Line
                type="monotone"
                dataKey="forecast"
                stroke="#0041C9"
                strokeWidth={2.5}
                strokeDasharray="6 4"
                dot={{ fill: '#FFE600', stroke: '#000', strokeWidth: 2, r: 3 }}
                activeDot={{ r: 5, fill: '#FFE600', stroke: '#000', strokeWidth: 2 }}
                name="Forecast"
              />
              <Legend
                wrapperStyle={{
                  fontFamily: 'JetBrains Mono, monospace',
                  fontSize: 10, fontWeight: 700, paddingTop: 8,
                }}
              />
            </ComposedChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Bottom legend row */}
      {!loading && chartData.length > 0 && (
        <div style={{
          padding: '8px 16px 12px',
          borderTop: '2px solid #000',
          display: 'flex', alignItems: 'center', gap: 20, flexWrap: 'wrap',
          fontFamily: 'JetBrains Mono, monospace', fontSize: 10, fontWeight: 700, flexShrink: 0,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={{ width: 16, height: 3, borderTop: '2px dashed #0041C9', display: 'inline-block' }} />
            <span style={{ color: '#0041C9' }}>Model Forecast</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={{ width: 14, height: 10, background: '#E0F2FE', border: '1px solid #0041C9', display: 'inline-block' }} />
            <span>90% Confidence Band</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={{ width: 8, height: 8, background: '#FFE600', border: '2px solid #000', display: 'inline-block', borderRadius: '50%' }} />
            <span>Data Point</span>
          </div>
          {forecast.method && (
            <span style={{ marginLeft: 'auto', color: '#555' }}>Method: {forecast.method}</span>
          )}
        </div>
      )}
    </div>
  );
}
