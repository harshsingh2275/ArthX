/**
 * Sidebar — left fixed toolbar (w-16), neobrutalist icon shelf.
 */
import React from 'react';

const tools = [
  { icon: 'search',       title: 'Search' },
  { icon: 'account_tree', title: 'Source Control' },
  { icon: 'radar',        title: 'Risk Scanner' },
  { icon: 'database',     title: 'Treasury DB' },
];

const bottomTools = [
  { icon: 'terminal', title: 'Terminal' },
  { icon: 'settings', title: 'Settings' },
];

export default function Sidebar() {
  return (
    <aside style={{
      position: 'fixed', left: 0, top: 0, bottom: 0,
      width: 64,
      background: '#fff',
      borderRight: '2.5px solid #000',
      boxShadow: '2px 0px 0px #000',
      zIndex: 50,
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '12px 0',
    }}>
      {/* Top section */}
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 12 }}>
        {/* Brand mark */}
        <div style={{
          width: 40, height: 40,
          background: '#FFE600',
          border: '2px solid #000',
          boxShadow: '2px 2px 0px #000',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontFamily: 'JetBrains Mono, monospace',
          fontWeight: 900, fontSize: 18,
          cursor: 'pointer', userSelect: 'none',
        }}>Å</div>
        <div style={{ width: 32, height: 2, background: '#000', margin: '4px 0' }} />
        {/* Dashboard active icon */}
        <button style={{
          width: 40, height: 40,
          background: '#FFE600',
          border: '2px solid #000',
          boxShadow: '2px 2px 0px #000',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }} title="Workspace Dashboard">
          <span className="material-symbols-outlined" style={{ fontSize: 20, fontWeight: 700 }}>dashboard</span>
        </button>
        {/* Other tool icons */}
        {tools.map(t => (
          <button key={t.icon} style={{
            width: 40, height: 40,
            background: '#fff',
            border: '2px solid transparent',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            boxShadow: 'none',
          }}
          onMouseEnter={e => { e.currentTarget.style.background = '#FFE600'; e.currentTarget.style.border = '2px solid #000'; e.currentTarget.style.boxShadow = '2px 2px 0px #000'; }}
          onMouseLeave={e => { e.currentTarget.style.background = '#fff'; e.currentTarget.style.border = '2px solid transparent'; e.currentTarget.style.boxShadow = 'none'; }}
          title={t.title}>
            <span className="material-symbols-outlined" style={{ fontSize: 20 }}>{t.icon}</span>
          </button>
        ))}
      </div>
      {/* Bottom section */}
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 12 }}>
        {bottomTools.map(t => (
          <button key={t.icon} style={{
            width: 40, height: 40,
            background: '#fff',
            border: '2px solid transparent',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            boxShadow: 'none',
          }}
          onMouseEnter={e => { e.currentTarget.style.background = '#FFE600'; e.currentTarget.style.border = '2px solid #000'; e.currentTarget.style.boxShadow = '2px 2px 0px #000'; }}
          onMouseLeave={e => { e.currentTarget.style.background = '#fff'; e.currentTarget.style.border = '2px solid transparent'; e.currentTarget.style.boxShadow = 'none'; }}
          title={t.title}>
            <span className="material-symbols-outlined" style={{ fontSize: 20 }}>{t.icon}</span>
          </button>
        ))}
      </div>
    </aside>
  );
}
