/**
 * TopNav — header bar with brand, workspace selector, search, live indicators.
 */
import React from 'react';

export default function TopNav({ onRunAnalysis, running }) {
  return (
    <header style={{
      height: 56,
      width: '100%',
      background: '#fff',
      borderBottom: '2.5px solid #000',
      boxShadow: '0 3px 0px #000',
      position: 'sticky', top: 0, zIndex: 40,
      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      padding: '0 20px',
      gap: 16,
    }}>
      {/* Brand + workspace */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 16, flexShrink: 0 }}>
        <span style={{
          fontFamily: 'JetBrains Mono, monospace',
          fontWeight: 900, fontSize: 20, letterSpacing: '-0.03em',
          color: '#000',
        }}>ArthX</span>
        <span style={{ fontWeight: 900, fontSize: 18, color: '#000' }}>/</span>
        <div style={{
          display: 'flex', alignItems: 'center', gap: 8,
          padding: '4px 12px',
          background: '#F4F0EA',
          border: '2px solid #000',
          boxShadow: '2px 2px 0px #000',
          fontFamily: 'JetBrains Mono, monospace',
          fontSize: 11, fontWeight: 700,
          cursor: 'pointer',
        }}>
          <span className="material-symbols-outlined" style={{ fontSize: 16, fontWeight: 700 }}>account_tree</span>
          <span>arthx-workspace / prod-treasury</span>
          <span className="material-symbols-outlined" style={{ fontSize: 16 }}>arrow_drop_down</span>
        </div>
      </div>

      {/* Command search bar */}
      <div style={{ flex: 1, maxWidth: 480, margin: '0 16px' }}>
        <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
          <span className="material-symbols-outlined" style={{
            position: 'absolute', left: 12, fontSize: 18, fontWeight: 700, pointerEvents: 'none',
          }}>terminal</span>
          <input
            type="text"
            placeholder="Search transactions, anomalies, or press ⌘K for commands..."
            style={{
              width: '100%',
              background: '#fff',
              border: '2px solid #000',
              boxShadow: '3px 3px 0px #000',
              padding: '6px 56px 6px 40px',
              fontFamily: 'JetBrains Mono, monospace',
              fontSize: 11, fontWeight: 500,
              color: '#000',
              outline: 'none',
              borderRadius: 0,
            }}
          />
          <kbd style={{
            position: 'absolute', right: 10,
            padding: '2px 6px',
            background: '#FFE600',
            border: '2px solid #000',
            fontFamily: 'JetBrains Mono, monospace',
            fontSize: 10, fontWeight: 900,
            boxShadow: '1px 1px 0px #000',
          }}>⌘K</kbd>
        </div>
      </div>

      {/* Right: status + re-analyze + user */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexShrink: 0 }}>
        {/* Live indicator */}
        <div style={{
          display: 'flex', alignItems: 'center', gap: 6,
          padding: '4px 10px',
          background: '#fff',
          border: '2px solid #000',
          boxShadow: '2px 2px 0px #000',
          fontFamily: 'JetBrains Mono, monospace',
          fontSize: 11, fontWeight: 700,
        }}>
          <span style={{
            display: 'inline-block', width: 10, height: 10,
            background: '#00E599', border: '1px solid #000',
            animation: 'pulse 2s infinite',
          }} />
          <span>LIVE</span>
        </div>

        {/* Re-analyze button */}
        <button
          onClick={onRunAnalysis}
          disabled={running}
          style={{
            display: 'flex', alignItems: 'center', gap: 6,
            background: running ? '#ccc' : '#FFE600',
            border: '2px solid #000',
            boxShadow: running ? 'none' : '3px 3px 0px #000',
            padding: '6px 14px',
            fontFamily: 'JetBrains Mono, monospace',
            fontSize: 11, fontWeight: 900,
            color: '#000',
            cursor: running ? 'not-allowed' : 'pointer',
          }}
        >
          <span className="material-symbols-outlined" style={{ fontSize: 16, fontWeight: 700 }}>
            {running ? 'sync' : 'play_arrow'}
          </span>
          <span>{running ? 'Running...' : 'Re-Analyze'}</span>
        </button>

        {/* PROD badge */}
        <span style={{
          padding: '4px 10px',
          background: '#00E599',
          border: '2px solid #000',
          boxShadow: '2px 2px 0px #000',
          fontFamily: 'JetBrains Mono, monospace',
          fontSize: 11, fontWeight: 900,
          letterSpacing: '0.08em',
        }}>PROD</span>

        {/* User avatar */}
        <div style={{
          width: 32, height: 32,
          background: '#FFE600',
          border: '2px solid #000',
          boxShadow: '2px 2px 0px #000',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          cursor: 'pointer',
        }}>
          <span className="material-symbols-outlined" style={{ fontSize: 20, fontWeight: 700 }}>person</span>
        </div>
      </div>

      <style>{`@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.4} }`}</style>
    </header>
  );
}
