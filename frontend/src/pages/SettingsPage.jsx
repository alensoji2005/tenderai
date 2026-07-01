import { useEffect, useState } from 'react';
import { Settings, Database, Activity, RefreshCw } from 'lucide-react';

export default function SettingsPage() {
  const [scraperStats, setScraperStats] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchScraperStats = () => {
    const apiUrl = localStorage.getItem('api_url') || import.meta.env.VITE_API_URL || 'http://localhost:8000';
    const token = localStorage.getItem('token');
    
    setLoading(true);
    fetch(`${apiUrl}/api/stats/scraper`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
      .then(res => res.json())
      .then(data => {
        setScraperStats(data);
        setLoading(false);
      })
      .catch(err => {
        console.error(err);
        setLoading(false);
      });
  };

  useEffect(() => {
    fetchScraperStats();
    // Auto-refresh every 10 seconds while the page is open
    const interval = setInterval(fetchScraperStats, 10000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div>
      <div className="page-title" style={{ marginBottom: '32px', display: 'flex', alignItems: 'center', gap: '16px' }}>
        <Settings size={40} color="var(--brand-primary)" />
        System Settings
      </div>

      <div className="erp-grid">
        <div className="erp-card" style={{ gridColumn: 'span 12' }}>
          <div className="erp-card-header">
            <Activity size={20} />
            Background Jobs: Oman Tender Scraper
          </div>

          <div style={{ padding: '24px', background: '#F9F9F9', border: '2px solid #000' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '14px', fontWeight: 600 }}>
                Data Collection Progress
              </div>
              <button 
                className="btn-primary" 
                style={{ padding: '8px 16px', fontSize: '12px' }}
                onClick={fetchScraperStats}
              >
                <RefreshCw size={14} className={loading ? 'spin' : ''} />
                Refresh
              </button>
            </div>

            {scraperStats ? (
              <>
                <div style={{ width: '100%', height: '24px', background: '#FFF', border: '2px solid #000', position: 'relative' }}>
                  <div 
                    style={{ 
                      width: `${scraperStats.progress_percent}%`, 
                      height: '100%', 
                      background: 'var(--brand-primary)',
                      transition: 'width 0.5s ease-in-out'
                    }} 
                  />
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '8px', fontSize: '12px', fontFamily: 'JetBrains Mono, monospace' }}>
                  <span>{scraperStats.total_scraped.toLocaleString()} Records</span>
                  <span>{scraperStats.target.toLocaleString()} Target</span>
                </div>
                
                <div style={{ marginTop: '24px', padding: '16px', border: '1px dashed #000', background: '#FFF' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--status-green)', fontWeight: 600, fontSize: '12px', fontFamily: 'JetBrains Mono, monospace' }}>
                    <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--status-green)' }} />
                    SCRAPER IS ACTIVE
                  </div>
                  <p style={{ marginTop: '8px', fontSize: '14px', color: 'var(--text-secondary)' }}>
                    The historical data scraper is currently running in the background. It is continually pulling awarded tender details from the Oman Tender Board. Machine learning model training is scheduled to begin once the target dataset is acquired.
                  </p>
                </div>
              </>
            ) : (
              <div style={{ padding: '20px', textAlign: 'center' }}>Loading scraper stats...</div>
            )}
          </div>
        </div>

        <div className="erp-card" style={{ gridColumn: 'span 6' }}>
          <div className="erp-card-header">
            <Database size={20} />
            Database Connection
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div>
              <label className="form-label">Host</label>
              <input type="text" className="form-input" value="localhost" readOnly disabled style={{ background: '#EFEFEF' }} />
            </div>
            <div>
              <label className="form-label">Port</label>
              <input type="text" className="form-input" value="5432" readOnly disabled style={{ background: '#EFEFEF' }} />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
