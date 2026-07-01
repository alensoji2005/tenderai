import { useEffect, useState, useCallback } from 'react';
import { Users, Target, Building2, Search, Filter } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export default function CompetitorsPage() {
  const [competitors, setCompetitors] = useState([]);
  const [loading, setLoading] = useState(true);
  const [entities, setEntities] = useState([]);
  
  // Filters
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedEntity, setSelectedEntity] = useState('');
  
  const navigate = useNavigate();
  const apiUrl = localStorage.getItem('api_url') || import.meta.env.VITE_API_URL || 'http://localhost:8000';
  const token = localStorage.getItem('token');

  // Fetch Entities for dropdown
  useEffect(() => {
    fetch(`${apiUrl}/api/competitors/entities`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
      .then(res => res.json())
      .then(data => setEntities(data.data || []))
      .catch(err => console.error('Failed to fetch entities', err));
  }, [apiUrl, token]);

  // Fetch Competitors based on filters
  const fetchCompetitors = useCallback(() => {
    setLoading(true);
    let queryParams = new URLSearchParams();
    queryParams.append('limit', '50');
    if (searchQuery) queryParams.append('search', searchQuery);
    if (selectedEntity) queryParams.append('entity', selectedEntity);
    
    fetch(`${apiUrl}/api/competitors?${queryParams.toString()}`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
      .then(res => {
        if (res.status === 401) {
          localStorage.removeItem('token');
          window.location.reload();
        }
        return res.json();
      })
      .then(data => {
        setCompetitors(data.data || []);
        setLoading(false);
      })
      .catch(err => {
        console.error(err);
        setLoading(false);
      });
  }, [apiUrl, token, searchQuery, selectedEntity]);

  useEffect(() => {
    const delayDebounceFn = setTimeout(() => {
      fetchCompetitors();
    }, 300); // 300ms debounce

    return () => clearTimeout(delayDebounceFn);
  }, [fetchCompetitors]);

  return (
    <div>
      <div className="erp-grid" style={{ marginBottom: '24px' }}>
        <div className="stat-card" style={{ gridColumn: 'span 4' }}>
          <div className="stat-label" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Users size={16} color="var(--brand-primary)" />
            Top Competitors
          </div>
          <div className="stat-value">50+</div>
          <div style={{ fontSize: '12px', color: 'var(--status-green)', display: 'flex', alignItems: 'center', gap: '4px' }}>
            Tracked in live data
          </div>
        </div>
        
        <div className="stat-card" style={{ gridColumn: 'span 4' }}>
          <div className="stat-label" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Target size={16} color="var(--brand-accent)" />
            Entities Tracked
          </div>
          <div className="stat-value">{entities.length || '-'}</div>
          <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
            Across Oman
          </div>
        </div>
      </div>

      <div className="erp-card">
        <div className="erp-card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Building2 size={20} />
            Competitor Leaderboard
          </div>
          
          {/* Filters */}
          <div style={{ display: 'flex', gap: '16px', fontWeight: 'normal', fontSize: '14px' }}>
            <div style={{ position: 'relative' }}>
              <Search size={16} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: '#666' }} />
              <input 
                type="text" 
                placeholder="Search company..." 
                className="form-input" 
                style={{ paddingLeft: '36px', width: '200px' }}
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
              />
            </div>
            
            <div style={{ position: 'relative' }}>
              <Filter size={16} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: '#666' }} />
              <select 
                className="form-input" 
                style={{ paddingLeft: '36px', width: '200px', cursor: 'pointer' }}
                value={selectedEntity}
                onChange={e => setSelectedEntity(e.target.value)}
              >
                <option value="">All Entities</option>
                {entities.map((ent, idx) => (
                  <option key={idx} value={ent}>{ent}</option>
                ))}
              </select>
            </div>
          </div>
        </div>
        
        {loading ? (
          <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-secondary)' }}>Loading data...</div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table className="erp-table">
              <thead>
                <tr>
                  <th>Company Name</th>
                  <th>Total Bids</th>
                  <th>Tenders Won</th>
                  <th>Win Rate</th>
                  <th>Avg Win Amount</th>
                </tr>
              </thead>
              <tbody>
                {competitors.map((c, i) => {
                  const winRate = c.total_bids > 0 ? ((c.tenders_won / c.total_bids) * 100).toFixed(1) : 0;
                  return (
                    <tr 
                      key={i} 
                      onClick={() => navigate(`/competitors/${encodeURIComponent(c.company_name)}`)}
                      style={{ cursor: 'pointer' }}
                      className="hover-row"
                    >
                      <td style={{ fontWeight: 500, color: 'var(--brand-primary)', textDecoration: 'underline' }}>
                        {c.company_name}
                      </td>
                      <td>{c.total_bids}</td>
                      <td style={{ color: c.tenders_won > 0 ? 'var(--status-green)' : 'inherit' }}>
                        {c.tenders_won}
                      </td>
                      <td>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <span>{winRate}%</span>
                          <div style={{ flex: 1, maxWidth: '60px', height: '4px', background: 'rgba(255,255,255,0.1)', borderRadius: '2px' }}>
                            <div style={{ width: `${winRate}%`, height: '100%', background: 'var(--brand-primary)', borderRadius: '2px' }} />
                          </div>
                        </div>
                      </td>
                      <td style={{ fontFamily: '"JetBrains Mono", monospace' }}>
                        {c.avg_winning_amount ? `OMR ${(c.avg_winning_amount / 1000000).toFixed(2)}M` : '-'}
                      </td>
                    </tr>
                  );
                })}
                {competitors.length === 0 && (
                  <tr>
                    <td colSpan="5" style={{ textAlign: 'center', padding: '40px', color: 'var(--text-secondary)' }}>
                      No competitor data found matching your filters.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
