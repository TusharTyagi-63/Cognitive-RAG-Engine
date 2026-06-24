import { useState, useEffect, useRef } from 'react';
import type { FormEvent } from 'react';
import { Send, Loader2, Copy, Check } from 'lucide-react';
import { useParams, useNavigate } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { api, baseUrl } from '../api/client';

const API_BASE = `${baseUrl}/api/v1`;

// Custom component for syntax highlighting with copy button
const CodeBlock = ({ inline, className, children, ...props }: any) => {
  const match = /language-(\w+)/.exec(className || '');
  const [copied, setCopied] = useState(false);
  
  if (!inline && match) {
    return (
      <div style={{ position: 'relative', marginTop: '1rem', marginBottom: '1rem', borderRadius: '8px', overflow: 'hidden', border: '1px solid var(--border)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: '#1e1e1e', padding: '0.25rem 0.75rem', borderBottom: '1px solid #333' }}>
          <span style={{ fontSize: '0.7rem', color: '#888', textTransform: 'uppercase', fontFamily: 'monospace' }}>{match[1]}</span>
          <button 
            onClick={() => {
              navigator.clipboard.writeText(String(children).replace(/\n$/, ''));
              setCopied(true);
              setTimeout(() => setCopied(false), 2000);
            }}
            style={{ background: 'transparent', border: 'none', padding: '0.25rem', color: '#888', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '0.25rem', fontSize: '0.75rem' }}
          >
            {copied ? <Check size={14} color="#10b981" /> : <Copy size={14} />}
            {copied ? 'Copied!' : 'Copy'}
          </button>
        </div>
        <SyntaxHighlighter
          style={vscDarkPlus as any}
          language={match[1]}
          PreTag="div"
          customStyle={{ margin: 0, borderRadius: 0, padding: '1rem', fontSize: '0.875rem' }}
          {...props}
        >
          {String(children).replace(/\n$/, '')}
        </SyntaxHighlighter>
      </div>
    );
  }
  return <code className={className} style={{ background: 'rgba(0,0,0,0.3)', padding: '0.1rem 0.4rem', borderRadius: '4px', fontSize: '0.875em', fontFamily: 'monospace' }} {...props}>{children}</code>;
};

export function ChatPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [messages, setMessages] = useState<{ role: string, content: string, sources?: any[] }[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [streaming, setStreaming] = useState(false);
  
  const [documents, setDocuments] = useState<{ id: string, filename: string }[]>([]);
  const [selectedDocs, setSelectedDocs] = useState<string[]>([]);

  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Load available documents for the multi-select filter
  useEffect(() => {
    api.get('/documents/').then(res => {
      setDocuments(res.data?.documents || []);
    }).catch(console.error);
  }, []);

  useEffect(() => {
    if (!loading && !streaming && inputRef.current) {
      setTimeout(() => { inputRef.current?.focus(); }, 50);
    }
  }, [loading, streaming, id]);

  useEffect(() => {
    if (id === 'new') {
      setMessages([{ role: 'assistant', content: 'Hello. The retrieval engine is online. Ask a question to begin semantic search across your knowledge base.' }]);
    } else if (id) {
      loadHistory(id);
    }
  }, [id]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const loadHistory = async (sessionId: string) => {
    try {
      const res = await api.get(`/chat/sessions/${sessionId}/messages`);
      setMessages(res.data?.data?.messages || []);
    } catch (err) {
      console.error('Failed to load history', err);
    }
  };

  const handleSend = async (e: FormEvent) => {
    e.preventDefault();
    if (!input.trim() || loading || streaming) return;

    const userMsg = input.trim();
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: userMsg }]);

    // Immediately show the AI thinking (no dead loading state)
    setStreaming(true);
    setMessages(prev => [...prev, { role: 'assistant', content: '' }]);

    try {
      let targetSessionId = id;

      // If new session, create it first
      if (id === 'new') {
        const title = userMsg.length > 30 ? userMsg.substring(0, 30) + '...' : userMsg;
        const createRes = await api.post('/chat/sessions', { title });
        targetSessionId = createRes.data?.data?.id;
      }

      const token = localStorage.getItem('token');
      
      const payload: any = { content: userMsg };
      if (selectedDocs.length > 0) {
        payload.document_ids = selectedDocs;
      }

      const response = await fetch(`${API_BASE}/chat/sessions/${targetSessionId}/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(payload)
      });

      if (!response.ok || !response.body) throw new Error('Stream failed');

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() ?? '';

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          const data = line.slice(6);

          if (data === '[DONE]') break;
          
          if (data.startsWith('[SOURCES]')) {
            try {
              const sources = JSON.parse(data.slice(9));
              setMessages(prev => {
                const updated = [...prev];
                updated[updated.length - 1] = { ...updated[updated.length - 1], sources };
                return updated;
              });
            } catch(e) { console.error("Failed to parse sources", e); }
            continue; 
          }

          // Restore newlines that were escaped for SSE transport
          const text = data.replace(/\\n/g, '\n');

          setMessages(prev => {
            const updated = [...prev];
            updated[updated.length - 1] = {
              ...updated[updated.length - 1],
              content: updated[updated.length - 1].content + text
            };
            return updated;
          });
        }
      }

      if (id === 'new') {
        navigate(`/chat/${targetSessionId}`, { replace: true });
      }
    } catch (err) {
      console.error(err);
      setMessages(prev => {
        const updated = [...prev];
        updated[updated.length - 1] = { role: 'assistant', content: 'Sorry, I encountered an error answering your question.' };
        return updated;
      });
    } finally {
      setLoading(false);
      setStreaming(false);
    }
  };

  return (
    <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', height: '100%', gap: '1rem' }}>
      <header>
        <h2 style={{ margin: 0 }}>AI Assistant</h2>
      </header>

      {/* Chat Window */}
      <div className="glass-panel" style={{ flex: 1, padding: '1.5rem', overflowY: 'auto' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          {messages.map((msg, idx) => (
          <div key={idx} style={{
            display: 'flex',
            justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start'
          }}>
            <div style={{
              maxWidth: '85%',
              padding: '1rem 1.2rem',
              borderRadius: msg.role === 'user' ? '20px 20px 4px 20px' : '20px 20px 20px 4px',
              background: msg.role === 'user' ? 'linear-gradient(135deg, var(--primary), var(--accent-secondary))' : 'rgba(255, 255, 255, 0.03)',
              border: msg.role === 'user' ? 'none' : '1px solid var(--border-light)',
              boxShadow: msg.role === 'user' ? '0 4px 15px rgba(99, 102, 241, 0.3)' : 'none',
              lineHeight: '1.6'
            }}>
              {msg.role === 'user' ? (
                msg.content
              ) : (
                <>
                  <ReactMarkdown
                    components={{
                      p: ({children}) => <p style={{margin: '0 0 0.5rem 0'}}>{children}</p>,
                      ul: ({children}) => <ul style={{margin: '0.5rem 0', paddingLeft: '1.5rem'}}>{children}</ul>,
                      ol: ({children}) => <ol style={{margin: '0.5rem 0', paddingLeft: '1.5rem'}}>{children}</ol>,
                      li: ({children}) => <li style={{marginBottom: '0.25rem'}}>{children}</li>,
                      strong: ({children}) => <strong style={{color: 'var(--text-main)', fontWeight: 600}}>{children}</strong>,
                      h1: ({children}) => <h1 style={{fontSize: '1.25rem', margin: '0.75rem 0 0.5rem 0'}}>{children}</h1>,
                      h2: ({children}) => <h2 style={{fontSize: '1.1rem', margin: '0.75rem 0 0.5rem 0'}}>{children}</h2>,
                      h3: ({children}) => <h3 style={{fontSize: '1rem', margin: '0.5rem 0 0.25rem 0'}}>{children}</h3>,
                      hr: () => <hr style={{border: 'none', borderTop: '1px solid var(--border)', margin: '0.75rem 0'}} />,
                      code: CodeBlock as any,
                    }}
                  >
                    {msg.content}
                  </ReactMarkdown>
                  
                  {/* Source Citations */}
                  {msg.sources && msg.sources.length > 0 && (
                    <div style={{ marginTop: '1.5rem', paddingTop: '1rem', borderTop: '1px solid rgba(255,255,255,0.1)' }}>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px', fontWeight: 600 }}>Sources Used</span>
                      <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', marginTop: '0.5rem' }}>
                        {Array.from(new Set(msg.sources.map((src: any) => src.document_id))).map((docId: any, i: number) => {
                          const docName = documents.find(d => d.id === docId)?.filename || 'Document';
                          return (
                            <div key={i} style={{ 
                              background: 'rgba(99, 102, 241, 0.1)', 
                              border: '1px solid var(--border)', 
                              padding: '0.2rem 0.6rem', 
                              borderRadius: '100px',
                              fontSize: '0.75rem',
                              color: 'var(--text-main)',
                              display: 'flex',
                              alignItems: 'center',
                              gap: '0.25rem'
                            }}>
                              <span style={{ color: 'var(--primary)' }}>📄</span>
                              {docName}
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}
                </>
              )}
              {/* Blinking cursor on last streaming message */}
              {streaming && idx === messages.length - 1 && msg.role === 'assistant' && (
                <span style={{ display: 'inline-block', width: '2px', height: '1em', background: 'var(--primary)', marginLeft: '2px', animation: 'blink 1s step-end infinite', verticalAlign: 'text-bottom' }} />
              )}
            </div>
          </div>
        ))}

        <div ref={bottomRef} />
        </div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', background: 'rgba(0,0,0,0.2)', padding: '1rem', borderRadius: '24px', border: '1px solid var(--border-light)', backdropFilter: 'blur(10px)' }}>
        {/* Multi-Document Selector */}
        {documents.length > 0 && (
          <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', padding: '0 0.5rem' }}>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', marginRight: '0.5rem' }}>Search in:</span>
            {documents.map(doc => (
              <label key={doc.id} style={{ 
                display: 'flex', 
                alignItems: 'center', 
                gap: '0.35rem', 
                fontSize: '0.75rem', 
                background: selectedDocs.includes(doc.id) ? 'rgba(99, 102, 241, 0.2)' : 'rgba(255,255,255,0.05)', 
                border: selectedDocs.includes(doc.id) ? '1px solid var(--primary)' : '1px solid transparent',
                padding: '0.25rem 0.75rem', 
                borderRadius: '100px', 
                cursor: 'pointer',
                transition: 'all 0.2s',
                color: selectedDocs.includes(doc.id) ? 'var(--text-main)' : 'var(--text-muted)'
              }}>
                <input 
                  type="checkbox" 
                  checked={selectedDocs.includes(doc.id)} 
                  onChange={(e) => {
                    if (e.target.checked) setSelectedDocs(prev => [...prev, doc.id]);
                    else setSelectedDocs(prev => prev.filter(id => id !== doc.id));
                  }}
                  style={{ display: 'none' }}
                />
                {doc.filename}
              </label>
            ))}
          </div>
        )}

        <form onSubmit={handleSend} style={{ display: 'flex', gap: '1rem' }}>
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask a question about your documents..."
            style={{ flex: 1, padding: '0.5rem 1rem', background: 'transparent', border: 'none', outline: 'none', boxShadow: 'none' }}
            disabled={loading || streaming}
          />
          <button type="submit" disabled={loading || streaming} style={{ padding: '0.75rem', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', aspectRatio: '1/1', background: 'var(--primary)', color: 'white', border: 'none', cursor: 'pointer' }}>
            {streaming ? <Loader2 size={18} className="animate-spin" /> : <Send size={18} style={{ transform: 'translateX(-1px)' }} />}
          </button>
        </form>
      </div>
    </div>
  );
}
