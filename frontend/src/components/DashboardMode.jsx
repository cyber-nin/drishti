import React, { useState, useEffect } from 'react';
import { LayoutDashboard, TrendingUp, AlertTriangle, ShieldCheck, ShieldAlert, BarChart3, Clock, HelpCircle } from 'lucide-react';

const DashboardMode = () => {
    const [trends, setTrends] = useState({ categories: {}, top_keywords: [] });
    const [sources, setSources] = useState([]);
    const [timeline, setTimeline] = useState([]);
    const [loading, setLoading] = useState(true);

    const fetchDashboardData = async () => {
        try {
            setLoading(true);
            const headers = { 'Content-Type': 'application/json' };
            
            const [trendsRes, sourcesRes, timelineRes] = await Promise.all([
                fetch('/dashboard/trends?hours=168', { headers }),
                fetch('/dashboard/sources', { headers }),
                fetch('/dashboard/timeline', { headers })
            ]);

            if (trendsRes.ok) setTrends(await trendsRes.json());
            if (sourcesRes.ok) setSources(await sourcesRes.json());
            if (timelineRes.ok) setTimeline(await timelineRes.json());
        } catch (err) {
            console.error("Failed to load dashboard statistics:", err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchDashboardData();
    }, []);

    // Divine-themed taxonomy categorisation styles
    const catLabels = {
        drugs: "Contraband & Narcotics",
        weapons: "Weapons & Ammo",
        documents: "Identity Theft & Docs",
        financial: "Financial & Cards Dumps",
        malware: "Malware & Ransomware Kits",
        data_breaches: "Database Breaches & Combo Lists"
    };

    const catGlows = {
        drugs: "border-l-4 border-l-orange-500",
        weapons: "border-l-4 border-l-red-500",
        documents: "border-l-4 border-l-yellow-500",
        financial: "border-l-4 border-l-blue-500",
        malware: "border-l-4 border-l-purple-500",
        data_breaches: "border-l-4 border-l-cyan-500"
    };

    if (loading) {
        return (
            <div className="fade-in space-y-4" style={{ padding: '2rem' }}>
                <div className="card card-saffron" style={{ textAlign: 'center', padding: '3rem' }}>
                    <div className="third-eye-portal">
                        <div className="third-eye-pupil">
                            <div className="third-eye-core" />
                        </div>
                    </div>
                    <p style={{ marginTop: '1rem', color: 'var(--text-2)', letterSpacing: '0.1em' }}>
                        OPENING THE EYE OF DRISHTI... LOADING COGNITIVE INTEL
                    </p>
                </div>
            </div>
        );
    }

    return (
        <div className="fade-in space-y-4" style={{ padding: '2rem', display: 'flex', flexDirection: 'column', gap: '2rem' }}>
            
            {/* Top Row Overview Cards */}
            <div className="grid-3">
                <div className="card card-saffron flex-between">
                    <div>
                        <span style={{ fontSize: '0.8rem', color: 'var(--text-2)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Threats Monitored</span>
                        <h2 className="gradient-text" style={{ fontSize: '2rem', fontWeight: 800, marginTop: '0.2rem' }}>
                            {Object.values(trends.categories).reduce((a, b) => a + b, 0) || 0}
                        </h2>
                    </div>
                    <AlertTriangle size={32} color="var(--saffron)" style={{ opacity: 0.8 }} />
                </div>

                <div className="card card-indigo flex-between">
                    <div>
                        <span style={{ fontSize: '0.8rem', color: 'var(--text-2)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Active Sources Mapped</span>
                        <h2 className="gradient-blue-text" style={{ fontSize: '2rem', fontWeight: 800, marginTop: '0.2rem' }}>
                            {sources.length || 0}
                        </h2>
                    </div>
                    <BarChart3 size={32} color="var(--indigo-cosmic)" style={{ opacity: 0.8 }} />
                </div>

                <div className="card flex-between" style={{ border: '1px solid var(--success-border)' }}>
                    <div>
                        <span style={{ fontSize: '0.8rem', color: 'var(--text-2)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Evidence Integrity</span>
                        <h2 style={{ fontSize: '1.25rem', fontWeight: 700, marginTop: '0.4rem', color: 'var(--success)' }}>
                            Forensic (Sec. 65B)
                        </h2>
                    </div>
                    <ShieldCheck size={32} color="var(--success)" style={{ opacity: 0.8 }} />
                </div>
            </div>

            {/* Middle Row Grid */}
            <div className="grid-2">
                
                {/* Taxonomy Category Distribution */}
                <div className="card">
                    <div className="flex-between" style={{ marginBottom: '1.5rem', borderBottom: '1px solid var(--border)', paddingBottom: '0.5rem' }}>
                        <h3 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '1rem', fontWeight: 700 }}>
                            <TrendingUp size={18} color="var(--saffron)" />
                            Threat Taxonomy Aggregates
                        </h3>
                        <span style={{ fontSize: '0.75rem', color: 'var(--text-2)' }}>Last 7 Days</span>
                    </div>
                    
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                        {Object.entries(trends.categories).length === 0 ? (
                            <p style={{ color: 'var(--text-2)', textAlign: 'center', padding: '1rem' }}>No threat events indexed in taxonomy registers yet.</p>
                        ) : (
                            Object.entries(trends.categories).map(([cat, val]) => (
                                <div key={cat} className="flex-between" style={{
                                    padding: '0.8rem 1rem', 
                                    background: 'var(--bg-input)', 
                                    borderRadius: 'var(--radius-md)',
                                    borderLeft: '4px solid ' + (cat === 'drugs' ? 'var(--saffron)' : (cat === 'weapons' ? '#ef4444' : (cat === 'documents' ? '#eab308' : (cat === 'financial' ? '#3b82f6' : '#a78bfa'))))
                                }}>
                                    <span style={{ fontWeight: 600, fontSize: '0.85rem' }}>{catLabels[cat] || cat}</span>
                                    <span className="badge badge-medium" style={{ background: 'var(--bg-hover)', color: '#fff', border: 'none' }}>{val} Hits</span>
                                </div>
                            ))
                        )}
                    </div>
                </div>

                {/* Top Source Onion Rankings */}
                <div className="card">
                    <div className="flex-between" style={{ marginBottom: '1.5rem', borderBottom: '1px solid var(--border)', paddingBottom: '0.5rem' }}>
                        <h3 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '1rem', fontWeight: 700 }}>
                            <ShieldAlert size={18} color="#ef4444" />
                            Risk Rankings (.onion sources)
                        </h3>
                        <span style={{ fontSize: '0.75rem', color: 'var(--text-2)' }}>Top Risk Rating</span>
                    </div>

                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.8rem' }}>
                        {sources.length === 0 ? (
                            <p style={{ color: 'var(--text-2)', textAlign: 'center', padding: '1rem' }}>No Dark Web domain ratings compiled yet.</p>
                        ) : (
                            sources.map((src, idx) => (
                                <div key={idx} className="flex-between" style={{
                                    padding: '0.6rem 0.8rem', 
                                    background: 'var(--bg-input)', 
                                    borderRadius: 'var(--radius-md)',
                                    border: '1px solid var(--border)'
                                }}>
                                    <div style={{ display: 'flex', flexDirection: 'column' }}>
                                        <span style={{ fontWeight: 700, fontSize: '0.82rem', fontFamily: 'JetBrains Mono, monospace', color: 'var(--text-1)' }}>
                                            {src.domain.length > 32 ? src.domain.substring(0, 30) + '...' : src.domain}
                                        </span>
                                        <span style={{ fontSize: '0.7rem', color: 'var(--text-2)', marginTop: '0.1rem' }}>
                                            Frequency: {src.finding_frequency} scans | {src.ioc_count} IOCs
                                        </span>
                                    </div>
                                    <span className={`badge ${src.avg_severity_score >= 80 ? 'badge-critical' : (src.avg_severity_score >= 60 ? 'badge-high' : 'badge-medium')}`}>
                                        Avg Risk: {src.avg_severity_score}
                                    </span>
                                </div>
                            ))
                        )}
                    </div>
                </div>

            </div>

            {/* Bottom Row - Timeline */}
            <div className="card">
                <div className="flex-between" style={{ marginBottom: '1.5rem', borderBottom: '1px solid var(--border)', paddingBottom: '0.5rem' }}>
                    <h3 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '1rem', fontWeight: 700 }}>
                        <Clock size={18} color="var(--indigo-cosmic)" />
                        Intelligence Activity Scan Logs Timeline
                    </h3>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-2)' }}>Timeline History</span>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                    {timeline.length === 0 ? (
                        <p style={{ color: 'var(--text-2)', textAlign: 'center', padding: '1.5rem' }}>No periodic scan logs recorded inside Drishti registry yet.</p>
                    ) : (
                        timeline.map((slot, idx) => (
                            <div key={idx} className="flex-between" style={{
                                padding: '0.8rem 1rem', 
                                background: 'var(--bg-input)', 
                                borderRadius: 'var(--radius-md)',
                                border: '1px solid var(--border)'
                            }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '1.5rem' }}>
                                    <div style={{ display: 'flex', flexDirection: 'column' }}>
                                        <span style={{ fontSize: '0.85rem', fontWeight: 600 }}>{slot.time_slot}</span>
                                        <span style={{ fontSize: '0.72rem', color: 'var(--text-2)' }}>Scans Executed: {slot.total_scans}</span>
                                    </div>
                                </div>
                                <div style={{ display: 'flex', gap: '0.5rem' }}>
                                    {slot.distribution.CRITICAL > 0 && <span className="badge badge-critical">{slot.distribution.CRITICAL} Critical</span>}
                                    {slot.distribution.HIGH > 0 && <span className="badge badge-high">{slot.distribution.HIGH} High</span>}
                                    {slot.distribution.MEDIUM > 0 && <span className="badge badge-medium">{slot.distribution.MEDIUM} Med</span>}
                                    {slot.distribution.LOW > 0 && <span className="badge badge-low">{slot.distribution.LOW} Low</span>}
                                </div>
                            </div>
                        ))
                    )}
                </div>
            </div>

        </div>
    );
};

export default DashboardMode;
