import { useEffect, useState } from 'react';
import Predictor from '../components/Predictor';
import { Database, TrendingUp, Users } from 'lucide-react';

export default function DashboardPage() {
  const [tenders, setTenders] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const apiUrl = localStorage.getItem('api_url') || 'http://localhost:8000';
    const token = localStorage.getItem('token');
    
    fetch(`${apiUrl}/api/tenders?limit=5`, {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    })
      .then(res => {
        if (res.status === 401) {
          localStorage.removeItem('token');
          window.location.reload();
        }
        return res.json();
      })
      .then(data => {
        setTenders(data.data || []);
        setLoading(false);
      })
      .catch(err => {
        console.error(err);
        setLoading(false);
      });
  }, []);

  return (
    <div>
      <div className="erp-grid" style={{ marginBottom: '24px' }}>
        <div className="stat-card" style={{ gridColumn: 'span 4' }}>
          <div className="stat-label" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Database size={16} color="var(--brand-primary)" />
            Total Tenders
          </div>
          <div className="stat-value">304</div>
          <div style={{ fontSize: '12px', color: 'var(--status-green)', display: 'flex', alignItems: 'center', gap: '4px' }}>
            <TrendingUp size={12} /> +12 this week
          </div>
        </div>
        
        <div className="stat-card" style={{ gridColumn: 'span 4' }}>
          <div className="stat-label" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Users size={16} color="var(--brand-accent)" />
            Competitors Tracked
          </div>
          <div className="stat-value">142</div>
          <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
            Across all categories
          </div>
        </div>
        
        <div className="stat-card" style={{ gridColumn: 'span 4' }}>
          <div className="stat-label" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <TrendingUp size={16} color="var(--status-green)" />
            Avg Win Margin
          </div>
          <div className="stat-value">14.2%</div>
          <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
            Historical analysis
          </div>
        </div>
      </div>

      <div className="erp-grid">
        <Predictor />
        
        <div className="erp-card" style={{ gridColumn: 'span 8', marginBottom: 0 }}>
          <div className="erp-card-header">
            Recent Active Tenders
          </div>
          
          {loading ? (
            <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-secondary)' }}>Loading data...</div>
          ) : tenders.length === 0 ? (
            <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-secondary)' }}>
              No active tenders found.
            </div>
          ) : (
            <div style={{ overflowX: 'auto' }}>
              <table className="erp-table">
                <thead>
                  <tr>
                    <th>Tender ID</th>
                    <th>Title</th>
                    <th>Est. Value</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {tenders.map(t => (
                    <tr key={t.tender_id}>
                      <td style={{ fontWeight: 500, color: 'var(--brand-primary)' }}>{t.reference_number || t.tender_id.substring(0, 8)}</td>
                      <td style={{ maxWidth: '250px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                        {t.title}
                      </td>
                      <td>{t.estimated_value ? `OMR ${t.estimated_value.toLocaleString()}` : '-'}</td>
                      <td>
                        <span className={`status-badge ${t.status === 'active' ? 'status-active' : ''}`}>
                          {t.status.charAt(0).toUpperCase() + t.status.slice(1)}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
