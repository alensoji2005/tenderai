import { HashRouter as Router, Routes, Route, NavLink, useLocation } from 'react-router-dom';
import { LayoutDashboard, FileText, BarChart3, Settings, Database, Search, Bell, X, Minus, Square } from 'lucide-react';
import DashboardPage from './pages/DashboardPage';
import CompetitorsPage from './pages/CompetitorsPage';
import CompetitorProfilePage from './pages/CompetitorProfilePage';
import TendersPage from './pages/TendersPage';
import { useEffect, useState } from 'react';

function TitleBar() {
  return (
    <div className="titlebar">
      <div className="titlebar-brand">
        <Database size={14} color="var(--brand-primary)" />
        TenderAI
      </div>
      <div className="titlebar-controls">
        <button className="titlebar-btn" onClick={() => window.api?.windowMin()}>
          <Minus size={16} />
        </button>
        <button className="titlebar-btn" onClick={() => window.api?.windowMax()}>
          <Square size={14} />
        </button>
        <button className="titlebar-btn close" onClick={() => window.api?.windowClose()}>
          <X size={16} />
        </button>
      </div>
    </div>
  );
}

function Sidebar() {
  return (
    <nav className="app-sidebar">
      <div style={{ padding: '0 16px', marginBottom: '24px', marginTop: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px', color: '#000' }}>
          <div style={{ 
            width: '40px', height: '40px', 
            background: 'var(--brand-primary)',
            border: '2px solid #000',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            boxShadow: '4px 4px 0px #000'
          }}>
            <Database size={20} color="white" />
          </div>
          <div>
            <div style={{ fontWeight: 700, fontSize: '18px', fontFamily: '"JetBrains Mono", monospace', textTransform: 'uppercase', letterSpacing: '-0.05em' }}>TenderAI</div>
            <div style={{ fontSize: '10px', color: 'var(--brand-primary)', fontWeight: 700, fontFamily: '"JetBrains Mono", monospace', letterSpacing: '0.1em' }}>ENTERPRISE</div>
          </div>
        </div>
      </div>

      <div className="nav-label">Main Menu</div>
      
      <NavLink to="/" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
        <LayoutDashboard size={18} />
        Dashboard
      </NavLink>
      <NavLink to="/tenders" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
        <FileText size={18} />
        Tenders
      </NavLink>
      <NavLink to="/competitors" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
        <BarChart3 size={18} />
        Competitors
      </NavLink>
      
      <div style={{ marginTop: 'auto' }}>
        <div style={{ padding: '16px', background: '#FFF', border: '2px solid #000', marginBottom: '16px', boxShadow: '4px 4px 0px #000' }}>
          <div style={{ fontSize: '10px', fontWeight: 700, fontFamily: '"JetBrains Mono", monospace', color: '#000', marginBottom: '8px', textTransform: 'uppercase', letterSpacing: '0.1em' }}>Backend Status</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '12px', fontWeight: 700, color: 'var(--status-green)', textTransform: 'uppercase' }}>
            <div style={{ width: '10px', height: '10px', background: 'var(--status-green)', border: '1px solid #000' }} />
            Connected
          </div>
        </div>
        
        <NavLink to="/settings" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
          <Settings size={18} />
          Settings
        </NavLink>
      </div>
    </nav>
  );
}

function TopHeader() {
  const location = useLocation();
  const getPageTitle = () => {
    switch (location.pathname) {
      case '/': return 'Overview';
      case '/tenders': return 'Tender Explorer';
      case '/competitors': return 'Competitor Intelligence';
      case '/settings': return 'System Settings';
      default: return 'Dashboard';
    }
  };

  return (
    <header style={{ 
      display: 'flex', justifyContent: 'space-between', alignItems: 'center', 
      marginBottom: '48px', paddingBottom: '24px', borderBottom: '2px solid #000' 
    }}>
      <h1 className="page-title" style={{ margin: 0 }}>{getPageTitle()}</h1>
      
      <div style={{ display: 'flex', alignItems: 'center', gap: '24px' }}>
        <div style={{ position: 'relative' }}>
          <Search size={16} style={{ position: 'absolute', left: '16px', top: '50%', transform: 'translateY(-50%)', color: '#000' }} />
          <input type="text" placeholder="Search data..." className="form-input" style={{ width: '300px', paddingLeft: '48px' }} />
        </div>
        
        <button style={{ background: '#FFF', border: '2px solid #000', color: '#000', cursor: 'pointer', position: 'relative', width: '48px', height: '48px', display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: '4px 4px 0px #000' }}>
          <Bell size={20} />
          <div style={{ position: 'absolute', top: '-4px', right: '-4px', width: '12px', height: '12px', background: 'var(--brand-primary)', border: '2px solid #000' }} />
        </button>
        
        <div style={{ 
          display: 'flex', alignItems: 'center', gap: '12px', 
          padding: '4px 16px 4px 4px', background: '#FFF', 
          border: '2px solid #000', cursor: 'pointer',
          boxShadow: '4px 4px 0px #000'
        }}>
          <div style={{ 
            width: '36px', height: '36px', 
            background: 'var(--brand-primary)', color: 'white', 
            border: '2px solid #000',
            display: 'flex', alignItems: 'center', justifyContent: 'center', 
            fontSize: '12px', fontWeight: 700, fontFamily: '"JetBrains Mono", monospace'
          }}>
            AD
          </div>
          <div style={{ fontSize: '12px', fontWeight: 700, color: '#000', textTransform: 'uppercase', fontFamily: '"JetBrains Mono", monospace' }}>Admin User</div>
        </div>
      </div>
    </header>
  );
}

function LoginScreen({ onLogin }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [showSettings, setShowSettings] = useState(false);
  const [apiUrl, setApiUrl] = useState(localStorage.getItem('api_url') || 'http://localhost:8000');

  const handleSaveSettings = () => {
    localStorage.setItem('api_url', apiUrl);
    setShowSettings(false);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    try {
      const formData = new URLSearchParams();
      formData.append('username', username);
      formData.append('password', password);
      
      const res = await fetch(`${apiUrl}/api/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: formData
      });
      
      if (!res.ok) {
        throw new Error('Invalid email or password');
      }
      
      const data = await res.json();
      localStorage.setItem('token', data.access_token);
      onLogin(data.access_token);
    } catch (err) {
      setError(err.message || 'Connection failed');
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', background: 'var(--bg-main)' }}>
      <TitleBar />
      <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', position: 'relative', overflow: 'hidden' }}>
        {/* Brutalist Background Pattern */}
        <div style={{ position: 'absolute', top: '-10%', left: '-5%', fontSize: '20vw', fontWeight: 700, color: '#000', opacity: 0.03, fontFamily: '"JetBrains Mono", monospace', pointerEvents: 'none' }}>SYS</div>
        
        <div className="erp-card" style={{ width: '420px', padding: '48px', zIndex: 1, background: '#FFF', position: 'relative' }}>
          <button 
            onClick={() => setShowSettings(!showSettings)}
            style={{ position: 'absolute', top: '16px', right: '16px', background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-secondary)' }}
          >
            ⚙️
          </button>
          
          <div style={{ textAlign: 'center', marginBottom: '40px' }}>
            <div style={{ 
              width: '64px', height: '64px', 
              background: 'var(--brand-primary)',
              border: '2px solid #000',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              boxShadow: '6px 6px 0px #000', margin: '0 auto 24px'
            }}>
              <Database size={32} color="white" />
            </div>
            <h2 style={{ fontSize: '32px', fontWeight: 700, marginBottom: '8px', textTransform: 'uppercase', letterSpacing: '-0.05em' }}>TenderAI</h2>
            <p className="text-secondary" style={{ fontSize: '12px', fontFamily: '"JetBrains Mono", monospace', textTransform: 'uppercase', letterSpacing: '0.1em', fontWeight: 700 }}>Authorized Access Only</p>
          </div>
          
          {error && (
            <div style={{ background: '#FFEBEB', border: '2px solid var(--status-red)', padding: '12px', marginBottom: '24px', color: 'var(--status-red)', fontSize: '12px', fontWeight: 700, fontFamily: '"JetBrains Mono", monospace', textTransform: 'uppercase' }}>
              {error}
            </div>
          )}
          
          {showSettings ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
              <div>
                <label className="form-label">Backend API URL</label>
                <input 
                  type="text" 
                  className="erp-input" 
                  value={apiUrl}
                  onChange={e => setApiUrl(e.target.value)}
                  placeholder="http://localhost:8000"
                />
              </div>
              <button className="btn-primary" onClick={handleSaveSettings}>Save Settings</button>
            </div>
          ) : (
            <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
              <div>
                <label className="form-label">Email Address</label>
                <input 
                  type="email" 
                  className="form-input" 
                  value={username}
                  onChange={e => setUsername(e.target.value)}
                  placeholder="USER@COMPANY.COM" 
                  required 
                />
              </div>
              <div>
                <label className="form-label">Password</label>
                <input 
                  type="password" 
                  className="form-input" 
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  placeholder="********" 
                  required 
                />
              </div>
              <button type="submit" className="btn-primary" style={{ marginTop: '16px', width: '100%', fontSize: '18px', padding: '20px' }}>
                INITIALIZE SESSION
              </button>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (token) {
      setIsAuthenticated(true);
    }
    setIsLoading(false);
  }, []);

  if (isLoading) return null;

  if (!isAuthenticated) {
    return <LoginScreen onLogin={() => setIsAuthenticated(true)} />;
  }

  return (
    <Router>
      <div className="app-container">
        <TitleBar />
        <div className="app-body">
          <Sidebar />
          <main className="main-content">
            <TopHeader />
            <Routes>
              <Route path="/" element={<DashboardPage />} />
              <Route path="/tenders" element={<TendersPage />} />
              <Route path="/competitors" element={<CompetitorsPage />} />
              <Route path="/competitors/:companyName" element={<CompetitorProfilePage />} />
            </Routes>
          </main>
        </div>
      </div>
    </Router>
  );
}

export default App;
