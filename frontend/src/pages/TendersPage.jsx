import { useEffect, useState } from 'react';
import { FileText, AlertCircle, Eye, RefreshCw, Download, Search, Filter } from 'lucide-react';

export default function TendersPage() {
  const [tenders, setTenders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedTender, setSelectedTender] = useState(null);
  const [syncStatus, setSyncStatus] = useState({ status: 'idle', last_sync: null });
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [exporting, setExporting] = useState(false);

  const apiUrl = localStorage.getItem('api_url') || import.meta.env.VITE_API_URL || 'http://localhost:8000';
  const token = localStorage.getItem('token');

  const fetchSyncStatus = () => {
    fetch(`${apiUrl}/api/jobs/status`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
      .then(res => res.json())
      .then(data => setSyncStatus(data))
      .catch(console.error);
  };

  const fetchTenders = () => {
    setLoading(true);
    let url = `${apiUrl}/api/tenders?limit=50`;
    if (searchTerm) url += `&title_search=${encodeURIComponent(searchTerm)}`;
    if (statusFilter) url += `&status=${encodeURIComponent(statusFilter)}`;
    if (categoryFilter) url += `&category=${encodeURIComponent(categoryFilter)}`;

    fetch(url, { headers: { 'Authorization': `Bearer ${token}` } })
      .then(res => {
        if (res.status === 401) {
          localStorage.removeItem('token');
          window.location.reload();
        }
        return res.json();
      })
      .then(data => { setTenders(data.data || []); setLoading(false); })
      .catch(err => { console.error(err); setLoading(false); });
  };

  const handleExport = () => {
    setExporting(true);
    let url = `${apiUrl}/api/tenders?limit=0`;
    if (searchTerm) url += `&title_search=${encodeURIComponent(searchTerm)}`;
    if (statusFilter) url += `&status=${encodeURIComponent(statusFilter)}`;
    if (categoryFilter) url += `&category=${encodeURIComponent(categoryFilter)}`;

    fetch(url, { headers: { 'Authorization': `Bearer ${token}` } })
      .then(res => res.json())
      .then(data => {
        const rows = data.data || [];
        if (rows.length === 0) {
          alert("No data to export");
          setExporting(false);
          return;
        }
        
        const headers = ["Tender ID", "Title", "Category", "Status", "Estimated Value", "Closing Date"];
        const csvContent = [
          headers.join(","),
          ...rows.map(r => [
            `"${r.tender_id || ''}"`, 
            `"${(r.title || '').replace(/"/g, '""')}"`, 
            `"${r.category || ''}"`, 
            `"${r.status || ''}"`, 
            r.estimated_value || '', 
            `"${r.closing_date || ''}"`
          ].join(","))
        ].join("\\n");
        
        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement("a");
        link.href = URL.createObjectURL(blob);
        link.download = `tenders_export_${new Date().toISOString().split('T')[0]}.csv`;
        link.click();
        
        setExporting(false);
      })
      .catch(err => { console.error(err); setExporting(false); });
  };

  const triggerSync = () => {
    fetch(`${apiUrl}/api/jobs/sync`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}` }
    })
      .then(res => {
        if (res.ok) {
          alert("Sync started in the background! This may take several minutes.");
          fetchSyncStatus();
        } else {
          res.json().then(data => alert(data.detail || "Failed to start sync."));
        }
      })
      .catch(console.error);
  };

  useEffect(() => {
    fetchSyncStatus();
    fetchTenders();
  }, [searchTerm, statusFilter, categoryFilter]);

  return (
    <div>
      <div className="erp-card" style={{ padding: '0', overflow: 'hidden' }}>
        <div className="erp-card-header" style={{ padding: '24px 32px', marginBottom: 0, borderBottom: '1px solid var(--border-light)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <FileText size={20} />
            Tender Explorer
          </div>
          
          <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
            {syncStatus.last_sync && (
              <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                Last sync: {new Date(syncStatus.last_sync).toLocaleString()}
              </span>
            )}
            <button 
              onClick={triggerSync}
              disabled={syncStatus.status === 'running'}
              className="btn-secondary"
              style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '6px 12px', fontSize: '13px', opacity: syncStatus.status === 'running' ? 0.7 : 1 }}
            >
              <RefreshCw size={14} />
              {syncStatus.status === 'running' ? 'Syncing...' : 'Sync Now'}
            </button>
          </div>
        </div>
        
        <div style={{ padding: '16px 32px', display: 'flex', gap: '16px', borderBottom: '1px solid var(--border-light)', background: 'rgba(255,255,255,0.02)' }}>
          <div style={{ flex: 1, position: 'relative' }}>
            <Search size={16} style={{ position: 'absolute', left: '12px', top: '10px', color: 'var(--text-secondary)' }} />
            <input 
              type="text" 
              placeholder="Search by Title..." 
              className="form-input" 
              style={{ paddingLeft: '36px', height: '36px', margin: 0 }}
              value={searchTerm}
              onChange={e => setSearchTerm(e.target.value)}
            />
          </div>
          <select className="form-input" style={{ width: '160px', height: '36px', margin: 0 }} value={statusFilter} onChange={e => setStatusFilter(e.target.value)}>
            <option value="">All Statuses</option>
            <option value="active">Active</option>
            <option value="awarded">Awarded</option>
          </select>
          <select className="form-input" style={{ width: '160px', height: '36px', margin: 0 }} value={categoryFilter} onChange={e => setCategoryFilter(e.target.value)}>
            <option value="">All Categories</option>
            <option value="Construction">Construction</option>
            <option value="IT">IT</option>
            <option value="Consultancy">Consultancy</option>
            <option value="Supply">Supply</option>
          </select>
          <button className="btn-primary" style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '0 16px', height: '36px' }} onClick={handleExport} disabled={exporting}>
            <Download size={16} />
            {exporting ? 'Exporting...' : 'Export CSV'}
          </button>
        </div>
        
        {loading ? (
          <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-secondary)' }}>Loading data...</div>
        ) : tenders.length === 0 ? (
          <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-secondary)' }}>
            No tenders found.
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table className="erp-table">
              <thead>
                <tr>
                  <th style={{ paddingLeft: '32px' }}>Tender ID</th>
                  <th>Title</th>
                  <th>Type</th>
                  <th>Est. Value</th>
                  <th>Status</th>
                  <th style={{ paddingRight: '32px' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {tenders.map(t => (
                  <tr key={t.tender_id} style={{ cursor: 'pointer' }} onClick={() => setSelectedTender(t)}>
                    <td style={{ paddingLeft: '32px', fontWeight: 500, color: 'var(--brand-primary)' }}>
                      {t.reference_number || t.tender_id.substring(0, 8)}
                    </td>
                    <td style={{ maxWidth: '300px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {t.title}
                    </td>
                    <td style={{ color: 'var(--text-secondary)' }}>{t.contract_type || 'General'}</td>
                    <td>{t.estimated_value ? `OMR ${t.estimated_value.toLocaleString()}` : '-'}</td>
                    <td>
                      <span className={`status-badge ${t.status === 'active' ? 'status-active' : 'status-awarded'}`}>
                        {t.status.charAt(0).toUpperCase() + t.status.slice(1)}
                      </span>
                    </td>
                    <td style={{ paddingRight: '32px' }}>
                      <button style={{ background: 'transparent', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer' }}>
                        <Eye size={18} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Side Drawer for Tender Details */}
      {selectedTender && (
        <>
          <div 
            style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.5)', zIndex: 100 }}
            onClick={() => setSelectedTender(null)}
          />
          <div style={{ 
            position: 'fixed', top: 0, right: 0, bottom: 0, width: '500px', 
            background: 'var(--bg-surface-solid)', zIndex: 101,
            borderLeft: '1px solid var(--border-light)', boxShadow: '-10px 0 30px rgba(0,0,0,0.5)',
            padding: '32px', overflowY: 'auto'
          }}>
            <h2 style={{ fontSize: '20px', marginBottom: '8px', color: 'var(--text-primary)' }}>Tender Intelligence</h2>
            <div style={{ color: 'var(--brand-primary)', fontFamily: 'Outfit', fontWeight: 500, marginBottom: '24px' }}>
              {selectedTender.reference_number || selectedTender.tender_id}
            </div>
            
            <div style={{ marginBottom: '32px' }}>
              <div className="form-label">Title / Scope</div>
              <p style={{ color: 'var(--text-primary)', fontSize: '14px', lineHeight: 1.6 }}>{selectedTender.title}</p>
            </div>

            <div className="erp-card" style={{ padding: '20px', marginBottom: '24px' }}>
               <h3 style={{ fontSize: '14px', color: 'var(--text-secondary)', marginBottom: '16px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Bidding Competitors</h3>
               
               {!selectedTender.bids || selectedTender.bids.length === 0 ? (
                 <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text-secondary)', fontSize: '13px' }}>
                   <AlertCircle size={14} />
                   No competitor bids recorded for this tender.
                 </div>
               ) : (
                 <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                   {selectedTender.bids.map((bid, i) => (
                     <div key={i} style={{ 
                       display: 'flex', justifyContent: 'space-between', alignItems: 'center', 
                       padding: '12px 16px', background: bid.is_winner ? 'rgba(46, 160, 67, 0.1)' : 'rgba(255,255,255,0.03)', 
                       borderRadius: '8px', border: bid.is_winner ? '1px solid rgba(46, 160, 67, 0.3)' : '1px solid rgba(255,255,255,0.05)'
                     }}>
                       <div style={{ fontWeight: 500, color: bid.is_winner ? 'var(--status-green)' : 'var(--text-primary)' }}>
                         {bid.company_name}
                         {bid.is_winner && <span style={{ marginLeft: '8px', fontSize: '10px', padding: '2px 6px', background: 'var(--status-green)', color: 'white', borderRadius: '4px' }}>WINNER</span>}
                       </div>
                       <div style={{ fontFamily: 'Outfit', fontWeight: 600 }}>
                         OMR {bid.amount.toLocaleString()}
                       </div>
                     </div>
                   ))}
                 </div>
               )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
