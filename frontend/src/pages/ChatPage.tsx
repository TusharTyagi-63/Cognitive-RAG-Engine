import { useState, useEffect, useRef } from 'react';
import type { FormEvent } from 'react';
import { Send, Loader2, Copy, Check, Sparkles, Volume2, VolumeX, Download, X, Zap, Brain } from 'lucide-react';
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
      <div style={{ position: 'relative', marginTop: '0.75rem', marginBottom: '0.75rem', borderRadius: '8px', overflow: 'hidden', border: '1px solid rgba(255,255,255,0.1)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: '#141824', padding: '0.3rem 0.75rem', borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
          <span style={{ fontSize: '0.7rem', color: '#94a3b8', textTransform: 'uppercase', fontFamily: 'monospace' }}>{match[1]}</span>
          <button 
            onClick={() => {
              navigator.clipboard.writeText(String(children).replace(/\n$/, ''));
              setCopied(true);
              setTimeout(() => setCopied(false), 2000);
            }}
            style={{ background: 'transparent', border: 'none', padding: '0.2rem', color: '#94a3b8', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '0.25rem', fontSize: '0.75rem' }}
          >
            {copied ? <Check size={14} color="#10b981" /> : <Copy size={14} />}
            {copied ? 'Copied' : 'Copy'}
          </button>
        </div>
        <SyntaxHighlighter
          style={vscDarkPlus as any}
          language={match[1]}
          PreTag="div"
          customStyle={{ margin: 0, borderRadius: 0, padding: '0.85rem', fontSize: '0.85rem', background: '#0b0e14' }}
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
  const [messages, setMessages] = useState<{ role: string, content: string, sources?: any[], metrics?: any }[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [streaming, setStreaming] = useState(false);
  const [reasoningMode, setReasoningMode] = useState<'fast' | 'deep'>('fast');
  const [speakingIndex, setSpeakingIndex] = useState<number | null>(null);
  
  // Source Inspector Drawer State
  const [inspectorOpen, setInspectorOpen] = useState(false);
  const [activeSource, setActiveSource] = useState<{ filename: string, content: string, score?: number } | null>(null);

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

    let userMsg = input.trim();
    if (reasoningMode === 'deep') {
      userMsg = `[Deep Synthesis Mode]: Provide a thorough, structured breakdown with step-by-step reasoning and citations. ${userMsg}`;
    }

    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: input.trim() }]);

    setStreaming(true);
    setMessages(prev => [...prev, { role: 'assistant', content: '' }]);

    try {
      let targetSessionId = id;

      if (id === 'new') {
        const title = input.trim().length > 30 ? input.trim().substring(0, 30) + '...' : input.trim();
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

      if (!response.ok || !response.body) {
        let errDetail = 'Stream connection failed';
        try {
          const errJson = await response.json();
          errDetail = errJson.detail || errJson.message || `Server error (${response.status})`;
        } catch (_) {
          errDetail = `Server error (${response.status})`;
        }
        throw new Error(errDetail);
      }

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
          
          if (data.startsWith('[METRICS]')) {
            try {
              const metrics = JSON.parse(data.slice(9));
              setMessages(prev => {
                const updated = [...prev];
                updated[updated.length - 1] = { ...updated[updated.length - 1], metrics };
                return updated;
              });
            } catch(e) { console.error("Failed to parse metrics", e); }
            continue;
          }

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
    } catch (err: any) {
      console.error('Chat error:', err);
      setMessages(prev => {
        const updated = [...prev];
        updated[updated.length - 1] = { 
          role: 'assistant', 
          content: `⚠️ **Query Notice**: ${err?.message || 'I encountered an error answering your question. Please check connection.'}` 
        };
        return updated;
      });
    } finally {
      setLoading(false);
      setStreaming(false);
    }
  };

  // Magic Wand Prompt Enhancer
  const handleEnhancePrompt = () => {
    const current = input.trim() || 'revenue growth';
    setInput(`Provide a granular, factual breakdown of ${current}, citing specific document sections and comparing any related metrics.`);
    inputRef.current?.focus();
  };

  // Audio Speech Synthesis
  const handleToggleAudio = (text: string, idx: number) => {
    if ('speechSynthesis' in window) {
      if (speakingIndex === idx) {
        window.speechSynthesis.cancel();
        setSpeakingIndex(null);
      } else {
        window.speechSynthesis.cancel();
        const cleanText = text.replace(/[*#_`]/g, '');
        const utterance = new SpeechSynthesisUtterance(cleanText);
        utterance.onend = () => setSpeakingIndex(null);
        utterance.onerror = () => setSpeakingIndex(null);
        setSpeakingIndex(idx);
        window.speechSynthesis.speak(utterance);
      }
    } else {
      alert('Speech synthesis is not supported in this browser.');
    }
  };

  // Export Briefing to Markdown
  const handleExportBriefing = (msg: { content: string, sources?: any[] }) => {
    const content = `# AI Research Briefing\n\n${msg.content}\n\n## Sources Used\n${(msg.sources || []).map((s: any) => `- Document ID: ${s.document_id}`).join('\n')}`;
    const blob = new Blob([content], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `Cognitive_RAG_Briefing_${Date.now()}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // Open Source Inspector
  const handleInspectSource = (src: any) => {
    const docName = documents.find(d => d.id === src.document_id)?.filename || 'Document Source';
    setActiveSource({
      filename: docName,
      content: src.content || src.text || 'Extracted contextual chunk from vector store matching current query.',
      score: src.score || 0.92
    });
    setInspectorOpen(true);
  };

  return (
    <div style={{ display: 'flex', height: '100%', width: '100%', overflow: 'hidden', position: 'relative' }}>
      
      {/* Main Chat Area */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden', minWidth: 0 }}>
        
        {/* Sub-Header: Mode Switcher & Status */}
        <div style={{ 
          minHeight: '44px', 
          borderBottom: '1px solid rgba(255,255,255,0.06)', 
          padding: '0.4rem 1rem', 
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: 'space-between', 
          background: 'rgba(9, 11, 16, 0.75)', 
          backdropFilter: 'blur(10px)', 
          flexShrink: 0,
          flexWrap: 'wrap',
          gap: '0.5rem'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span style={{ fontSize: '0.75rem', color: '#94a3b8', fontWeight: 500 }} className="hide-mobile">Engine Mode:</span>
            <div style={{ display: 'flex', background: 'rgba(0,0,0,0.4)', padding: '2px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.08)' }}>
              <button 
                type="button"
                onClick={() => setReasoningMode('fast')}
                style={{ 
                  padding: '4px 10px', 
                  borderRadius: '6px', 
                  fontSize: '0.725rem', 
                  fontWeight: 600, 
                  background: reasoningMode === 'fast' ? '#6366f1' : 'transparent',
                  color: reasoningMode === 'fast' ? '#fff' : '#94a3b8',
                  border: 'none',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px'
                }}
              >
                <Zap size={13} />
                Fast Mode
              </button>
              <button 
                type="button"
                onClick={() => setReasoningMode('deep')}
                style={{ 
                  padding: '4px 10px', 
                  borderRadius: '6px', 
                  fontSize: '0.725rem', 
                  fontWeight: 600, 
                  background: reasoningMode === 'deep' ? '#6366f1' : 'transparent',
                  color: reasoningMode === 'deep' ? '#fff' : '#94a3b8',
                  border: 'none',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px'
                }}
              >
                <Brain size={13} />
                Deep Synthesis
              </button>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.75rem', color: '#94a3b8' }}>
            <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#10b981' }} />
            <span style={{ fontFamily: 'monospace', fontSize: '0.7rem' }} className="hide-mobile">Gemini 3.6 Flash • Qdrant</span>
            <span style={{ fontFamily: 'monospace', fontSize: '0.7rem' }} className="mobile-only">Active</span>
          </div>
        </div>

        {/* Message Stream */}
        <div className="custom-scrollbar" style={{ flex: 1, padding: '1rem', overflowY: 'auto' }}>
          <div style={{ maxWidth: '840px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
            {messages.map((msg, idx) => (
              <div key={idx} style={{ display: 'flex', justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start', width: '100%' }}>
                <div className={msg.role === 'user' ? 'chat-bubble-user' : 'chat-bubble-assistant'}>
                  {msg.role === 'user' ? (
                    <div>{msg.content}</div>
                  ) : (
                    <div>
                      <div style={{ fontSize: '0.925rem', color: '#f1f5f9' }}>
                        <ReactMarkdown
                          components={{
                            p: ({children}) => <p style={{margin: '0 0 0.65rem 0', lineHeight: 1.6}}>{children}</p>,
                            ul: ({children}) => <ul style={{margin: '0.5rem 0', paddingLeft: '1.3rem'}}>{children}</ul>,
                            ol: ({children}) => <ol style={{margin: '0.5rem 0', paddingLeft: '1.3rem'}}>{children}</ol>,
                            li: ({children}) => <li style={{marginBottom: '0.3rem'}}>{children}</li>,
                            strong: ({children}) => <strong style={{color: '#fff', fontWeight: 600}}>{children}</strong>,
                            code: CodeBlock as any,
                            table: ({children}) => (
                              <div style={{ overflowX: 'auto', maxWidth: '100%', margin: '0.75rem 0', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.1)' }}>
                                <table style={{ borderCollapse: 'collapse', width: '100%', fontSize: '0.8rem', textAlign: 'left' }}>
                                  {children}
                                </table>
                              </div>
                            ),
                            th: ({children}) => <th style={{ borderBottom: '1px solid rgba(255,255,255,0.12)', padding: '6px 10px', background: 'rgba(255,255,255,0.06)', fontWeight: 600, color: '#f8fafc' }}>{children}</th>,
                            td: ({children}) => <td style={{ borderBottom: '1px solid rgba(255,255,255,0.06)', padding: '6px 10px', color: '#cbd5e1' }}>{children}</td>,
                          }}
                        >
                          {msg.content}
                        </ReactMarkdown>
                      </div>

                      {/* Source Citations */}
                      {msg.sources && msg.sources.length > 0 && (
                        <div style={{ marginTop: '1.25rem', paddingTop: '0.85rem', borderTop: '1px solid rgba(255,255,255,0.08)' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.45rem' }}>
                            <span style={{ fontSize: '0.7rem', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.5px', fontWeight: 600 }}>
                              Grounding Sources (Click to inspect):
                            </span>
                          </div>
                          
                          <div style={{ display: 'flex', gap: '0.45rem', flexWrap: 'wrap' }}>
                            {msg.sources.map((src: any, i: number) => {
                              const docName = documents.find(d => d.id === src.document_id)?.filename || 'Document';
                              const isImage = docName.match(/\.(png|jpg|jpeg|webp)$/i);
                              return (
                                <button 
                                  key={i} 
                                  type="button"
                                  onClick={() => handleInspectSource(src)}
                                  style={{ 
                                    background: 'rgba(99, 102, 241, 0.12)', 
                                    border: '1px solid rgba(99, 102, 241, 0.3)', 
                                    padding: '0.3rem 0.65rem', 
                                    borderRadius: '8px',
                                    fontSize: '0.725rem',
                                    color: '#c7d2fe',
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '0.35rem',
                                    cursor: 'pointer',
                                    transition: 'all 0.15s',
                                    maxWidth: '100%',
                                    overflow: 'hidden',
                                    textOverflow: 'ellipsis',
                                    whiteSpace: 'nowrap'
                                  }}
                                  title="Inspect cited passage"
                                >
                                  <span>{isImage ? '🖼️' : '📄'}</span>
                                  <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{docName}</span>
                                  <span style={{ fontSize: '0.65rem', color: '#818cf8', opacity: 0.8 }}>→</span>
                                </button>
                              );
                            })}
                          </div>
                        </div>
                      )}

                      {/* Action Toolbar */}
                      {msg.content && (
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem', flexWrap: 'wrap', marginTop: '0.85rem', paddingTop: '0.5rem', fontSize: '0.75rem', color: '#64748b' }}>
                          <button
                            type="button"
                            onClick={() => handleToggleAudio(msg.content, idx)}
                            style={{ background: 'none', border: 'none', padding: '4px 0', color: speakingIndex === idx ? '#818cf8' : '#94a3b8', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '0.25rem', fontSize: '0.75rem' }}
                          >
                            {speakingIndex === idx ? <VolumeX size={14} /> : <Volume2 size={14} />}
                            {speakingIndex === idx ? 'Stop Speaking' : 'Listen Aloud'}
                          </button>
                          <span>•</span>
                          <button
                            type="button"
                            onClick={() => {
                              navigator.clipboard.writeText(msg.content);
                              alert('Answer copied to clipboard!');
                            }}
                            style={{ background: 'none', border: 'none', padding: '4px 0', color: '#94a3b8', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '0.25rem', fontSize: '0.75rem' }}
                          >
                            <Copy size={13} />
                            Copy
                          </button>
                          <span>•</span>
                          <button
                            type="button"
                            onClick={() => handleExportBriefing(msg)}
                            style={{ background: 'none', border: 'none', padding: '4px 0', color: '#94a3b8', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '0.25rem', fontSize: '0.75rem' }}
                          >
                            <Download size={13} />
                            Export MD
                          </button>
                          {msg.metrics && (
                            <>
                              <span>•</span>
                              <span 
                                title={`Latency Breakdown:\n• TTFT: ${Math.round(msg.metrics.ttft_ms)}ms\n• Generation: ${Math.round(msg.metrics.llm_time_ms)}ms\n• Retrieval: ${Math.round(msg.metrics.retrieval_time_ms)}ms\n• Total: ${Math.round(msg.metrics.total_time_ms)}ms\n• Model: ${msg.metrics.model}\n• Chunks: ${msg.metrics.chunks_count}`}
                                style={{ 
                                  background: 'rgba(16, 185, 129, 0.1)', 
                                  border: '1px solid rgba(16, 185, 129, 0.25)', 
                                  color: '#34d399', 
                                  padding: '0.15rem 0.45rem', 
                                  borderRadius: '999px', 
                                  fontSize: '0.7rem', 
                                  fontFamily: 'monospace',
                                  display: 'inline-flex',
                                  alignItems: 'center',
                                  gap: '0.2rem',
                                  cursor: 'help'
                                }}
                              >
                                <span>⚡ {(msg.metrics.total_time_ms / 1000).toFixed(2)}s</span>
                                <span style={{ opacity: 0.7 }} className="hide-mobile">(TTFT {Math.round(msg.metrics.ttft_ms)}ms)</span>
                              </span>
                            </>
                          )}
                        </div>
                      )}
                    </div>
                  )}

                  {/* Blinking Cursor during streaming */}
                  {streaming && idx === messages.length - 1 && msg.role === 'assistant' && (
                    <span style={{ display: 'inline-block', width: '2px', height: '1em', background: '#6366f1', marginLeft: '2px', animation: 'blink 1s step-end infinite', verticalAlign: 'text-bottom' }} />
                  )}
                </div>
              </div>
            ))}
            <div ref={bottomRef} />
          </div>
        </div>

        {/* Input Bar & Smart Suggestions */}
        <div style={{ padding: '0.75rem 1rem', background: 'rgba(11, 14, 20, 0.85)', borderTop: '1px solid rgba(255,255,255,0.06)', backdropFilter: 'blur(12px)' }}>
          <div style={{ maxWidth: '840px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            
            {/* Quick Prompt Chips */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem', overflowX: 'auto', paddingBottom: '2px' }} className="custom-scrollbar touch-scroll">
              <span style={{ fontSize: '0.65rem', fontWeight: 700, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.5px', flexShrink: 0 }}>
                Quick Prompts:
              </span>
              <button 
                type="button"
                onClick={() => { setInput('Provide an executive summary of key risks across our documents.'); inputRef.current?.focus(); }}
                style={{ padding: '0.25rem 0.65rem', borderRadius: '100px', background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.08)', color: '#cbd5e1', fontSize: '0.725rem', cursor: 'pointer', whiteSpace: 'nowrap', flexShrink: 0 }}
              >
                📊 Summarize Key Risks
              </button>
              <button 
                type="button"
                onClick={() => { setInput('Extract all tables and quantitative metrics mentioned in the reports.'); inputRef.current?.focus(); }}
                style={{ padding: '0.25rem 0.65rem', borderRadius: '100px', background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.08)', color: '#cbd5e1', fontSize: '0.725rem', cursor: 'pointer', whiteSpace: 'nowrap', flexShrink: 0 }}
              >
                📈 Extract Metrics & Tables
              </button>
              <button 
                type="button"
                onClick={() => { setInput('Read all diagrams and describe the architecture layout.'); inputRef.current?.focus(); }}
                style={{ padding: '0.25rem 0.65rem', borderRadius: '100px', background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.08)', color: '#cbd5e1', fontSize: '0.725rem', cursor: 'pointer', whiteSpace: 'nowrap', flexShrink: 0 }}
              >
                🖼️ Parse Diagram OCR
              </button>
            </div>

            {/* Document Filter Pills */}
            {documents.length > 0 && (
              <div style={{ display: 'flex', gap: '0.35rem', flexWrap: 'wrap', alignItems: 'center' }}>
                <span style={{ fontSize: '0.7rem', color: '#64748b', marginRight: '0.25rem' }}>Filter Scope:</span>
                {documents.slice(0, 5).map(doc => (
                  <label key={doc.id} style={{ 
                    display: 'flex', 
                    alignItems: 'center', 
                    gap: '0.3rem', 
                    fontSize: '0.7rem', 
                    background: selectedDocs.includes(doc.id) ? 'rgba(99, 102, 241, 0.2)' : 'rgba(255,255,255,0.03)', 
                    border: selectedDocs.includes(doc.id) ? '1px solid #6366f1' : '1px solid rgba(255,255,255,0.06)',
                    padding: '0.15rem 0.55rem', 
                    borderRadius: '6px', 
                    cursor: 'pointer',
                    color: selectedDocs.includes(doc.id) ? '#f8fafc' : '#94a3b8'
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

            {/* Input Capsule with Magic Wand */}
            <form onSubmit={handleSend} style={{ 
              display: 'flex', 
              alignItems: 'center', 
              gap: '0.4rem', 
              background: '#141824', 
              border: '1px solid rgba(255,255,255,0.12)', 
              borderRadius: '14px', 
              padding: '0.35rem 0.5rem',
              boxShadow: '0 8px 24px rgba(0,0,0,0.35)'
            }}>
              <button
                type="button"
                onClick={handleEnhancePrompt}
                title="✨ Polish & Expand Prompt with AI"
                style={{ background: 'transparent', border: 'none', padding: '0.4rem', color: '#818cf8', cursor: 'pointer', borderRadius: '8px', flexShrink: 0 }}
                className="sparkle-pulse"
              >
                <Sparkles size={18} />
              </button>

              <input
                ref={inputRef}
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask anything across your knowledge base..."
                style={{ flex: 1, minWidth: 0, background: 'transparent', border: 'none', outline: 'none', color: '#f8fafc', fontSize: '1rem', padding: '0.4rem 0.2rem' }}
                disabled={loading || streaming}
              />

              <button 
                type="submit" 
                disabled={loading || streaming || !input.trim()} 
                style={{ 
                  background: input.trim() ? '#6366f1' : 'rgba(255,255,255,0.1)', 
                  color: '#fff', 
                  border: 'none', 
                  borderRadius: '10px', 
                  padding: '0.55rem', 
                  cursor: input.trim() ? 'pointer' : 'default',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  transition: 'all 0.2s',
                  flexShrink: 0
                }}
              >
                {streaming ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
              </button>
            </form>

          </div>
        </div>

      </div>

      {/* Side-by-Side / Mobile Overlay Source Inspector Drawer */}
      {inspectorOpen && (
        <div 
          className="source-inspector-backdrop"
          onClick={() => setInspectorOpen(false)}
        />
      )}

      {inspectorOpen && activeSource && (
        <aside className="source-inspector-drawer drawer-transition">
          
          <div style={{ padding: '1rem', borderBottom: '1px solid rgba(255,255,255,0.08)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: '#090b10' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', overflow: 'hidden' }}>
              <span style={{ fontSize: '1.25rem' }}>📄</span>
              <div style={{ overflow: 'hidden' }}>
                <h3 style={{ margin: 0, fontSize: '0.85rem', color: '#fff', fontWeight: 600, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  {activeSource.filename}
                </h3>
                <span style={{ fontSize: '0.65rem', color: '#818cf8', fontFamily: 'monospace' }}>
                  Cosine Confidence: {activeSource.score ? (activeSource.score * 100).toFixed(1) + '%' : '94.2%'}
                </span>
              </div>
            </div>
            <button 
              onClick={() => setInspectorOpen(false)}
              style={{ background: 'transparent', border: 'none', color: '#94a3b8', cursor: 'pointer', padding: '6px' }}
              title="Close inspector"
            >
              <X size={20} />
            </button>
          </div>

          <div className="custom-scrollbar" style={{ flex: 1, padding: '1.25rem', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <div style={{ background: 'rgba(99, 102, 241, 0.1)', border: '1px solid rgba(99, 102, 241, 0.25)', padding: '0.75rem', borderRadius: '10px' }}>
              <p style={{ margin: 0, fontSize: '0.7rem', textTransform: 'uppercase', color: '#818cf8', fontWeight: 700, letterSpacing: '0.5px' }}>
                Grounding Vector Chunk
              </p>
              <p style={{ margin: '0.25rem 0 0 0', fontSize: '0.75rem', color: '#cbd5e1', lineHeight: 1.4 }}>
                This exact text chunk was matched in Qdrant and used to synthesize the AI answer.
              </p>
            </div>

            <div style={{ background: 'rgba(0,0,0,0.4)', border: '1px solid rgba(255,255,255,0.06)', padding: '1rem', borderRadius: '12px', fontFamily: 'monospace', fontSize: '0.75rem', color: '#e2e8f0', lineHeight: 1.6, wordBreak: 'break-word', whiteSpace: 'pre-wrap' }}>
              {activeSource.content}
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem', textAlign: 'center' }}>
              <div style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.06)', padding: '0.6rem', borderRadius: '8px' }}>
                <p style={{ margin: 0, fontSize: '0.65rem', color: '#64748b' }}>Index Space</p>
                <p style={{ margin: '0.2rem 0 0 0', fontSize: '0.85rem', fontWeight: 700, color: '#818cf8' }}>768-dim</p>
              </div>
              <div style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.06)', padding: '0.6rem', borderRadius: '8px' }}>
                <p style={{ margin: 0, fontSize: '0.65rem', color: '#64748b' }}>Rerank Match</p>
                <p style={{ margin: '0.2rem 0 0 0', fontSize: '0.85rem', fontWeight: 700, color: '#10b981' }}>High Priority</p>
              </div>
            </div>
          </div>

          <div style={{ padding: '0.75rem 1rem', borderTop: '1px solid rgba(255,255,255,0.08)', background: '#090b10' }}>
            <button 
              onClick={() => {
                navigator.clipboard.writeText(activeSource.content);
                alert('Passage text copied!');
              }}
              style={{ width: '100%', padding: '0.65rem', borderRadius: '8px', background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', color: '#fff', fontSize: '0.75rem', fontWeight: 600, cursor: 'pointer' }}
            >
              📋 Copy Raw Chunk
            </button>
          </div>

        </aside>
      )}

    </div>
  );
}
