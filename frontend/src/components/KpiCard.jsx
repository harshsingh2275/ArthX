/**
 * KpiCard — single metric card with accent bar, big mono number, sub-labels.
 * Props:
 *   accentColor  — top bar color
 *   iconName     — material symbol
 *   iconBg       — icon bg color
 *   label        — card title (string, shown uppercase)
 *   value        — main big number (string)
 *   subLeft      — left footer text (string)
 *   subRight     — right footer text/node
 *   loading      — bool
 */
import React from 'react';

export default function KpiCard({
  accentColor, iconName, iconBg, label, value, subLeft, subRight, loading,
}) {
  return (
    <div style={{
      background: '#fff',
      border: '2.5px solid #000',
      boxShadow: '4px 4px 0px #000',
      padding: 16,
      display: 'flex', flexDirection: 'column', justifyContent: 'space-between',
      position: 'relative', overflow: 'hidden',
      minHeight: 130,
    }}>
      {/* Accent bar */}
      <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 6, background: accentColor }} />

      {/* Header row */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', paddingTop: 6 }}>
        <span style={{
          fontFamily: 'Space Grotesk, sans-serif',
          fontSize: 11, fontWeight: 700,
          textTransform: 'uppercase', letterSpacing: '0.07em',
        }}>{label}</span>
        <div style={{
          width: 24, height: 24,
          background: iconBg,
          border: '2px solid #000',
          boxShadow: '1px 1px 0px #000',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          flexShrink: 0,
        }}>
          <span className="material-symbols-outlined" style={{ fontSize: 15, fontWeight: 700 }}>{iconName}</span>
        </div>
      </div>

      {/* Big value */}
      <div style={{ margin: '12px 0' }}>
        {loading ? (
          <div style={{
            height: 36, width: '60%',
            background: '#F4F0EA', border: '1px solid #ccc',
            animation: 'shimmer 1.2s infinite',
          }} />
        ) : (
          <span style={{
            fontFamily: 'JetBrains Mono, monospace',
            fontSize: 30, fontWeight: 900,
            letterSpacing: '-0.02em',
            lineHeight: 1,
          }}>{value}</span>
        )}
      </div>

      {/* Footer */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        paddingTop: 8, borderTop: '2px solid #000',
        fontFamily: 'JetBrains Mono, monospace',
        fontSize: 11, fontWeight: 600,
      }}>
        <span style={{ color: '#333' }}>{subLeft}</span>
        {subRight && <span>{subRight}</span>}
      </div>

      <style>{`@keyframes shimmer{0%{opacity:.6}50%{opacity:1}100%{opacity:.6}}`}</style>
    </div>
  );
}
