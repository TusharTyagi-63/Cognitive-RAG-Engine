import { useEffect, useState } from 'react';
import { Outlet, Link, useNavigate, useLocation } from 'react-router-dom';
import { MessageSquare, Home, LogOut, Trash2 } from 'lucide-react';
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

  useEffect(() => {
    api.get('/chat/sessions').then(res => setSessions(res.data?.data || [])).catch(console.error);
  }, [location.pathname]);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const handleDeleteSession = async (e: React.MouseEvent, id: string) => {
    e.preventDefault();
    e.stopPropagation();
    try {
      await api.delete(`/chat/sessions/${id}`);
      setSessions(sessions.filter(s => s.id !== id));
      if (location.pathname === `/chat/${id}`) {
        navigate('/chat/new');
      }
    } catch (err) {
      console.error('Delete session failed', err);
    }
  };

  return (
    <div style={{ display: 'flex', width: '100%', height: '100vh' }}>
      {/* Sidebar */}
      <aside style={{ width: '250px', background: 'rgba(0, 0, 0, 0.4)', borderRight: '1px solid var(--border)', display: 'flex', flexDirection: 'column', transition: 'all 0.3s ease' }}>
        <div style={{ padding: '2rem 1.5rem', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
          <h1 style={{ margin: 0, fontSize: '1.25rem', fontWeight: 700, background: 'linear-gradient(135deg, var(--primary), var(--primary-light))', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', letterSpacing: '-0.5px' }}>
          Cognitive RAG Engine
          </h1>
        </div>
        
        <nav style={{ flex: 1, marginTop: '2rem', display: 'flex', flexDirection: 'column', gap: '0.5rem', overflowY: 'auto' }}>
          <Link to="/" style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', padding: '0.75rem 1rem', borderRadius: '8px', color: 'var(--text-main)', background: location.pathname === '/' ? 'rgba(99, 102, 241, 0.1)' : 'transparent', border: location.pathname === '/' ? '1px solid var(--border-glow)' : '1px solid transparent', transition: 'all 0.2s' }}>
            <Home size={20} color={location.pathname === '/' ? 'var(--primary)' : 'var(--text-muted)'} />
            Dashboard
          </Link>
          <Link to="/chat/new" style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', padding: '0.75rem 1rem', borderRadius: '8px', color: 'var(--text-main)', background: location.pathname === '/chat/new' ? 'rgba(99, 102, 241, 0.1)' : 'transparent', border: location.pathname === '/chat/new' ? '1px solid var(--border-glow)' : '1px solid transparent', transition: 'all 0.2s' }}>
            <MessageSquare size={20} color={location.pathname === '/chat/new' ? 'var(--primary)' : 'var(--text-muted)'} />
            New Chat
          </Link>

          <div style={{ marginTop: '1rem', borderTop: '1px solid var(--border)', paddingTop: '1rem', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            {sessions.map(s => (
              <div key={s.id} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Link to={`/chat/${s.id}`} style={{ 
                  flex: 1,
                  display: 'block', 
                  whiteSpace: 'nowrap', 
                  overflow: 'hidden', 
                  textOverflow: 'ellipsis', 
                  padding: '0.5rem 1rem', 
                  borderRadius: '8px', 
                  color: location.pathname === `/chat/${s.id}` ? 'var(--primary)' : 'var(--text-muted)',
                  background: location.pathname === `/chat/${s.id}` ? 'rgba(99, 102, 241, 0.05)' : 'transparent',
                  border: location.pathname === `/chat/${s.id}` ? '1px solid var(--border-glow)' : '1px solid transparent',
                  fontSize: '0.875rem',
                  transition: 'all 0.2s'
                }}>
                  {s.title}
                </Link>
                <button
                  onClick={(e) => handleDeleteSession(e, s.id)}
                  style={{ background: 'transparent', padding: '4px', color: 'var(--text-muted)' }}
                  title="Delete chat"
                >
                  <Trash2 size={16} />
                </button>
              </div>
            ))}
          </div>
        </nav>

        <button 
          onClick={handleLogout}
          style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', background: 'transparent', color: 'var(--text-muted)' }}>
          <LogOut size={20} />
          Logout
        </button>
      </aside>

      {/* Main Content */}
      <main style={{ flex: 1, overflowY: 'auto', padding: '2rem' }}>
        <Outlet />
      </main>
    </div>
  );
}
