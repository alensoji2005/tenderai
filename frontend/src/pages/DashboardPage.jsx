import { useEffect, useState } from 'react';
import Predictor from '../components/Predictor';
import { Database, TrendingUp, Users } from 'lucide-react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar } from 'recharts';

export default function DashboardPage() {
  const [tenders, setTenders] = useState([]);
  const [stats, setStats] = useState({
    total_tenders: 0,
    total_competitors: 0,
    avg_win_margin: 0,
    chart_data: [],
    top_entities: [],
    top_categories: []
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const apiUrl = localStorage.getItem('api_url') || import.meta.env.VITE_API_URL || 'http://localhost:8000';
    const token = localStorage.getItem('token');
    
    // Fetch Recent Tenders
    fetch(`${apiUrl}/api/tenders?limit=5`, {
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
        setTenders(data.data || []);
      })
      .catch(err => console.error(err));

    // Fetch Dashboard Stats
    fetch(`${apiUrl}/api/stats/dashboard`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
      .then(res => res.json())
      .then(data => {
        setStats(data);
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
          <div className="stat-value">{stats.total_tenders.toLocaleString()}</div>
          <div style={{ fontSize: '12px', color: 'var(--status-green)', display: 'flex', alignItems: 'center', gap: '4px' }}>
            <TrendingUp size={12} /> Live Scraped Data
          </div>
        </div>
        
        <div className="stat-card" style={{ gridColumn: 'span 4' }}>
          <div className="stat-label" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Users size={16} color="var(--brand-accent)" />
            Competitors Tracked
          </div>
          <div className="stat-value">{stats.total_competitors.toLocaleString()}</div>
          <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
            Across all categories
          </div>
        </div>
        
        <div className="stat-card" style={{ gridColumn: 'span 4' }}>
          <div className="stat-label" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <TrendingUp size={16} color="var(--status-green)" />
            Avg Win Margin
          </div>
          <div className="stat-value">{stats.avg_win_margin}%</div>
          <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
            Historical analysis
          </div>
        </div>
      </div>

      <div className="erp-grid" style={{ marginBottom: '24px' }}>
        {/* Tender Volume Chart */}
        <div className="erp-card" style={{ gridColumn: 'span 12', padding: '24px' }}>
          <div className="erp-card-header" style={{ marginBottom: '16px', borderBottom: 'none' }}>
            Awarded Tender Volume (Last 6 Months)
          </div>
          <div style={{ width: '100%', height: '300px' }}>
            <ResponsiveContainer>
              <AreaChart data={stats.chart_data} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorTenders" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="var(--brand-primary)" stopOpacity={0.8}/>
                    <stop offset="95%" stopColor="var(--brand-primary)" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <XAxis dataKey="name" stroke="#000" tick={{fontFamily: 'JetBrains Mono', fontSize: 12}} />
                <YAxis stroke="#000" tick={{fontFamily: 'JetBrains Mono', fontSize: 12}} />
                <CartesianGrid strokeDasharray="3 3" stroke="#ccc" />
                <Tooltip 
                  contentStyle={{ border: '2px solid #000', borderRadius: 0, fontFamily: 'JetBrains Mono' }}
                  itemStyle={{ color: '#000' }}
                />
                <Area type="monotone" dataKey="Tenders" stroke="var(--brand-primary)" strokeWidth={3} fillOpacity={1} fill="url(#colorTenders)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Top Entities Chart */}
        <div className="erp-card" style={{ gridColumn: 'span 6', padding: '24px' }}>
          <div className="erp-card-header" style={{ marginBottom: '16px', borderBottom: 'none' }}>
            Top Entities by Volume
          </div>
          <div style={{ width: '100%', height: '300px' }}>
            <ResponsiveContainer>
              <BarChart data={stats.top_entities} margin={{ top: 10, right: 30, left: 0, bottom: 0 }} layout="vertical">
                <XAxis type="number" stroke="#000" tick={{fontFamily: 'JetBrains Mono', fontSize: 12}} />
                <YAxis dataKey="name" type="category" stroke="#000" tick={{fontFamily: 'JetBrains Mono', fontSize: 10}} width={150} />
                <CartesianGrid strokeDasharray="3 3" stroke="#ccc" />
                <Tooltip contentStyle={{ border: '2px solid #000', borderRadius: 0, fontFamily: 'JetBrains Mono' }} />
                <Bar dataKey="count" fill="var(--brand-accent)" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
        
        {/* Top Categories Chart */}
        <div className="erp-card" style={{ gridColumn: 'span 6', padding: '24px' }}>
          <div className="erp-card-header" style={{ marginBottom: '16px', borderBottom: 'none' }}>
            Top Categories by Volume
          </div>
          <div style={{ width: '100%', height: '300px' }}>
            <ResponsiveContainer>
              <BarChart data={stats.top_categories} margin={{ top: 10, right: 30, left: 0, bottom: 0 }} layout="vertical">
                <XAxis type="number" stroke="#000" tick={{fontFamily: 'JetBrains Mono', fontSize: 12}} />
                <YAxis dataKey="name" type="category" stroke="#000" tick={{fontFamily: 'JetBrains Mono', fontSize: 10}} width={150} />
                <CartesianGrid strokeDasharray="3 3" stroke="#ccc" />
                <Tooltip contentStyle={{ border: '2px solid #000', borderRadius: 0, fontFamily: 'JetBrains Mono' }} />
                <Bar dataKey="count" fill="var(--brand-primary)" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
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
