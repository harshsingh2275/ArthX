/**
 * AssistantPanel — Terminal-style conversational AI chat.
 * Sends questions to POST /api/assistant/query.
 * Preserves the dark terminal aesthetic from the Stitch export.
 */
import React, { useState, useRef, useEffect } from 'react';
import { queryAssistant } from '../api/client';

const DEMO_PROMPTS = [
  "What's our cash flow forecast for the next 30 days?",
  "Which vendors have unusual transaction activity?",
  "Are there any duplicate invoices I should know about?",
  "Why is the top flagged vendor marked as high risk?",
];

function MessageBubble({ msg }) {
  if (msg.role === 'user') {
    return (
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10 }}>
        <span style={{ color: '#00E599', fontWeight: 900, userSelect: 'none', whiteSpace: 'nowrap', fontFamily: 'JetBrains Mono, monospace', fontSize: 12 }}>
          finops@arthx:~$
        </span>
        <span style={{ color: '#fff', fontWeight: 500, fontFamily: 'JetBrains Mono, monospace', fontSize: 12, wordBreak: 'break-word' }}>
          /ask &quot;{msg.content}&quot;
        </span>
      </div>
    );
  }
  if (msg.role === 'thinking') {
    return (
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: '#777', fontFamily: 'JetBrains Mono, monospace', fontSize: 11 }}>
        <span style={{ animation: 'spin 1s linear infinite', display: 'inline-block' }}>⟳</span>
        <span>ArthX-AI reasoning…</span>
        <style>{`@keyframes spin{from{transform:rotate(0deg)}to{transform:rotate(360deg)}}`}</style>
      </div>
    );
  }
  if (msg.role === 'error') {
    return (
      <div style={{
        borderLeft: '3px solid #FF4365',
        paddingLeft: 12, color: '#FF4365',
        fontFamily: 'JetBrains Mono, monospace', fontSize: 11,
      }}>
        [ERROR] {msg.content}
      </div>
    );
  }
  // assistant
  return (
    <div style={{ paddingLeft: 4, borderLeft: '2px solid #FFE600' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: '#FFE600', fontWeight: 900, fontSize: 11, fontFamily: 'JetBrains Mono, monospace', marginBottom: 8 }}>
        <span className="material-symbols-outlined" style={{ fontSize: 16 }}>psychology</span>
        <span>[ARTHX-AI REASONING CORE]</span>
      </div>
      <div style={{ color: '#E0E0E0', fontFamily: 'JetBrains Mono, monospace', fontSize: 12, lineHeight: 1.7, whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
        {msg.content}
      </div>
    </div>
  );
}

export default function AssistantPanel() {
  const [messages, setMessages]   = useState([]);
  const [input, setInput]         = useState('');
  const [loading, setLoading]     = useState(false);
  const scrollRef                 = useRef(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const sendQuestion = async (question) => {
    if (!question.trim() || loading) return;
    const q = question.trim();
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: q }, { role: 'thinking', content: '' }]);
    setLoading(true);
    try {
      const data = await queryAssistant(q);
      const answer = data.answer || data.response || JSON.stringify(data);
      setMessages(prev => [
        ...prev.filter(m => m.role !== 'thinking'),
        { role: 'assistant', content: answer },
      ]);
    } catch (err) {
      setMessages(prev => [
        ...prev.filter(m => m.role !== 'thinking'),
        { role: 'error', content: err.message },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendQuestion(input);
    }
  };

  return (
    <div style={{
      background: '#111111',
      border: '2.5px solid #000',
      boxShadow: '4px 4px 0px #000',
      display: 'flex', flexDirection: 'column',
      fontFamily: 'JetBrains Mono, monospace',
    }}>
      {/* Tab bar */}
      <div style={{
        height: 40, padding: '0 12px',
        background: '#000',
        borderBottom: '2px solid #000',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, height: '100%' }}>
          <button style={{
            height: 28, padding: '0 12px',
            background: '#FFE600', color: '#000',
            border: '2px solid #000',
            boxShadow: '2px 2px 0px #fff',
            display: 'flex', alignItems: 'center', gap: 6,
            fontSize: 11, fontWeight: 900,
          }}>
            <span className="material-symbols-outlined" style={{ fontSize: 15, fontWeight: 700 }}>smart_toy</span>
            <span>AI ASSISTANT</span>
          </button>
          <button style={{
            height: 28, padding: '0 12px',
            background: 'transparent', color: '#A0A0A0',
            border: 'none', boxShadow: 'none',
            fontSize: 11, fontWeight: 700,
          }}>ANOMALY LOGS</button>
        </div>
        <span style={{ color: '#A0A0A0', fontSize: 11 }}>
          Model: <span style={{ color: '#FFE600', fontWeight: 900 }}>ArthX-FinOps-70b</span>
        </span>
      </div>

      {/* Demo prompt chips */}
      {messages.length === 0 && (
        <div style={{
          padding: '12px 16px',
          background: '#0D0E11',
          borderBottom: '1px solid #222',
          display: 'flex', flexWrap: 'wrap', gap: 8,
        }}>
          <span style={{ color: '#555', fontSize: 10, fontWeight: 700, letterSpacing: '0.06em', alignSelf: 'center' }}>
            QUICK ASK →
          </span>
          {DEMO_PROMPTS.map((p, i) => (
            <button
              key={i}
              onClick={() => sendQuestion(p)}
              style={{
                background: '#1A1A1A',
                color: '#ccc',
                border: '1px solid #333',
                boxShadow: 'none',
                padding: '4px 10px',
                fontSize: 10, fontWeight: 600,
                cursor: 'pointer',
                borderRadius: 0,
              }}
              onMouseEnter={e => { e.currentTarget.style.background = '#FFE600'; e.currentTarget.style.color = '#000'; e.currentTarget.style.border = '1px solid #000'; }}
              onMouseLeave={e => { e.currentTarget.style.background = '#1A1A1A'; e.currentTarget.style.color = '#ccc'; e.currentTarget.style.border = '1px solid #333'; }}
            >
              {p.length > 40 ? p.slice(0, 40) + '…' : p}
            </button>
          ))}
        </div>
      )}

      {/* Message stream */}
      <div
        ref={scrollRef}
        style={{
          padding: 16,
          background: '#0D0E11',
          display: 'flex', flexDirection: 'column', gap: 16,
          maxHeight: 280, overflowY: 'auto',
          borderBottom: '2px solid #000',
          minHeight: 120,
        }}
      >
        {messages.length === 0 ? (
          <div style={{ color: '#444', fontSize: 11, fontWeight: 500 }}>
            <span style={{ color: '#00E599', fontWeight: 900 }}>finops@arthx:~$</span>{' '}
            <span style={{ color: '#666' }}>Ask about cash flow, anomalies, or invoice issues…</span>
          </div>
        ) : (
          messages.map((m, i) => <MessageBubble key={i} msg={m} />)
        )}
      </div>

      {/* Input bar */}
      <div style={{
        height: 44, padding: '0 16px',
        background: '#111111',
        display: 'flex', alignItems: 'center', gap: 12,
      }}>
        <span style={{ color: '#00E599', fontSize: 11, fontWeight: 900, whiteSpace: 'nowrap', userSelect: 'none' }}>
          arthx-ai &gt;
        </span>
        <input
          type="text"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask about cash position, vendor anomalies, or duplicate invoices…"
          disabled={loading}
          style={{
            flex: 1,
            background: 'transparent',
            border: 'none',
            outline: 'none',
            color: '#fff',
            fontFamily: 'JetBrains Mono, monospace',
            fontSize: 12, fontWeight: 500,
            caretColor: '#FFE600',
          }}
        />
        <button
          onClick={() => sendQuestion(input)}
          disabled={loading || !input.trim()}
          style={{
            display: 'flex', alignItems: 'center', gap: 6,
            background: loading || !input.trim() ? '#333' : '#FFE600',
            color: '#000',
            border: '2px solid #000',
            padding: '4px 12px',
            fontSize: 11, fontWeight: 900,
            boxShadow: '2px 2px 0px #fff',
            whiteSpace: 'nowrap',
            cursor: loading || !input.trim() ? 'not-allowed' : 'pointer',
          }}
        >
          <span>Enter</span>
          <span style={{ fontWeight: 900 }}>↵</span>
        </button>
      </div>
    </div>
  );
}
