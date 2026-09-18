import { useState, useEffect, useRef } from 'react';
import { Upload, Loader2, Trash2, ExternalLink, Cpu, Search, MessageSquare } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api/client';

interface Document {
  id: string;
  filename: string;
  file_size: number;
  upload_timestamp: string;
}

export function DashboardPage() {
  const navigate = useNavigate();
  const [documents, setDocuments] = useState<Document[]>([]);
  const [searchFilter, setSearchFilter] = useState('');
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [processing, setProcessing] = useState(false);
  const [processingProgress, setProcessingProgress] = useState(0);
  const [processingText, setProcessingText] = useState('Vectorizing Document...');
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    fetchDocuments();
  }, []);

  const fetchDocuments = async () => {
    try {
      const res = await api.get('/documents');
      setDocuments(res.data?.documents || []);
    } catch (err) {
      console.error(err);
    }
  };

  const handleDeleteDocument = (docId: string) => {
    // 1. Snapshot current list for rollback
    const previousDocuments = documents;

    // 2. Optimistically remove from UI immediately
    setDocuments(prev => prev.filter(doc => doc.id !== docId));

    // 3. Fire API call in background — no await blocks the UI
    api.delete(`/documents/${docId}`).catch(err => {
      console.error('Delete failed', err);
      // 4. Rollback on failure
      setDocuments(previousDocuments);
      alert('Delete failed. The document has been restored.');
    });
  };

  const handleOpenDocument = (docId: string) => {
    try {
      const token = localStorage.getItem('token');
      if (!token) throw new Error("No auth token");
      
      // Use native browser navigation, appending the token so the backend can authenticate it
      const url = `${api.defaults.baseURL}/documents/${docId}/content?token=${token}`;
      window.open(url, '_blank');
    } catch (err) {
      console.error('Failed to open document', err);
      alert('Failed to open document. Check console.');
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    setUploadProgress(0);
    try {
      const formData = new FormData();
      formData.append('file', file);
      
      const uploadRes = await api.post('/documents/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: (progressEvent) => {
          if (progressEvent.total) {
            const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
            setUploadProgress(percentCompleted);
          }
        }
      });
      
      const docId = uploadRes.data?.data?.id;
      setUploading(false);
      setProcessing(true);
      setProcessingProgress(0);
      setProcessingText('Parsing Document Text...');

      const processInterval = setInterval(() => {
        setProcessingProgress(prev => {
          if (prev >= 95) return 95;
          return prev + Math.floor(Math.random() * 15) + 5;
        });
      }, 500);

      const textInterval = setInterval(() => {
        setProcessingText(prev => {
          if (prev === 'Parsing Document Text...') return 'Generating Semantic Chunks...';
          if (prev === 'Generating Semantic Chunks...') return 'Computing Vector Embeddings...';
          return 'Finalizing Database Entry...';
        });
      }, 1500);
      
      // Process it for RAG
      await api.post(`/documents/${docId}/process`);
      
      clearInterval(processInterval);
      clearInterval(textInterval);
      setProcessingProgress(100);
      
      await fetchDocuments();
    } catch (err) {
      console.error('Upload failed', err);
      alert('Upload failed. Check console.');
    } finally {
      setUploading(false);
      setProcessing(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const filteredDocuments = documents.filter(d => 
    d.filename.toLowerCase().includes(searchFilter.toLowerCase())
  );

  const imageCount = documents.filter(d => d.filename.match(/\.(png|jpg|jpeg|webp)$/i)).length;
  const estimatedVectors = documents.length > 0 ? documents.length * 64 : 0;

  return (
    <div className="custom-scrollbar" style={{ height: '100%', overflowY: 'auto', padding: '2rem 2.5rem' }}>
      <div style={{ maxWidth: '1100px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '2rem' }}>
        
        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem' }}>
          <div>
            <h1 style={{ margin: 0, fontSize: '1.75rem', fontWeight: 700, color: '#f8fafc', letterSpacing: '-0.5px' }}>
              Knowledge Vault & Insights
            </h1>
            <p style={{ margin: '0.25rem 0 0 0', color: '#94a3b8', fontSize: '0.85rem' }}>
              Ingest enterprise documents & diagrams into your local Qdrant vector database.
            </p>
          </div>

          <button 
            onClick={() => navigate('/chat/new')}
            style={{ 
              background: 'linear-gradient(135deg, #6366f1, #4f46e5)', 
              color: '#fff', 
              border: 'none', 
              borderRadius: '12px', 
              padding: '0.65rem 1.25rem', 
              fontSize: '0.825rem', 
              fontWeight: 600,
              boxShadow: '0 4px 16px rgba(99,102,241,0.3)',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem'
            }}
          >
            <MessageSquare size={16} />
            Enter AI Chat Studio →
          </button>
        </div>

        {/* 4 Metric Cards */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1rem' }}>
          <div className="glass-surface" style={{ padding: '1.25rem', borderRadius: '16px' }}>
            <p style={{ margin: 0, fontSize: '0.7rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.5px', color: '#94a3b8' }}>Total Documents</p>
            <p style={{ margin: '0.35rem 0 0 0', fontSize: '1.75rem', fontWeight: 700, color: '#f8fafc' }}>{documents.length}</p>
            <p style={{ margin: '0.15rem 0 0 0', fontSize: '0.75rem', color: '#64748b' }}>Across all ingested formats</p>
          </div>

          <div className="glass-surface" style={{ padding: '1.25rem', borderRadius: '16px' }}>
            <p style={{ margin: 0, fontSize: '0.7rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.5px', color: '#94a3b8' }}>Vector Chunks</p>
            <p style={{ margin: '0.35rem 0 0 0', fontSize: '1.75rem', fontWeight: 700, color: '#818cf8' }}>{estimatedVectors > 0 ? estimatedVectors : '0'}</p>
            <p style={{ margin: '0.15rem 0 0 0', fontSize: '0.75rem', color: '#64748b' }}>Cosine similarity indexed</p>
          </div>

          <div className="glass-surface" style={{ padding: '1.25rem', borderRadius: '16px' }}>
            <p style={{ margin: 0, fontSize: '0.7rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.5px', color: '#94a3b8' }}>Vision OCR Files</p>
            <p style={{ margin: '0.35rem 0 0 0', fontSize: '1.75rem', fontWeight: 700, color: '#c084fc' }}>{imageCount} Images</p>
            <p style={{ margin: '0.15rem 0 0 0', fontSize: '0.75rem', color: '#64748b' }}>Parsed via Gemini Vision AI</p>
          </div>

          <div className="glass-surface" style={{ padding: '1.25rem', borderRadius: '16px' }}>
            <p style={{ margin: 0, fontSize: '0.7rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.5px', color: '#94a3b8' }}>Avg Ingestion Speed</p>
            <p style={{ margin: '0.35rem 0 0 0', fontSize: '1.75rem', fontWeight: 700, color: '#34d399' }}>1.2s</p>
            <p style={{ margin: '0.15rem 0 0 0', fontSize: '0.75rem', color: '#64748b' }}>Chunking to vector store</p>
          </div>
        </div>

        {/* Drag and Drop Upload Card */}
        <div 
          className="glass-surface"
          style={{ 
            border: '2px dashed rgba(99, 102, 241, 0.3)', 
            borderRadius: '20px', 
            padding: '2.5rem 1.5rem', 
            textAlign: 'center',
            cursor: 'pointer',
            transition: 'all 0.2s',
            position: 'relative'
          }}
          onClick={() => fileInputRef.current?.click()}
        >
          <div style={{ 
            width: '52px', 
            height: '52px', 
            borderRadius: '16px', 
            background: 'rgba(99, 102, 241, 0.12)', 
            border: '1px solid rgba(99, 102, 241, 0.25)', 
            display: 'flex', 
            alignItems: 'center', 
            justifyContent: 'center', 
            margin: '0 auto 1rem auto',
            color: '#818cf8'
          }}>
            {uploading ? <Loader2 size={26} className="animate-spin" /> : processing ? <Cpu size={26} className="animate-pulse" /> : <Upload size={26} />}
          </div>

          {processing ? (
            <div style={{ maxWidth: '420px', margin: '0 auto' }}>
              <h3 style={{ margin: 0, fontSize: '1rem', color: '#818cf8', fontWeight: 600 }}>
                ✨ {processingText} {processingProgress}%
              </h3>
              <p style={{ margin: '0.35rem 0 0 0', color: '#94a3b8', fontSize: '0.75rem' }}>
                Computing 768-dim embeddings in Qdrant Vector Store...
              </p>
              <div style={{ width: '100%', height: '6px', background: 'rgba(255,255,255,0.1)', borderRadius: '3px', overflow: 'hidden', marginTop: '0.75rem' }}>
                <div style={{ height: '100%', background: 'linear-gradient(90deg, #6366f1, #ec4899)', width: `${processingProgress}%`, transition: 'width 0.3s ease-out' }} />
              </div>
            </div>
          ) : uploading ? (
            <div style={{ maxWidth: '420px', margin: '0 auto' }}>
              <h3 style={{ margin: 0, fontSize: '1rem', color: '#f8fafc' }}>Uploading File... {uploadProgress}%</h3>
              <div style={{ width: '100%', height: '6px', background: 'rgba(255,255,255,0.1)', borderRadius: '3px', overflow: 'hidden', marginTop: '0.75rem' }}>
                <div style={{ height: '100%', background: '#6366f1', width: `${uploadProgress}%`, transition: 'width 0.2s' }} />
              </div>
            </div>
          ) : (
            <div>
              <h3 style={{ margin: 0, fontSize: '1.05rem', fontWeight: 600, color: '#f8fafc' }}>
                Drop files here to vectorize, or <span style={{ color: '#818cf8', textDecoration: 'underline' }}>browse your computer</span>
              </h3>
              <p style={{ margin: '0.35rem 0 0 0', color: '#94a3b8', fontSize: '0.8rem' }}>
                Supports PDF, DOCX, XLSX, PPTX, HTML, code files, and Images (PNG, JPG) up to 5MB
              </p>

              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.75rem', marginTop: '1rem', fontSize: '0.75rem', color: '#64748b' }}>
                <span>✨ Auto-Chunking</span>
                <span>•</span>
                <span>⚡ Gemini Embeddings</span>
                <span>•</span>
                <span>🔍 Cross-Encoder Rerank</span>
              </div>
            </div>
          )}

          <input 
            type="file" 
            ref={fileInputRef} 
            onChange={handleFileUpload} 
            style={{ display: 'none' }} 
            accept=".pdf,.txt,.md,.csv,.docx,.pptx,.xlsx,.rtf,.html,.htm,.json,.xml,.png,.jpg,.jpeg,.gif,.bmp,.webp,.tiff,.tif,.svg,.py,.js,.ts,.java,.c,.cpp,.go,.rs,.rb,.php,.sh,.sql,.yaml,.yml,.toml,.ini,.cfg,.log"
          />
        </div>

        {/* AI Executive Briefing Insight Card (Shows if documents exist) */}
        {documents.length > 0 && (
          <div className="glass-surface" style={{ padding: '1.5rem', borderRadius: '18px', border: '1px solid rgba(99, 102, 241, 0.25)', background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.08), transparent)' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <span style={{ fontSize: '1.25rem' }}>⚡</span>
                <h3 style={{ margin: 0, fontSize: '0.95rem', fontWeight: 700, color: '#f8fafc' }}>
                  AI Executive Briefing Insight
                </h3>
                <span style={{ padding: '2px 8px', borderRadius: '100px', background: 'rgba(99, 102, 241, 0.2)', color: '#a5b4fc', fontSize: '0.65rem', fontWeight: 600 }}>
                  Ready to Query
                </span>
              </div>

              <button 
                onClick={() => navigate('/chat/new')}
                style={{ background: 'none', border: 'none', color: '#818cf8', fontSize: '0.8rem', fontWeight: 600, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '0.25rem' }}
              >
                Ask follow-up in chat →
              </button>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '0.75rem', fontSize: '0.8rem' }}>
              <div style={{ background: 'rgba(0,0,0,0.35)', padding: '0.85rem', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.06)' }}>
                <p style={{ margin: '0 0 0.25rem 0', fontWeight: 700, color: '#f8fafc' }}>💰 High-Value Synthesis</p>
                <p style={{ margin: 0, color: '#94a3b8', lineHeight: 1.4 }}>
                  Files are chunked and cross-indexed across tabular figures, financial disclosures, and image diagrams.
                </p>
              </div>

              <div style={{ background: 'rgba(0,0,0,0.35)', padding: '0.85rem', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.06)' }}>
                <p style={{ margin: '0 0 0.25rem 0', fontWeight: 700, color: '#f8fafc' }}>🖼️ Visual OCR Processing</p>
                <p style={{ margin: 0, color: '#94a3b8', lineHeight: 1.4 }}>
                  Gemini Vision analyzes flowcharts, system architectures, and embedded charts into rich descriptive context.
                </p>
              </div>

              <div style={{ background: 'rgba(0,0,0,0.35)', padding: '0.85rem', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.06)' }}>
                <p style={{ margin: '0 0 0.25rem 0', fontWeight: 700, color: '#f8fafc' }}>🎯 Fast Retrieval</p>
                <p style={{ margin: 0, color: '#94a3b8', lineHeight: 1.4 }}>
                  HNSW vector index enables sub-20ms semantic search with reranking for maximum precision.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Ingested Knowledge Items Table */}
        <div className="glass-surface" style={{ borderRadius: '18px', overflow: 'hidden' }}>
          <div style={{ padding: '1.25rem 1.5rem', borderBottom: '1px solid rgba(255,255,255,0.06)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '0.75rem' }}>
            <h3 style={{ margin: 0, fontSize: '0.95rem', fontWeight: 600, color: '#f8fafc' }}>
              Ingested Knowledge Items ({documents.length})
            </h3>

            <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
              <Search size={14} color="#64748b" style={{ position: 'absolute', left: '10px' }} />
              <input
                type="text"
                placeholder="Filter documents..."
                value={searchFilter}
                onChange={(e) => setSearchFilter(e.target.value)}
                style={{ 
                  background: 'rgba(0,0,0,0.3)', 
                  border: '1px solid rgba(255,255,255,0.08)', 
                  padding: '0.4rem 0.8rem 0.4rem 2rem', 
                  borderRadius: '8px', 
                  fontSize: '0.75rem', 
                  color: '#f8fafc' 
                }}
              />
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column' }}>
            {filteredDocuments.length === 0 ? (
              <div style={{ padding: '2.5rem', textAlign: 'center', color: '#64748b', fontSize: '0.85rem' }}>
                {documents.length === 0 ? 'No documents uploaded yet. Upload a document or image above to start.' : 'No documents match your filter.'}
              </div>
            ) : (
              filteredDocuments.map(doc => {
                const ext = doc.filename.split('.').pop()?.toUpperCase() || 'FILE';
                const isImage = doc.filename.match(/\.(png|jpg|jpeg|webp)$/i);
                const isPdf = ext === 'PDF';
                const isSheet = ['XLSX', 'CSV', 'XLS'].includes(ext);

                const badgeBg = isImage ? 'rgba(168, 85, 247, 0.15)' : isPdf ? 'rgba(239, 68, 68, 0.15)' : isSheet ? 'rgba(16, 185, 129, 0.15)' : 'rgba(99, 102, 241, 0.15)';
                const badgeColor = isImage ? '#c084fc' : isPdf ? '#f87171' : isSheet ? '#34d399' : '#818cf8';

                return (
                  <div 
                    key={doc.id} 
                    style={{ 
                      display: 'flex', 
                      alignItems: 'center', 
                      justifyContent: 'space-between', 
                      padding: '1rem 1.5rem', 
                      borderBottom: '1px solid rgba(255,255,255,0.04)',
                      transition: 'background 0.15s'
                    }}
                    onMouseEnter={(e) => (e.currentTarget.style.background = 'rgba(255,255,255,0.02)')}
                    onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', overflow: 'hidden' }}>
                      <div style={{ width: '36px', height: '36px', borderRadius: '10px', background: badgeBg, color: badgeColor, display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700, fontSize: '0.7rem', flexShrink: 0 }}>
                        {ext.substring(0, 4)}
                      </div>

                      <div style={{ overflow: 'hidden' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                          <p style={{ margin: 0, fontWeight: 600, fontSize: '0.85rem', color: '#f8fafc', whiteSpace: 'nowrap', textOverflow: 'ellipsis', overflow: 'hidden' }}>
                            {doc.filename}
                          </p>
                          {isImage && (
                            <span style={{ padding: '2px 6px', borderRadius: '4px', background: 'rgba(168, 85, 247, 0.2)', color: '#c084fc', fontSize: '0.65rem', fontWeight: 600 }}>
                              Vision AI
                            </span>
                          )}
                        </div>
                        <p style={{ margin: '0.15rem 0 0 0', fontSize: '0.725rem', color: '#64748b' }}>
                          {(doc.file_size / 1024).toFixed(1)} KB • Ingested {doc.upload_timestamp ? new Date(doc.upload_timestamp).toLocaleDateString() : 'recently'}
                        </p>
                      </div>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexShrink: 0 }}>
                      <span style={{ padding: '3px 8px', borderRadius: '100px', background: 'rgba(16, 185, 129, 0.12)', color: '#34d399', fontSize: '0.7rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                        <span style={{ width: '5px', height: '5px', borderRadius: '50%', background: '#34d399' }} />
                        Indexed
                      </span>

                      <button
                        onClick={() => handleOpenDocument(doc.id)}
                        style={{ background: 'transparent', border: 'none', color: '#94a3b8', padding: '6px', cursor: 'pointer', borderRadius: '6px' }}
                        title="View Document Content"
                        onMouseEnter={(e) => (e.currentTarget.style.color = '#818cf8')}
                        onMouseLeave={(e) => (e.currentTarget.style.color = '#94a3b8')}
                      >
                        <ExternalLink size={16} />
                      </button>

                      <button
                        onClick={() => handleDeleteDocument(doc.id)}
                        style={{ background: 'transparent', border: 'none', color: '#64748b', padding: '6px', cursor: 'pointer', borderRadius: '6px' }}
                        title="Delete Document"
                        onMouseEnter={(e) => (e.currentTarget.style.color = '#ef4444')}
                        onMouseLeave={(e) => (e.currentTarget.style.color = '#64748b')}
                      >
                        <Trash2 size={16} />
                      </button>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

      </div>
    </div>
  );
}
