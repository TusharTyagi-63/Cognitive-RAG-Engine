import { useState } from 'react';
import type { FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { api } from '../api/client';

export function LoginPage() {
  const [isSignUp, setIsSignUp] = useState(false);
  const [email, setEmail] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    
    try {
      if (isSignUp) {
        // Register the user
        await api.post('/auth/register', {
          email,
          username,
          password
        });
      }

      // Log them in (either after signup or just logging in directly)
      const formData = new URLSearchParams();
      formData.append('username', username);
      formData.append('password', password);
      
      const response = await api.post('/auth/login', formData, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
      });
      
      login(response.data.access_token);
      navigate('/');
    } catch (err: any) {
      if (err.response?.data?.detail) {
        // Handle FastAPI validation errors dynamically
        if (Array.isArray(err.response.data.detail)) {
          setError(err.response.data.detail[0].msg);
        } else if (typeof err.response.data.detail === 'object') {
          setError(JSON.stringify(err.response.data.detail));
        } else {
          setError(err.response.data.detail);
        }
      } else {
        setError(isSignUp ? 'Registration failed.' : 'Login failed. Please check credentials.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: '100vh', padding: '1rem' }}>
      <form onSubmit={handleSubmit} className="glass-panel login-card">
        <div style={{ textAlign: 'center', marginBottom: '1rem' }}>
          <h2 style={{ margin: 0, fontSize: '2rem' }}>{isSignUp ? 'Create Account' : 'Welcome Back'}</h2>
          <p style={{ color: 'var(--text-muted)' }}>{isSignUp ? 'Sign up to start chatting' : 'Log in to access your RAG documents'}</p>
        </div>

        {isSignUp && (
          <input 
            type="email" 
            placeholder="Email Address" 
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
        )}

        <input 
          type="text" 
          placeholder="Username" 
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          required
        />
        
        <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
          <input 
            type={showPassword ? "text" : "password"} 
            placeholder="Password" 
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            style={{ width: '100%', paddingRight: '2.5rem' }}
          />
          <button 
            type="button"
            onClick={() => setShowPassword(!showPassword)}
            style={{ 
              position: 'absolute', 
              right: '0.75rem', 
              background: 'none', 
              border: 'none', 
              padding: 0, 
              color: 'var(--text-muted)',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}
            title={showPassword ? "Hide password" : "Show password"}
          >
            {showPassword ? (
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path><line x1="1" y1="1" x2="23" y2="23"></line></svg>
            ) : (
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path><circle cx="12" cy="12" r="3"></circle></svg>
            )}
          </button>
        </div>

        {error && <div style={{ color: '#ef4444', fontSize: '0.875rem' }}>{error}</div>}

        <button type="submit" style={{ marginTop: '1rem' }} disabled={loading}>
          {loading ? (isSignUp ? 'Creating...' : 'Logging In...') : (isSignUp ? 'Sign Up' : 'Log In')}
        </button>

        <div style={{ textAlign: 'center', marginTop: '1rem', fontSize: '0.875rem' }}>
          <button 
            type="button" 
            onClick={() => { setIsSignUp(!isSignUp); setError(''); }}
            style={{ background: 'none', border: 'none', color: 'var(--text-muted)', textDecoration: 'underline', padding: 0 }}
          >
            {isSignUp ? 'Already have an account? Log In' : 'Need an account? Sign Up'}
          </button>
        </div>
      </form>
    </div>
  );
}
