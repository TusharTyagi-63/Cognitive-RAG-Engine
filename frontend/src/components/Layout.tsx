import { useEffect, useState } from 'react';
import { Outlet, Link, useNavigate, useLocation } from 'react-router-dom';
import { MessageSquare, Home, LogOut, Trash2, Menu, X } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { api } from '../api/client';

interface Session {
  id: string;
  title: string;
  updated_at: string;
}

export function Layout() {
  const { logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [sessions, setSessions] = useState<Session[]>([]);
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false);

  // Close sidebar on navigation (mobile)
  useEffect(() => {
    setIsMobileSidebarOpen(false);
  }, [location.pathname]);

  useEffect(() => {
    // Only refetch when we actually navigate to a new session (not on every route change)
    if (location.pathname.startsWith('/chat/') && location.pathname !== '/chat/new') {
      // A new session was just created, refresh the list
      api.get('/chat/sessions').then(res => setSessions(res.data?.data || [])).catch(console.error);
    }
  }, [location.pathname]);

  // Initial load
  useEffect(() => {
    api.get('/chat/sessions').then(res => setSessions(res.data?.data || [])).catch(console.error);
  }, []);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const handleDeleteSession = (e: React.MouseEvent, id: string) => {
    e.preventDefault();
    e.stopPropagation();

    // Optimistic UI: update immediately, then sync with server
    const previousSessions = sessions;
    setSessions(sessions.filter(s => s.id !== id));
    if (location.pathname === `/chat/${id}`) {
      navigate('/chat/new');
    }

    // Fire API call in the background; rollback on failure
    api.delete(`/chat/sessions/${id}`).catch(err => {
      console.error('Delete session failed, rolling back', err);
      setSessions(previousSessions);
    });
  };

  return (
    <div className="layout-container" style={{ background: '#090b10' }}>
      {/* Mobile Header (Only visible on small screens) */}
      <div className="mobile-header" style={{ background: '#0d1017', borderBottom: '1px solid rgba(255,255,255,0.08)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <div style={{ width: '24px', height: '24px', borderRadius: '6px', background: 'linear-gradient(135deg, #6366f1, #8b5cf6)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <MessageSquare size={14} color="#fff" />
          </div>
          <h1 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 700, color: '#f8fafc', letterSpacing: '-0.3px' }}>
            Cognitive RAG
          </h1>
        </div>
        <button 
          onClick={() => setIsMobileSidebarOpen(true)}
          style={{ background: 'transparent', padding: '0.5rem', border: 'none', cursor: 'pointer' }}
        >
          <Menu size={22} color="var(--text-main)" />
        </button>
      </div>

      {/* Sidebar Overlay (Mobile) */}
      <div 
        className={`sidebar-overlay ${isMobileSidebarOpen ? 'open' : ''}`} 
        onClick={() => setIsMobileSidebarOpen(false)}
      />

      {/* Sidebar */}
      <aside className={`sidebar ${isMobileSidebarOpen ? 'open' : ''}`} style={{ width: '260px', background: '#0b0e14', borderRight: '1px solid rgba(255,255,255,0.06)' }}>
        <div style={{ padding: '1.25rem 1.25rem', borderBottom: '1px solid rgba(255,255,255,0.06)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
            <div style={{ width: '28px', height: '28px', borderRadius: '8px', background: 'linear-gradient(135deg, #6366f1, #a855f7)', display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: '0 4px 12px rgba(99,102,241,0.35)' }}>
              <MessageSquare size={16} color="#fff" />
            </div>
            <div>
              <h1 style={{ margin: 0, fontSize: '0.95rem', fontWeight: 700, color: '#f8fafc', letterSpacing: '-0.3px', lineHeight: 1.2 }}>
                Cognitive RAG
              </h1>
              <span style={{ fontSize: '0.65rem', textTransform: 'uppercase', letterSpacing: '0.5px', color: '#818cf8', fontWeight: 600 }}>
                Enterprise Studio
              </span>
            </div>
          </div>
          {isMobileSidebarOpen && (
            <button 
              onClick={() => setIsMobileSidebarOpen(false)}
              style={{ background: 'transparent', padding: '0', border: 'none', cursor: 'pointer' }}
            >
              <X size={20} color="var(--text-muted)" />
            </button>
          )}
        </div>
        
        <div style={{ padding: '1rem 1rem 0 1rem' }}>
          <Link to="/chat/new" style={{ 
            display: 'flex', 
            alignItems: 'center', 
            justifyContent: 'center',
            gap: '0.5rem', 
            padding: '0.65rem 1rem', 
            borderRadius: '10px', 
            color: '#fff', 
            background: 'linear-gradient(135deg, #6366f1, #4f46e5)',
            boxShadow: '0 4px 14px rgba(99,102,241,0.3)',
            fontWeight: 600,
            fontSize: '0.825rem',
            transition: 'all 0.2s',
            textDecoration: 'none'
          }}>
            <MessageSquare size={16} />
            New Chat Session
          </Link>
        </div>

        <nav className="custom-scrollbar" style={{ flex: 1, marginTop: '1rem', padding: '0 0.75rem', display: 'flex', flexDirection: 'column', gap: '0.35rem', overflowY: 'auto' }}>
          <Link to="/" style={{ 
            display: 'flex', 
            alignItems: 'center', 
            gap: '0.75rem', 
            padding: '0.6rem 0.85rem', 
            borderRadius: '8px', 
            color: location.pathname === '/' ? '#f8fafc' : 'var(--text-muted)', 
            background: location.pathname === '/' ? 'rgba(99, 102, 241, 0.12)' : 'transparent', 
            border: location.pathname === '/' ? '1px solid rgba(99, 102, 241, 0.3)' : '1px solid transparent', 
            fontSize: '0.85rem',
            fontWeight: 500,
            transition: 'all 0.2s' 
          }}>
            <Home size={17} color={location.pathname === '/' ? '#818cf8' : '#94a3b8'} />
            Knowledge Vault
          </Link>

          <div style={{ marginTop: '0.75rem', borderTop: '1px solid rgba(255,255,255,0.06)', paddingTop: '0.75rem' }}>
            <div style={{ padding: '0 0.5rem 0.5rem 0.5rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '0.7rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.5px', color: '#64748b' }}>
                Recent Discussions
              </span>
              <span style={{ fontSize: '0.65rem', color: '#818cf8', fontWeight: 600 }}>{sessions.length}</span>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
              {sessions.length === 0 && (
                <p style={{ fontSize: '0.75rem', color: '#64748b', padding: '0.5rem', margin: 0 }}>
                  No active chats yet.
                </p>
              )}
              {sessions.map(s => (
                <div key={s.id} style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                  <Link to={`/chat/${s.id}`} style={{ 
                    flex: 1,
                    display: 'block', 
                    whiteSpace: 'nowrap', 
                    overflow: 'hidden', 
                    textOverflow: 'ellipsis', 
                    padding: '0.5rem 0.75rem', 
                    borderRadius: '8px', 
                    color: location.pathname === `/chat/${s.id}` ? '#f8fafc' : '#94a3b8',
                    background: location.pathname === `/chat/${s.id}` ? 'rgba(99, 102, 241, 0.15)' : 'rgba(255,255,255,0.02)',
                    border: location.pathname === `/chat/${s.id}` ? '1px solid rgba(99, 102, 241, 0.35)' : '1px solid rgba(255,255,255,0.03)',
                    fontSize: '0.8rem',
                    transition: 'all 0.15s'
                  }}>
                    💬 {s.title}
                  </Link>
                  <button
                    onClick={(e) => handleDeleteSession(e, s.id)}
                    style={{ background: 'transparent', border: 'none', padding: '6px', color: '#64748b', cursor: 'pointer', borderRadius: '6px' }}
                    title="Delete chat"
                    onMouseEnter={(e) => (e.currentTarget.style.color = '#ef4444')}
                    onMouseLeave={(e) => (e.currentTarget.style.color = '#64748b')}
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              ))}
            </div>
          </div>
        </nav>

        {/* User Profile & Status Footer */}
        <div style={{ padding: '0.85rem 1rem', borderTop: '1px solid rgba(255,255,255,0.06)', background: '#090b10', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
            <div style={{ width: '30px', height: '30px', borderRadius: '50%', background: 'linear-gradient(135deg, #ec4899, #8b5cf6)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700, fontSize: '0.75rem', color: '#fff' }}>
              CR
            </div>
            <div>
              <p style={{ margin: 0, fontSize: '0.8rem', fontWeight: 600, color: '#f8fafc', lineHeight: 1.2 }}>Account Active</p>
              <p style={{ margin: 0, fontSize: '0.65rem', color: '#10b981', display: 'flex', alignItems: 'center', gap: '0.3rem', fontWeight: 500 }}>
                <span style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: '#10b981', display: 'inline-block' }}></span> Cloud Connected
              </p>
            </div>
          </div>
          <button 
            onClick={handleLogout}
            style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)', color: '#94a3b8', padding: '0.45rem', borderRadius: '8px', cursor: 'pointer' }}
            title="Log Out"
          >
            <LogOut size={16} />
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="main-content" style={{ padding: 0, background: '#0d1017' }}>
        <Outlet />
      </main>
    </div>
  );
}
