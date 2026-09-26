/**
 * TopNav — header bar with brand, workspace selector, dataset switcher, live indicators.
 * Dataset switcher: hover the Re-Analyze button to reveal neobrutalist dropdown.
 */
import React, { useState, useRef } from 'react';

const SHADOW = '3px 3px 0px #000';
const SHADOW_SM = '2px 2px 0px #000';

export default function TopNav({
  onRunAnalysis,
  running,
  datasets = [],
  activeDataset = null,
}) {
  const [dropOpen, setDropOpen] = useState(false);
  const dropRef = useRef(null);

  const activeLabel = datasets.find(d => d.id === activeDataset)?.label ?? 'Default Dataset';
  const activeDsShort = activeLabel.split(' — ')[0]; // e.g. "Dataset A"

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
          boxShadow: SHADOW_SM,
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
              boxShadow: SHADOW,
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

      {/* Right: status + dataset switcher + re-analyze + user */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexShrink: 0 }}>
        {/* Live indicator */}
        <div style={{
          display: 'flex', alignItems: 'center', gap: 6,
          padding: '4px 10px',
          background: '#fff',
          border: '2px solid #000',
          boxShadow: SHADOW_SM,
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

        {/* ── Dataset Switcher + Re-Analyze (grouped hover zone) ── */}
        <div
          ref={dropRef}
          onMouseEnter={() => setDropOpen(true)}
          onMouseLeave={() => setDropOpen(false)}
          style={{ position: 'relative' }}
        >
          {/* Active dataset indicator strip */}
          <div style={{
            display: 'flex', alignItems: 'center', gap: 0,
          }}>
            {/* Dataset badge (left-attached chip) */}
            <div style={{
              display: 'flex', alignItems: 'center', gap: 5,
              padding: '6px 10px',
              background: '#F4F0EA',
              border: '2px solid #000',
              borderRight: 'none',
              fontFamily: 'JetBrains Mono, monospace',
              fontSize: 10, fontWeight: 700,
              whiteSpace: 'nowrap',
              boxShadow: running ? 'none' : '3px 3px 0px #000',
              cursor: 'default',
            }}>
              <span className="material-symbols-outlined" style={{ fontSize: 14 }}>database</span>
              <span>{activeDsShort}</span>
              <span className="material-symbols-outlined" style={{ fontSize: 13 }}>
                {dropOpen ? 'expand_less' : 'expand_more'}
              </span>
            </div>

            {/* Re-Analyze button (right side) */}
            <button
              onClick={() => onRunAnalysis(activeDataset)}
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
                borderRadius: 0,
              }}
            >
              <span className="material-symbols-outlined" style={{ fontSize: 16, fontWeight: 700 }}>
                {running ? 'sync' : 'play_arrow'}
              </span>
              <span>{running ? 'Running...' : 'Re-Analyze'}</span>
            </button>
          </div>

          {/* ── Neobrutalist Dataset Dropdown ── */}
          {dropOpen && datasets.length > 0 && (
            <div style={{
              position: 'absolute',
              top: '100%',
              right: 0,
              marginTop: 4,
              background: '#fff',
              border: '2.5px solid #000',
              boxShadow: '4px 4px 0px #000',
              minWidth: 340,
              zIndex: 200,
            }}>
              {/* Dropdown header */}
              <div style={{
                padding: '7px 14px',
                background: '#000',
                color: '#FFE600',
                fontFamily: 'JetBrains Mono, monospace',
                fontSize: 9, fontWeight: 900, letterSpacing: '0.12em',
                textTransform: 'uppercase',
                borderBottom: '2px solid #000',
              }}>
                Select Dataset — Re-Ingest + Analyze
              </div>

              {datasets.map((ds, i) => {
                const isActive = ds.id === activeDataset;
                return (
                  <div
                    key={ds.id}
                    onClick={() => {
                      if (!running) {
                        setDropOpen(false);
                        onRunAnalysis(ds.id);
                      }
                    }}
                    style={{
                      padding: '10px 14px',
                      borderBottom: i < datasets.length - 1 ? '2px solid #000' : 'none',
                      background: isActive ? '#FFFDE6' : '#fff',
                      cursor: running ? 'not-allowed' : 'pointer',
                      display: 'flex', flexDirection: 'column', gap: 3,
                      transition: 'background 0.05s',
                    }}
                    onMouseEnter={e => { if (!isActive) e.currentTarget.style.background = '#F4F0EA'; }}
                    onMouseLeave={e => { if (!isActive) e.currentTarget.style.background = '#fff'; }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      {isActive && (
                        <span style={{
                          fontFamily: 'JetBrains Mono, monospace',
                          fontSize: 9, fontWeight: 900,
                          background: '#000', color: '#FFE600',
                          padding: '1px 6px',
                          letterSpacing: '0.08em',
                        }}>ACTIVE</span>
                      )}
                      <span style={{
                        fontFamily: 'Space Grotesk, sans-serif',
                        fontSize: 12, fontWeight: 800,
                        color: '#000',
                      }}>{ds.label}</span>
                    </div>
                    <span style={{
                      fontFamily: 'JetBrains Mono, monospace',
                      fontSize: 10, fontWeight: 500, color: '#555',
                      lineHeight: 1.4,
                    }}>{ds.description}</span>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* PROD badge */}
        <span style={{
          padding: '4px 10px',
          background: '#00E599',
          border: '2px solid #000',
          boxShadow: SHADOW_SM,
          fontFamily: 'JetBrains Mono, monospace',
          fontSize: 11, fontWeight: 900,
          letterSpacing: '0.08em',
        }}>PROD</span>

        {/* User avatar */}
        <div style={{
          width: 32, height: 32,
          background: '#FFE600',
          border: '2px solid #000',
          boxShadow: SHADOW_SM,
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
