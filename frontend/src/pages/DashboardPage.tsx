import { useState, useEffect, useRef } from 'react';
import { Upload, FileText, Loader2, CheckCircle, Trash2, ExternalLink, Cpu, Sparkles, Database } from 'lucide-react';
import { api } from '../api/client';

interface Document {
  id: string;
  filename: string;
  file_size: number;
  upload_timestamp: string;
}

export function DashboardPage() {
  const [documents, setDocuments] = useState<Document[]>([]);
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

  return (
    <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
      <header className="dashboard-header">
        <h1 className="text-gradient" style={{ fontSize: '2.5rem', margin: '0 0 0.5rem 0' }}>Dashboard</h1>
        <p style={{ color: 'var(--text-muted)', margin: 0 }}>Manage your documents and start chatting with the RAG engine.</p>
      </header>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '2rem' }}>
        {/* Upload Card */}
        <div className="glass-panel upload-card-padding" style={{ padding: '3rem 2rem', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '1.5rem', border: '2px dashed var(--border-light)', background: 'rgba(0,0,0,0.2)' }}>
          <div style={{ padding: '1rem', background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.2), rgba(236, 72, 153, 0.2))', borderRadius: '50%', color: 'var(--primary)', boxShadow: processing ? '0 0 30px rgba(236, 72, 153, 0.4)' : '0 0 20px rgba(99, 102, 241, 0.2)', transition: 'box-shadow 0.3s ease' }}>
            {uploading ? <Loader2 size={32} className="animate-spin" /> : processing ? <Cpu size={32} className="animate-pulse" color="var(--accent)" /> : <Upload size={32} />}
          </div>
          <div style={{ textAlign: 'center', width: '100%' }}>
            {processing ? (
              <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '0.5rem', width: '100%' }}>
                <h3 className="text-gradient animate-pulse" style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '0.5rem', justifyContent: 'center' }}>
                  <Sparkles size={20} /> {processingText} {processingProgress}%
                </h3>
                <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem', margin: 0, display: 'flex', alignItems: 'center', gap: '0.5rem', justifyContent: 'center' }}>
                  <Database size={14} className="animate-spin" style={{ animationDuration: '3s' }} /> Embedding in Qdrant Vector DB
                </p>
                <div style={{ width: '100%', height: '6px', background: 'rgba(255,255,255,0.1)', borderRadius: '3px', overflow: 'hidden', marginTop: '0.75rem', boxShadow: 'inset 0 1px 2px rgba(0,0,0,0.5), 0 0 10px rgba(236, 72, 153, 0.3)' }}>
                  <div style={{ height: '100%', background: 'linear-gradient(90deg, var(--accent), var(--primary))', width: `${processingProgress}%`, transition: 'width 0.3s ease-out', boxShadow: '0 0 10px var(--primary)' }} />
                </div>
              </div>
            ) : (
              <>
                <h3 style={{ margin: '0 0 0.5rem 0' }}>
                  {uploading ? 'Uploading...' : 'Upload Document'}
                </h3>
                {uploading && (
                  <div style={{ width: '100%', height: '6px', background: 'rgba(255,255,255,0.1)', borderRadius: '3px', overflow: 'hidden', marginTop: '0.75rem', boxShadow: 'inset 0 1px 2px rgba(0,0,0,0.5), 0 0 10px rgba(99, 102, 241, 0.3)' }}>
                    <div style={{ height: '100%', background: 'linear-gradient(90deg, var(--primary), var(--accent))', width: `${uploadProgress}%`, transition: 'width 0.2s', boxShadow: '0 0 10px var(--accent)' }} />
                  </div>
                )}
                <p style={{ margin: '0.5rem 0 0 0', color: 'var(--text-muted)', fontSize: '0.875rem' }}>Supports PDF, Word, PPT, Excel, HTML, JSON, code files & more (up to 10MB).</p>
              </>
            )}
          </div>
          
          <input 
            type="file" 
            ref={fileInputRef} 
            onChange={handleFileUpload} 
            style={{ display: 'none' }} 
            accept=".pdf,.txt,.md,.csv,.docx,.pptx,.xlsx,.rtf,.html,.htm,.json,.xml,.py,.js,.ts,.java,.c,.cpp,.go,.rs,.rb,.php,.sh,.sql,.yaml,.yml,.toml,.ini,.cfg,.log"
          />
          <button 
            onClick={() => fileInputRef.current?.click()} 
            disabled={uploading || processing}
            style={{ marginTop: '1rem' }}
          >
            Select File
          </button>
        </div>

        {/* Stats Card */}
        <div className="glass-panel" style={{ padding: '2rem' }}>
          <h3 style={{ margin: '0 0 1.5rem 0' }}>Your Documents</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {documents.length === 0 ? (
              <p style={{ color: 'var(--text-muted)' }}>No documents uploaded yet.</p>
            ) : (
              documents.map(doc => (
                <div key={doc.id} className="glass-card" style={{ display: 'flex', alignItems: 'center', gap: '1rem', padding: '1rem', cursor: 'default' }}>
                  <div style={{ background: 'rgba(99, 102, 241, 0.1)', padding: '0.5rem', borderRadius: '8px' }}>
                    <FileText size={20} color="var(--primary)" />
                  </div>
                  <div style={{ flex: 1, overflow: 'hidden' }}>
                    <p style={{ margin: 0, whiteSpace: 'nowrap', textOverflow: 'ellipsis', overflow: 'hidden', fontWeight: 500 }}>{doc.filename}</p>
                    <p style={{ margin: 0, fontSize: '0.75rem', color: 'var(--text-muted)' }}>{(doc.file_size / 1024).toFixed(1)} KB</p>
                  </div>
                  <CheckCircle size={16} color="#10b981" style={{ opacity: 0.8 }} />
                  <button 
                    onClick={() => handleOpenDocument(doc.id)}
                    style={{ background: 'transparent', padding: '6px', color: 'var(--primary)', border: '1px solid transparent' }}
                    title="Open document"
                    onMouseEnter={(e) => { e.currentTarget.style.background = 'rgba(99, 102, 241, 0.1)'; }}
                    onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; }}
                  >
                    <ExternalLink size={16} />
                  </button>
                  <button 
                    onClick={() => handleDeleteDocument(doc.id)}
                    style={{ background: 'transparent', padding: '6px', color: 'var(--text-muted)', border: '1px solid transparent' }}
                    title="Delete document"
                    onMouseEnter={(e) => { e.currentTarget.style.color = '#ef4444'; e.currentTarget.style.background = 'rgba(239, 68, 68, 0.1)'; }}
                    onMouseLeave={(e) => { e.currentTarget.style.color = 'var(--text-muted)'; e.currentTarget.style.background = 'transparent'; }}
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
