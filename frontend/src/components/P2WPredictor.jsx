import { useState } from 'react';
import { Crosshair, Zap, DollarSign, ShieldCheck, Flame } from 'lucide-react';

export default function P2WPredictor() {
  const [formData, setFormData] = useState({
    title: '',
    base_cost: '',
    estimated_value: '',
    target_probability: 95,
    entity: 'Ministry of Health',
    category: 'Construction',
    company_name: 'Oman Poles LLC'
  });
  const [prediction, setPrediction] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    
    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const res = await fetch(`${apiUrl}/api/ml/predict-p2w`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          base_cost: Number(formData.base_cost) || 100000,
          estimated_value: Number(formData.estimated_value) || 120000,
          target_probability: Number(formData.target_probability),
          title: formData.title,
          entity: formData.entity,
          category: formData.category,
          company_name: formData.company_name
        })
      });
      const data = await res.json();
      
      if (!res.ok) {
        throw new Error(data.detail || 'Prediction failed');
      }
      
      setTimeout(() => {
        setPrediction(data);
        setLoading(false);
      }, 600);
    } catch (err) {
      console.error(err);
      alert(err.message || 'An error occurred during prediction.');
      setLoading(false);
    }
  };

  const renderCard = (title, data, icon, color) => {
    if (!data) return null;
    return (
      <div style={{
        padding: '16px',
        backgroundColor: '#f8fafc',
        border: `1px solid ${color}`,
        borderRadius: '8px',
        display: 'flex',
        flexDirection: 'column',
        gap: '8px'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: color, fontWeight: 'bold' }}>
          {icon}
          <span>{title}</span>
        </div>
        <div>
          <span style={{ fontSize: '12px', color: '#64748b' }}>Recommended Bid</span>
          <div style={{ fontSize: '20px', fontWeight: 'bold', color: '#0f172a' }}>
            OMR {data.bid_price.toLocaleString()}
          </div>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '14px', marginTop: '8px' }}>
          <div>
            <span style={{ color: '#64748b' }}>Profit: </span>
            <span style={{ color: '#059669', fontWeight: 'bold' }}>OMR {data.profit.toLocaleString()}</span>
          </div>
          <div>
            <span style={{ color: '#64748b' }}>Win Prob: </span>
            <span style={{ color: '#2563eb', fontWeight: 'bold' }}>{data.win_probability}%</span>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="erp-card" style={{ gridColumn: 'span 6', backgroundColor: '#ffffff', border: '1px solid #e2e8f0', boxShadow: 'none' }}>
      <div className="erp-card-header" style={{ marginBottom: '16px' }}>
        <div style={{ width: '32px', height: '32px', borderRadius: '8px', backgroundColor: '#eff6ff', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#2563eb' }}>
          <Crosshair size={18} />
        </div>
        Price-to-Win (P2W) Recommender
      </div>
      
      <p style={{ color: '#475569', fontSize: '13px', marginBottom: '24px' }}>
        Input your base cost to simulate thousands of scenarios and find the exact bid price that maximizes profit at your target win probability.
      </p>

      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
        <div>
          <label className="form-label" style={{ color: '#1e293b' }}>Tender Title</label>
          <input 
            type="text" 
            className="form-input" 
            style={{ backgroundColor: '#ffffff', border: '1px solid #cbd5e1', color: '#0f172a' }}
            placeholder="e.g. Construction of Data Center..."
            value={formData.title}
            onChange={e => setFormData({...formData, title: e.target.value})}
            required
          />
        </div>
        
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
          <div>
            <label className="form-label" style={{ color: '#1e293b' }}>Base Cost (OMR)</label>
            <input 
              type="number" 
              className="form-input" 
              style={{ backgroundColor: '#ffffff', border: '1px solid #cbd5e1', color: '#0f172a' }}
              placeholder="100000"
              value={formData.base_cost}
              onChange={e => setFormData({...formData, base_cost: e.target.value})}
              required
            />
          </div>
          <div>
            <label className="form-label" style={{ color: '#1e293b' }}>Est. Official Value (OMR)</label>
            <input 
              type="number" 
              className="form-input" 
              style={{ backgroundColor: '#ffffff', border: '1px solid #cbd5e1', color: '#0f172a' }}
              placeholder="120000"
              value={formData.estimated_value}
              onChange={e => setFormData({...formData, estimated_value: e.target.value})}
              required
            />
          </div>
        </div>

        <div>
          <label className="form-label" style={{ color: '#1e293b' }}>
            Target Probability: <strong style={{ color: '#2563eb' }}>{formData.target_probability}%</strong>
          </label>
          <input 
            type="range" 
            min="50" 
            max="99" 
            step="1"
            style={{ width: '100%', marginTop: '8px' }}
            value={formData.target_probability}
            onChange={e => setFormData({...formData, target_probability: e.target.value})}
          />
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', color: '#64748b' }}>
            <span>50% (High Profit)</span>
            <span>99% (Low Profit)</span>
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '16px' }}>
          <div>
            <label className="form-label" style={{ color: '#1e293b' }}>Entity Name</label>
            <input 
              type="text" 
              className="form-input" 
              style={{ backgroundColor: '#ffffff', border: '1px solid #cbd5e1', color: '#0f172a' }}
              placeholder="e.g. Ministry of Health"
              value={formData.entity}
              onChange={e => setFormData({...formData, entity: e.target.value})}
              required
            />
          </div>
          <div>
            <label className="form-label" style={{ color: '#1e293b' }}>Category</label>
            <input 
              type="text" 
              className="form-input" 
              style={{ backgroundColor: '#ffffff', border: '1px solid #cbd5e1', color: '#0f172a' }}
              placeholder="e.g. Construction"
              value={formData.category}
              onChange={e => setFormData({...formData, category: e.target.value})}
              required
            />
          </div>
          <div>
            <label className="form-label" style={{ color: '#1e293b' }}>Your Company</label>
            <input 
              type="text" 
              className="form-input" 
              style={{ backgroundColor: '#ffffff', border: '1px solid #cbd5e1', color: '#0f172a' }}
              placeholder="Oman Poles LLC"
              value={formData.company_name}
              onChange={e => setFormData({...formData, company_name: e.target.value})}
              required
            />
          </div>
        </div>

        <button 
          type="submit" 
          style={{ 
            marginTop: '8px', 
            width: '100%', 
            backgroundColor: '#2563eb', 
            color: '#ffffff', 
            border: 'none', 
            padding: '12px', 
            borderRadius: '6px', 
            fontWeight: 'bold', 
            cursor: loading ? 'not-allowed' : 'pointer',
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            gap: '8px'
          }}
          disabled={loading}
        >
          {loading ? (
            <>
              <div style={{ width: '16px', height: '16px', border: '2px solid rgba(255,255,255,0.3)', borderTopColor: 'white', borderRadius: '50%', animation: 'spin 1s linear infinite' }} />
              Simulating Options...
            </>
          ) : (
            <>
              <Zap size={16} /> Run P2W Optimization
            </>
          )}
        </button>
      </form>

      {prediction && !loading && (
        <div style={{ marginTop: '24px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div style={{ fontSize: '14px', fontWeight: 'bold', color: '#0f172a', borderBottom: '1px solid #e2e8f0', paddingBottom: '8px' }}>
            Simulation Results
          </div>
          
          <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '16px' }}>
            {renderCard("Target Match (Recommended)", prediction.recommended, <DollarSign size={18} />, "#2563eb")}
            {renderCard("Aggressive Strategy", prediction.aggressive, <Flame size={18} />, "#ea580c")}
            {renderCard("Conservative Strategy", prediction.conservative, <ShieldCheck size={18} />, "#059669")}
          </div>
        </div>
      )}
      
      <style>{`
        @keyframes spin { 100% { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}
