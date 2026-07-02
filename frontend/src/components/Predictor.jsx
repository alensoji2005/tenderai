import { useState } from 'react';
import { Target, Zap, TrendingUp, AlertTriangle } from 'lucide-react';

export default function Predictor() {
  const [formData, setFormData] = useState({
    title: '',
    estimated_value: '',
    duration_months: '',
    entity: 'Ministry of Health',
    category: 'Construction'
  });
  const [prediction, setPrediction] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    
    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const res = await fetch(`${apiUrl}/api/ml/predict-optimal`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: formData.title,
          estimated_value: Number(formData.estimated_value) || 100000,
          duration_months: Number(formData.duration_months) || 12,
          is_sme: true,
          entity: formData.entity,
          category: formData.category
        })
      });
      const data = await res.json();
      
      if (!res.ok) {
        throw new Error(data.detail || 'Prediction failed');
      }
      
      // Simulate network delay for effect
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

  return (
    <div className="erp-card" style={{ gridColumn: 'span 6' }}>
      <div className="erp-card-header" style={{ marginBottom: '16px' }}>
        <div style={{ width: '32px', height: '32px', borderRadius: '8px', background: 'rgba(88, 166, 255, 0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--brand-primary)' }}>
          <Target size={18} />
        </div>
        AI Bid Forecaster
      </div>
      
      <p style={{ color: 'var(--text-secondary)', fontSize: '13px', marginBottom: '24px' }}>
        Predict winning bid amounts and generate optimal margins using our proprietary ML model.
      </p>

      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
        <div>
          <label className="form-label">Tender Title / Scope</label>
          <input 
            type="text" 
            className="form-input" 
            placeholder="e.g. Construction of Data Center..."
            value={formData.title}
            onChange={e => setFormData({...formData, title: e.target.value})}
            required
          />
        </div>
        
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
          <div>
            <label className="form-label">Est. Value (OMR)</label>
            <input 
              type="number" 
              className="form-input" 
              placeholder="150000"
              value={formData.estimated_value}
              onChange={e => setFormData({...formData, estimated_value: e.target.value})}
              required
            />
          </div>
          <div>
            <label className="form-label">Duration (Mos)</label>
            <input 
              type="number" 
              className="form-input" 
              placeholder="12"
              value={formData.duration_months}
              onChange={e => setFormData({...formData, duration_months: e.target.value})}
              required
            />
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
          <div>
            <label className="form-label">Entity Name</label>
            <input 
              type="text" 
              className="form-input" 
              placeholder="e.g. Ministry of Health"
              value={formData.entity}
              onChange={e => setFormData({...formData, entity: e.target.value})}
              required
            />
          </div>
          <div>
            <label className="form-label">Category</label>
            <input 
              type="text" 
              className="form-input" 
              placeholder="e.g. Construction"
              value={formData.category}
              onChange={e => setFormData({...formData, category: e.target.value})}
              required
            />
          </div>
        </div>

        <button 
          type="submit" 
          className="btn-primary" 
          style={{ marginTop: '8px', width: '100%', background: 'linear-gradient(135deg, var(--brand-primary) 0%, #3b82f6 100%)' }}
          disabled={loading}
        >
          {loading ? (
            <>
              <div style={{ width: '16px', height: '16px', border: '2px solid rgba(255,255,255,0.3)', borderTopColor: 'white', borderRadius: '50%', animation: 'spin 1s linear infinite' }} />
              Analyzing Market...
            </>
          ) : (
            <>
              <Zap size={16} /> Run Analysis
            </>
          )}
        </button>
      </form>

      {prediction && !loading && (
        <div style={{ 
          marginTop: '24px', 
          padding: '24px', 
          background: 'rgba(46, 160, 67, 0.05)', 
          border: '1px solid rgba(46, 160, 67, 0.2)', 
          borderRadius: '12px',
          position: 'relative',
          overflow: 'hidden'
        }}>
          <div style={{ position: 'absolute', top: 0, right: 0, padding: '12px', opacity: 0.1 }}>
            <TrendingUp size={64} />
          </div>
          
          <div style={{ fontSize: '12px', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '4px' }}>
            Optimal Bid Amount
          </div>
          <div style={{ fontSize: '32px', fontFamily: 'Outfit', fontWeight: 600, color: 'var(--status-green)', marginBottom: '16px' }}>
            OMR {prediction.predicted_winning_amount.toLocaleString()}
          </div>
          
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px', color: 'var(--text-primary)', background: 'rgba(255,255,255,0.05)', padding: '10px 12px', borderRadius: '8px' }}>
            <AlertTriangle size={14} color="var(--status-warning)" />
            Confidence Score: <strong style={{ color: 'var(--brand-primary)' }}>{(prediction.confidence_score * 100).toFixed(1)}%</strong>
          </div>

          {prediction.likely_competitors && prediction.likely_competitors.length > 0 && (
            <div style={{ marginTop: '16px', paddingTop: '16px', borderTop: '1px solid rgba(46, 160, 67, 0.2)' }}>
              <div style={{ fontSize: '12px', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '8px' }}>
                Likely Competitors
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                {prediction.likely_competitors.map((comp, idx) => (
                  <span key={idx} style={{ background: 'rgba(255,255,255,0.1)', padding: '4px 8px', borderRadius: '4px', fontSize: '12px', color: 'var(--text-primary)' }}>
                    {comp}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
      
      <style>{`
        @keyframes spin { 100% { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}
