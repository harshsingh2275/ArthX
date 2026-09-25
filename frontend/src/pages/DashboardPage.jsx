import React from 'react';

export default function DashboardPage() {
  return (
    <div style={{ padding: '2rem', fontFamily: 'system-ui, sans-serif' }}>
      <header style={{ marginBottom: '2rem' }}>
        <h1 style={{ fontSize: '2rem', fontWeight: 'bold', color: '#1e293b' }}>
          ArthX — Financial Intelligence Platform
        </h1>
        <p style={{ color: '#64748b' }}>
          Explainable AI Cash Flow Forecasting & Fraud Anomaly Detection
        </p>
      </header>
      <div style={{ background: '#f8fafc', padding: '1.5rem', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
        <h2 style={{ fontSize: '1.25rem', fontWeight: 600, color: '#334155' }}>System Status: Initializing</h2>
        <p style={{ color: '#475569', marginTop: '0.5rem' }}>Phase 0 Setup Placeholder — Frontend active.</p>
      </div>
    </div>
  );
}
