import React, { useState, useEffect } from 'react';
import { Eye, Plus, Trash2, Mail, Link, AlertCircle, RefreshCw, EyeOff, ShieldAlert, Check } from 'lucide-react';

const WatchlistMode = () => {
    const [watchlists, setWatchlists] = useState([]);
    const [alerts, setAlerts] = useState({});
    const [selectedList, setSelectedList] = useState(null);
    const [loading, setLoading] = useState(true);
    const [activeAlertTab, setActiveAlertTab] = useState(null);
    
    // Form fields for creating watchlist
    const [formName, setFormName] = useState('');
    const [formKeywords, setFormKeywords] = useState('');
    const [formEmail, setFormEmail] = useState('');
    const [formWebhook, setFormWebhook] = useState('');
    const [formThreshold, setFormThreshold] = useState(35);
    
    const [newKeyword, setNewKeyword] = useState('');

    const fetchWatchlists = async () => {
        try {
            setLoading(true);
            const r = await fetch('/watchlist');
            if (r.ok) {
                const data = await r.json();
                setWatchlists(data);
                if (data.length > 0 && !selectedList) {
                    setSelectedList(data[0]);
                }
            }
        } catch (err) {
            console.error("Failed to fetch watchlists:", err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchWatchlists();
    }, []);

    useEffect(() => {
        if (selectedList) {
            fetchAlerts(selectedList.id);
        }
    }, [selectedList]);

    const fetchAlerts = async (id) => {
        try {
            const r = await fetch(`/watchlist/${id}/alerts`);
            if (r.ok) {
                const data = await r.json();
                setAlerts(prev => ({ ...prev, [id]: data }));
            }
        } catch (err) {
            console.error("Failed to load alerts for watchlist:", err);
        }
    };

    const handleCreateWatchlist = async (e) => {
        e.preventDefault();
        if (!formName || !formKeywords) return;
        
        const kwList = formKeywords.split(',').map(k => k.trim()).filter(Boolean);
        
        try {
            const r = await fetch('/watchlist', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    name: formName,
                    keywords: kwList,
                    alert_email: formEmail,
                    webhook_url: formWebhook,
                    severity_threshold: parseInt(formThreshold)
                })
            });
            
            if (r.ok) {
                setFormName('');
                setFormKeywords('');
                setFormEmail('');
                setFormWebhook('');
                setFormThreshold(35);
                fetchWatchlists();
            }
        } catch (err) {
            console.error("Error creating watchlist:", err);
        }
    };

    const handleAddKeyword = async (id) => {
        if (!newKeyword.trim()) return;
        try {
            const r = await fetch(`/watchlist/${id}/keyword`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ keyword: newKeyword })
            });
            if (r.ok) {
                setNewKeyword('');
                // Refresh watchlists
                const prevId = selectedList ? selectedList.id : null;
                const r2 = await fetch('/watchlist');
                if (r2.ok) {
                    const data = await r2.json();
                    setWatchlists(data);
                    const updated = data.find(w => w.id === id);
                    if (updated) setSelectedList(updated);
                }
            }
        } catch (err) {
            console.error("Error adding keyword:", err);
        }
    };

    const handleDeleteWatchlist = async (id) => {
        if (!confirm("Are you sure you want to delete this watchlist? All associated alerts will be permanently removed.")) return;
        try {
            const r = await fetch(`/watchlist/${id}`, { method: 'DELETE' });
            if (r.ok) {
                const remaining = watchlists.filter(w => w.id !== id);
                setWatchlists(remaining);
                setSelectedList(remaining.length > 0 ? remaining[0] : null);
            }
        } catch (err) {
            console.error("Error removing watchlist:", err);
        }
    };

    const handleTriggerScan = async (id) => {
        try {
            const r = await fetch(`/watchlist/${id}/scan`, { method: 'POST' });
            if (r.ok) {
                alert("Background monitoring scan triggered successfully! Check findings in the log/history in a few moments.");
            }
        } catch (err) {
            console.error("Error triggering scan:", err);
        }
    };

    if (loading && watchlists.length === 0) {
        return (
            <div className="fade-in space-y-4" style={{ padding: '2rem' }}>
                <div className="card card-saffron" style={{ textAlign: 'center', padding: '3rem' }}>
                    <p style={{ color: 'var(--text-2)', letterSpacing: '0.1em' }}>LOADING SECURITY WATCHLISTS...</p>
                </div>
            </div>
        );
    }

    return (
        <div className="fade-in grid-2" style={{ padding: '2rem', gap: '2rem' }}>
            
            {/* Left Column — Monitored Lists & Creation */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
                
                {/* Active Watchlists List */}
                <div className="card">
                    <h3 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '1rem', fontWeight: 700, marginBottom: '1.2rem', borderBottom: '1px solid var(--border)', paddingBottom: '0.5rem' }}>
                        <Eye size={18} color="var(--saffron)" />
                        Active Watchlists
                    </h3>
                    
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                        {watchlists.length === 0 ? (
                            <p style={{ color: 'var(--text-2)', textAlign: 'center', padding: '1rem' }}>No watchlists configured. Create one below to start automatic scanning.</p>
                        ) : (
                            watchlists.map(wl => (
                                <div key={wl.id} 
                                     onClick={() => setSelectedList(wl)}
                                     style={{
                                         padding: '1rem', 
                                         background: selectedList?.id === wl.id ? 'var(--bg-hover)' : 'var(--bg-input)', 
                                         borderRadius: 'var(--radius-md)',
                                         border: selectedList?.id === wl.id ? '1px solid var(--saffron-border)' : '1px solid var(--border)',
                                         cursor: 'pointer',
                                         transition: 'all 0.2s'
                                     }}>
                                    <div className="flex-between" style={{ marginBottom: '0.4rem' }}>
                                        <span style={{ fontWeight: 700, fontSize: '0.9rem' }}>{wl.name}</span>
                                        <div style={{ display: 'flex', gap: '0.5rem' }} onClick={(e) => e.stopPropagation()}>
                                            <button className="btn-secondary" 
                                                    style={{ padding: '0.3rem 0.5rem', borderRadius: '4px', fontSize: '0.72rem' }}
                                                    onClick={() => handleTriggerScan(wl.id)}>
                                                <RefreshCw size={12} />
                                            </button>
                                            <button className="btn-cancel" 
                                                    style={{ padding: '0.3rem 0.5rem', borderRadius: '4px', border: 'none' }}
                                                    onClick={() => handleDeleteWatchlist(wl.id)}>
                                                <Trash2 size={12} />
                                            </button>
                                        </div>
                                    </div>
                                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.3rem', marginTop: '0.5rem' }}>
                                        {wl.keywords.map((k, idx) => (
                                            <span key={idx} className="badge badge-medium" style={{ fontSize: '0.65rem' }}>{k}</span>
                                        ))}
                                    </div>
                                </div>
                            ))
                        )}
                    </div>
                </div>

                {/* Create Watchlist Form */}
                <div className="card">
                    <h3 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '1rem', fontWeight: 700, marginBottom: '1.2rem' }}>
                        <Plus size={18} color="var(--saffron)" />
                        Add New Watchlist
                    </h3>
                    
                    <form onSubmit={handleCreateWatchlist} className="space-y-4">
                        <div>
                            <label style={{ fontSize: '0.8rem', color: 'var(--text-2)', display: 'block', marginBottom: '0.3rem' }}>Watchlist Name</label>
                            <input type="text" value={formName} onChange={e => setFormName(e.target.value)} placeholder="e.g. Threat Actor Watchlist" required />
                        </div>
                        <div>
                            <label style={{ fontSize: '0.8rem', color: 'var(--text-2)', display: 'block', marginBottom: '0.3rem' }}>Keywords (comma-separated)</label>
                            <textarea value={formKeywords} onChange={e => setFormKeywords(e.target.value)} placeholder="e.g. credit card dump, explosives, passport" required rows={2} />
                        </div>
                        <div className="grid-2">
                            <div>
                                <label style={{ fontSize: '0.8rem', color: 'var(--text-2)', display: 'block', marginBottom: '0.3rem' }}><Mail size={12} style={{ marginRight: '0.2rem' }} /> Alert Email</label>
                                <input type="text" value={formEmail} onChange={e => setFormEmail(e.target.value)} placeholder="analyst@lea.gov.in" />
                            </div>
                            <div>
                                <label style={{ fontSize: '0.8rem', color: 'var(--text-2)', display: 'block', marginBottom: '0.3rem' }}><Link size={12} style={{ marginRight: '0.2rem' }} /> Webhook URL</label>
                                <input type="text" value={formWebhook} onChange={e => setFormWebhook(e.target.value)} placeholder="https://siem-endpoint/alert" />
                            </div>
                        </div>
                        <div>
                            <label style={{ fontSize: '0.8rem', color: 'var(--text-2)', display: 'block', marginBottom: '0.3rem' }}>Severity Threshold: {formThreshold}</label>
                            <input type="range" min="0" max="100" value={formThreshold} onChange={e => setFormThreshold(e.target.value)} />
                        </div>
                        <button type="submit" className="btn-primary" style={{ width: '100%' }}>Create Watchlist</button>
                    </form>
                </div>

            </div>

            {/* Right Column — Selected Watchlist Details & Alerts log */}
            <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
                {selectedList ? (
                    <>
                        {/* Selected Header */}
                        <div className="flex-between" style={{ borderBottom: '1px solid var(--border)', paddingBottom: '1rem' }}>
                            <div>
                                <h2 style={{ fontSize: '1.25rem', fontWeight: 800 }}>{selectedList.name}</h2>
                                <p style={{ fontSize: '0.78rem', color: 'var(--text-2)', marginTop: '0.1rem' }}>
                                    Severity threshold: {selectedList.severity_threshold} | Alert routing: {selectedList.alert_email ? 'Email' : 'None'}
                                </p>
                            </div>
                            <button className="btn-secondary" onClick={() => fetchAlerts(selectedList.id)}>
                                <RefreshCw size={14} style={{ marginRight: '0.2rem' }} /> Reload Alerts
                            </button>
                        </div>

                        {/* Keyword Adder */}
                        <div>
                            <label style={{ fontSize: '0.8rem', color: 'var(--text-2)', display: 'block', marginBottom: '0.4rem' }}>Add Keyword to this list</label>
                            <div style={{ display: 'flex', gap: '0.5rem' }}>
                                <input type="text" value={newKeyword} onChange={e => setNewKeyword(e.target.value)} placeholder="e.g. ransomware decrypt" />
                                <button className="btn-primary" style={{ padding: '0.65rem 1.2rem' }} onClick={() => handleAddKeyword(selectedList.id)}>
                                    <Plus size={16} />
                                </button>
                            </div>
                        </div>

                        {/* Alerts triggered list */}
                        <div>
                            <h3 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.9rem', fontWeight: 700, marginBottom: '1rem' }}>
                                <ShieldAlert size={16} color="var(--danger)" />
                                Triggered Security Alerts ({alerts[selectedList.id]?.length || 0})
                            </h3>
                            
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', maxHeight: '420px', overflowY: 'auto' }}>
                                {!alerts[selectedList.id] || alerts[selectedList.id].length === 0 ? (
                                    <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-2)', background: 'var(--bg-input)', borderRadius: 'var(--radius-md)' }}>
                                        <Check size={24} color="var(--success)" style={{ margin: '0 auto 0.5rem' }} />
                                        <p style={{ fontSize: '0.8rem' }}>No alerts triggered. The monitored parameters are clean.</p>
                                    </div>
                                ) : (
                                    alerts[selectedList.id].map(alert => (
                                        <div key={alert.id} style={{
                                            padding: '1rem',
                                            background: 'var(--bg-input)',
                                            borderRadius: 'var(--radius-md)',
                                            border: '1px solid var(--border)',
                                            display: 'flex',
                                            flexDirection: 'column',
                                            gap: '0.4rem'
                                        }}>
                                            <div className="flex-between">
                                                <span className="badge badge-critical" style={{ fontSize: '0.65rem' }}>Risk Score: {alert.severity_score}</span>
                                                <span style={{ fontSize: '0.72rem', color: 'var(--text-2)' }}>{alert.created_at}</span>
                                            </div>
                                            <p style={{ fontSize: '0.82rem', color: 'var(--text-2)', fontFamily: 'JetBrains Mono, monospace', wordBreak: 'break-all' }}>
                                                Source: <a href={alert.source_url} target="_blank" rel="noreferrer" style={{ color: 'var(--saffron-light)' }}>{alert.source_url}</a>
                                            </p>
                                            <p style={{ fontSize: '0.82rem', color: 'var(--text-1)', background: 'var(--bg-hover)', padding: '0.6rem', borderRadius: '4px', borderLeft: '3px solid var(--saffron)' }}>
                                                {alert.finding_summary}
                                            </p>
                                        </div>
                                    ))
                                )}
                            </div>
                        </div>
                    </>
                ) : (
                    <div style={{ textAlign: 'center', padding: '5rem', color: 'var(--text-2)' }}>
                        <EyeOff size={36} style={{ margin: '0 auto 1rem', opacity: 0.5 }} />
                        <p>No active watchlist selected.</p>
                    </div>
                )}
            </div>

        </div>
    );
};

export default WatchlistMode;
