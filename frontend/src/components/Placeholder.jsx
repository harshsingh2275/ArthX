import React from 'react';

export default function Placeholder({ title, message }) {
  return (
    <div style={{ padding: '1rem', border: '1px dashed #cbd5e1', borderRadius: '6px' }}>
      <h3>{title}</h3>
      <p>{message}</p>
    </div>
  );
}
