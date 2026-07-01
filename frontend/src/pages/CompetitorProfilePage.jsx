import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Building2, AlertTriangle } from 'lucide-react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, Legend, ResponsiveContainer,
  PieChart, Pie, Cell
} from 'recharts';

const COLORS = ['#FF4D4D', '#333333', '#888888', '#CCCCCC', '#FF9999', '#444444', '#111111', '#555555'];

export default function CompetitorProfilePage() {
  const { companyName } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const apiUrl = localStorage.getItem('api_url') || import.meta.env.VITE_API_URL || 'http://localhost:8000';
    const token = localStorage.getItem('token');
    
    fetch(`${apiUrl}/api/competitors/${encodeURIComponent(companyName)}`, {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    })
      .then(res => {
        if (res.status === 401) {
          localStorage.removeItem('token');
          window.location.reload();
        }
        if (!res.ok) {
          throw new Error('Competitor not found');
        }
        return res.json();
      })
      .then(json => {
        setData(json);
        setLoading(false);
      })
      .catch(err => {
        console.error(err);
        setError(err.message);
        setLoading(false);
      });
  }, [companyName]);

  if (loading) {
    return <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-secondary)' }}>Loading profile data...</div>;
  }

  if (error || !data) {
    return (
      <div style={{ padding: '40px', textAlign: 'center' }}>
        <AlertTriangle size={48} color="var(--status-red)" style={{ marginBottom: '16px' }} />
        <h2 style={{ marginBottom: '16px' }}>{error || 'Competitor not found'}</h2>
        <button className="btn-primary" onClick={() => navigate('/competitors')}>Back to Leaderboard</button>
      </div>
    );
  }

  const { stats, history, entity_distribution } = data;
  const winRate = stats.total_bids > 0 ? ((stats.tenders_won / stats.total_bids) * 100).toFixed(1) : 0;

  // Prepare data for the Bar Chart
  const timeSeriesDataMap = {};
  history.forEach(bid => {
    if (!bid.awarded_date) return;
    const date = new Date(bid.awarded_date);
    const month = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;
    if (!timeSeriesDataMap[month]) {
      timeSeriesDataMap[month] = { month, won: 0, lost: 0 };
    }
    if (bid.is_winner) {
      timeSeriesDataMap[month].won += 1;
    } else {
      timeSeriesDataMap[month].lost += 1;
    }
  });
  const timeSeriesData = Object.values(timeSeriesDataMap).sort((a, b) => a.month.localeCompare(b.month));

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', gap: '16px', marginBottom: '24px' }}>
        <button 
          onClick={() => navigate('/competitors')} 
          style={{ background: 'none', border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text-secondary)' }}
        >
          <ArrowLeft size={16} /> Back
        </button>
        <h2 style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '12px' }}>
          <Building2 size={24} color="var(--brand-primary)" />
          {companyName}
        </h2>
      </div>

      <div className="erp-grid" style={{ marginBottom: '24px' }}>
        <div className="stat-card" style={{ gridColumn: 'span 3' }}>
          <div className="stat-label">Total Bids</div>
          <div className="stat-value">{stats.total_bids}</div>
        </div>
        <div className="stat-card" style={{ gridColumn: 'span 3' }}>
          <div className="stat-label">Tenders Won</div>
          <div className="stat-value" style={{ color: 'var(--status-green)' }}>{stats.tenders_won}</div>
        </div>
        <div className="stat-card" style={{ gridColumn: 'span 3' }}>
          <div className="stat-label">Win Rate</div>
          <div className="stat-value">{winRate}%</div>
        </div>
        <div className="stat-card" style={{ gridColumn: 'span 3' }}>
          <div className="stat-label">Total Won Amount</div>
          <div className="stat-value" style={{ fontSize: '20px' }}>
            {stats.total_won_amount ? `OMR ${(stats.total_won_amount / 1000000).toFixed(2)}M` : 'OMR 0'}
          </div>
        </div>
      </div>

      <div className="erp-grid" style={{ marginBottom: '24px' }}>
        <div className="erp-card" style={{ gridColumn: 'span 8' }}>
          <div className="erp-card-header">Bid Activity Trend (Wins vs Losses)</div>
          <div style={{ height: '300px', width: '100%' }}>
            {timeSeriesData.length > 0 ? (
              <ResponsiveContainer>
                <BarChart data={timeSeriesData} margin={{ top: 20, right: 30, left: 0, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="month" />
                  <YAxis />
                  <RechartsTooltip cursor={{fill: 'rgba(0,0,0,0.05)'}} />
                  <Legend />
                  <Bar dataKey="won" name="Won" stackId="a" fill="var(--status-green)" />
                  <Bar dataKey="lost" name="Lost" stackId="a" fill="#E0E0E0" />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-secondary)' }}>
                Not enough time-series data
              </div>
            )}
          </div>
        </div>

        <div className="erp-card" style={{ gridColumn: 'span 4' }}>
          <div className="erp-card-header">Top Government Entities Targetted</div>
          <div style={{ height: '300px', width: '100%' }}>
            {entity_distribution.length > 0 ? (
              <ResponsiveContainer>
                <PieChart>
                  <Pie
                    data={entity_distribution}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={80}
                    paddingAngle={2}
                    dataKey="value"
                  >
                    {entity_distribution.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <RechartsTooltip formatter={(value, name) => [`${value} bids`, name]} />
                  <Legend layout="horizontal" verticalAlign="bottom" align="center" wrapperStyle={{ fontSize: '10px' }} />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-secondary)' }}>
                No entity data
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="erp-card">
        <div className="erp-card-header">Recent Bid History</div>
        <div style={{ overflowX: 'auto' }}>
          <table className="erp-table">
            <thead>
              <tr>
                <th>Date</th>
                <th>Tender No.</th>
                <th>Entity</th>
                <th>Bid Amount</th>
                <th>Result</th>
              </tr>
            </thead>
            <tbody>
              {history.map((h, i) => (
                <tr key={i}>
                  <td>{h.awarded_date ? new Date(h.awarded_date).toLocaleDateString() : 'N/A'}</td>
                  <td style={{ fontFamily: '"JetBrains Mono", monospace' }}>{h.tender_no}</td>
                  <td style={{ maxWidth: '250px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{h.entity_name}</td>
                  <td style={{ fontFamily: '"JetBrains Mono", monospace' }}>{h.total_quoted_value ? `OMR ${h.total_quoted_value.toLocaleString()}` : '-'}</td>
                  <td>
                    <span className={`status-badge ${h.is_winner ? 'status-active' : ''}`} style={!h.is_winner ? { background: '#F5F5F5', color: '#666', border: '1px solid #CCC' } : {}}>
                      {h.is_winner ? 'WON' : 'LOST'}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
