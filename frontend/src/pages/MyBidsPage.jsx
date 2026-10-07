import { useEffect, useState } from 'react';
import { ClipboardList, Trash2 } from 'lucide-react';

const EMPTY = { tender_no: '', title: '', entity: '', our_price: '', base_cost: '', typical_bid: '', bidders: '' };

const apiUrl = () => localStorage.getItem('api_url') || import.meta.env.VITE_API_URL || 'http://localhost:8000';
const headers = () => ({ 'Content-Type': 'application/json', 'Authorization': `Bearer ${localStorage.getItem('token')}` });

async function call(path, options = {}) {
  const res = await fetch(`${apiUrl()}/api/my-bids${path}`, { headers: headers(), ...options });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Request failed');
  return data;
}

const smallBtn = { padding: '4px 10px', border: '2px solid #000', background: '#fff', cursor: 'pointer', fontWeight: 600 };

const money = (v) => (v == null ? '-' : `OMR ${Number(v).toLocaleString()}`);
const num = (v) => (v === '' ? null : Number(v));

export default function MyBidsPage() {
  const [bids, setBids] = useState([]);
  const [stats, setStats] = useState(null);
  const [form, setForm] = useState(EMPTY);
  const [error, setError] = useState('');

  const refresh = () =>
    Promise.all([call('/'), call('/calibration')])
      .then(([list, cal]) => { setBids(list.data); setStats(cal); })
      .catch(e => setError(e.message));

  useEffect(() => { refresh(); }, []);

  const submit = async (e) => {
    e.preventDefault();
    setError('');
    try {
      await call('/', {
        method: 'POST',
        body: JSON.stringify({
          tender_no: form.tender_no,
          title: form.title,
          entity: form.entity || null,
          our_price: Number(form.our_price),
          base_cost: Number(form.base_cost),
          typical_bid: num(form.typical_bid),
          bidders: num(form.bidders),
        }),
      });
      setForm(EMPTY);
      refresh();
    } catch (err) {
      setError(err.message);
    }
  };

  const setResult = async (bid, result) => {
    let winning_price = null;
    if (result === 'lost') {
      const input = window.prompt('Winning price (OMR)? Leave blank if unknown.');
      if (input === null) return;
      winning_price = input.trim() === '' ? null : Number(input);
    }
    try {
      await call(`/${bid.id}/result`, { method: 'PATCH', body: JSON.stringify({ result, winning_price }) });
      refresh();
    } catch (err) {
      setError(err.message);
    }
  };

  const remove = async (bid) => {
    if (!window.confirm(`Delete the bid on ${bid.tender_no}?`)) return;
    try {
      await call(`/${bid.id}`, { method: 'DELETE' });
      refresh();
    } catch (err) {
      setError(err.message);
    }
  };

  const field = (key, label, props = {}) => (
    <div>
      <label className="form-label">{label}</label>
      <input className="form-input" value={form[key]} onChange={e => setForm({ ...form, [key]: e.target.value })} {...props} />
    </div>
  );

  return (
    <div>
      <div className="page-title" style={{ marginBottom: '32px', display: 'flex', alignItems: 'center', gap: '16px' }}>
        <ClipboardList size={40} color="var(--brand-primary)" />
        My Bids
      </div>

      {error && <div style={{ marginBottom: '16px', padding: '12px', border: '2px solid #000', background: '#fee2e2' }}>{error}</div>}

      <div className="erp-grid">
        <div className="erp-card" style={{ gridColumn: 'span 12' }}>
          <div className="erp-card-header">How well do P2W predictions match reality?</div>
          {stats && (
            <div style={{ padding: '16px 24px' }}>
              <div style={{ display: 'flex', gap: '32px', flexWrap: 'wrap', marginBottom: '16px' }}>
                <div><b>{stats.won}</b> won / <b>{stats.lost}</b> lost / {stats.pending} pending</div>
                <div>Real win rate: <b>{stats.win_rate == null ? '-' : `${stats.win_rate}%`}</b></div>
                <div>Avg predicted: <b>{stats.mean_predicted == null ? '-' : `${stats.mean_predicted}%`}</b></div>
                <div>Brier score: <b>{stats.brier ?? '-'}</b> <span style={{ color: 'var(--text-secondary)' }}>(lower is better; 0.25 = coin flip)</span></div>
                <div>Realised profit: <b>{money(stats.realised_profit)}</b></div>
              </div>
              {stats.buckets.length > 0 ? (
                <table className="erp-table">
                  <thead><tr><th>Predicted range</th><th>Bids</th><th>Avg predicted</th><th>Actually won</th></tr></thead>
                  <tbody>
                    {stats.buckets.map(b => (
                      <tr key={b.range}><td>{b.range}</td><td>{b.n}</td><td>{b.predicted}%</td><td>{b.actual}%</td></tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <div style={{ color: 'var(--text-secondary)' }}>
                  Log bids with a typical-bid estimate and record their results. Once some are settled, predicted vs actual win rates appear here.
                </div>
              )}
            </div>
          )}
        </div>

        <div className="erp-card" style={{ gridColumn: 'span 12' }}>
          <div className="erp-card-header">Log a bid you placed</div>
          <form onSubmit={submit} style={{ padding: '16px 24px', display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px', alignItems: 'end' }}>
            {field('tender_no', 'Tender No', { required: true })}
            {field('title', 'Title', { required: true })}
            {field('entity', 'Entity')}
            {field('bidders', 'Bidders (if known)', { type: 'number', min: 2 })}
            {field('our_price', 'Our Price (OMR)', { type: 'number', min: 0, step: 'any', required: true })}
            {field('base_cost', 'Base Cost (OMR)', { type: 'number', min: 0, step: 'any', required: true })}
            {field('typical_bid', 'Expected Typical Bid (OMR)', { type: 'number', min: 0, step: 'any' })}
            <button className="btn-primary" type="submit" style={{ height: '40px' }}>Log Bid</button>
          </form>
        </div>

        <div className="erp-card" style={{ gridColumn: 'span 12' }}>
          <div className="erp-card-header">Bid history</div>
          <table className="erp-table">
            <thead>
              <tr>
                <th style={{ paddingLeft: '32px' }}>Tender</th><th>Our price</th><th>Cost</th>
                <th>Predicted win</th><th>Result</th><th>Winning price</th><th style={{ paddingRight: '32px' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {bids.length === 0 && (
                <tr><td colSpan={7} style={{ padding: '24px 32px', color: 'var(--text-secondary)' }}>No bids logged yet.</td></tr>
              )}
              {bids.map(b => (
                <tr key={b.id}>
                  <td style={{ paddingLeft: '32px' }}>
                    <div style={{ fontWeight: 600 }}>{b.tender_no}</div>
                    <div style={{ color: 'var(--text-secondary)', maxWidth: '260px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{b.title}</div>
                  </td>
                  <td>{money(b.our_price)}</td>
                  <td>{money(b.base_cost)}</td>
                  <td>{b.predicted_probability == null ? '-' : `${b.predicted_probability}%`}</td>
                  <td style={{ fontWeight: 600, textTransform: 'uppercase' }}>{b.result}</td>
                  <td>{money(b.winning_price)}</td>
                  <td style={{ paddingRight: '32px', display: 'flex', gap: '8px' }}>
                    {b.result === 'pending' && (
                      <>
                        <button style={smallBtn} onClick={() => setResult(b, 'won')}>Won</button>
                        <button style={smallBtn} onClick={() => setResult(b, 'lost')}>Lost</button>
                      </>
                    )}
                    {b.result !== 'pending' && (
                      <button style={smallBtn} onClick={() => setResult(b, 'pending')}>Reopen</button>
                    )}
                    <button style={smallBtn} onClick={() => remove(b)} aria-label="Delete bid"><Trash2 size={14} /></button>
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
