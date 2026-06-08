import React, { useState, useEffect } from 'react';
import { Users, Search, RefreshCw, User, Award, ShieldAlert, BookOpen, Fingerprint, Calendar, Download, Link, Compass } from 'lucide-react';

const ActorMode = () => {
    const [profiles, setProfiles] = useState([]);
    const [selectedActor, setSelectedActor] = useState(null);
    const [fullProfile, setFullProfile] = useState(null);
    const [loading, setLoading] = useState(true);
    
    // Correlator state
    const [correlateQuery, setCorrelateQuery] = useState('');
    const [correlationResults, setCorrelationResults] = useState([]);
    const [correlating, setCorrelating] = useState(false);

    const fetchProfiles = async () => {
        try {
            setLoading(true);
            const r = await fetch('/actors');
            if (r.ok) {
                const data = await r.json();
                setProfiles(data);
                if (data.length > 0 && !selectedActor) {
                    setSelectedActor(data[0]);
                }
            }
        } catch (err) {
            console.error("Failed to load profiles:", err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchProfiles();
    }, []);

    useEffect(() => {
        if (selectedActor) {
            fetchFullProfile(selectedActor.id);
        }
    }, [selectedActor]);

    const fetchFullProfile = async (id) => {
        try {
            const r = await fetch(`/actor/${id}`);
            if (r.ok) {
                setFullProfile(await r.json());
            }
        } catch (err) {
            console.error("Failed to fetch full profile:", err);
        }
    };

    const handleCorrelate = async (e) => {
        e.preventDefault();
        if (!correlateQuery.trim()) return;
        
        try {
            setCorrelating(true);
            const r = await fetch('/actor/correlate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ artifact: correlateQuery })
            });
            if (r.ok) {
                setCorrelationResults(await r.json());
            }
        } catch (err) {
            console.error("Failed to correlate indicator:", err);
        } finally {
            setCorrelating(false);
        }
    };

    if (loading && profiles.length === 0) {
        return (
            <div className="fade-in space-y-4" style={{ padding: '2rem' }}>
                <div className="card card-saffron" style={{ textAlign: 'center', padding: '3rem' }}>
                    <p style={{ color: 'var(--text-2)', letterSpacing: '0.1em' }}>LOADING THREAT ACTOR PERSOAN PROFILES...</p>
                </div>
            </div>
        );
    }

    return (
        <div className="fade-in grid-2" style={{ padding: '2rem', gap: '2rem' }}>
            
            {/* Left Column — Profiles lists & Cross Correlator */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
                
                {/* Profiles List */}
                <div className="card">
                    <div className="flex-between" style={{ marginBottom: '1.2rem', borderBottom: '1px solid var(--border)', paddingBottom: '0.5rem' }}>
                        <h3 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '1rem', fontWeight: 700 }}>
                            <Users size={18} color="var(--saffron)" />
                            Indexed Personas
                        </h3>
                        <button className="btn-secondary" style={{ padding: '0.35rem 0.6rem', fontSize: '0.75rem' }} onClick={fetchProfiles}>
                            <RefreshCw size={12} />
                        </button>
                    </div>

                    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', maxHeight: '350px', overflowY: 'auto' }}>
                        {profiles.length === 0 ? (
                            <p style={{ color: 'var(--text-2)', textAlign: 'center', padding: '1rem' }}>No threat actor personas indexed yet. Ingest them from scanner investigations.</p>
                        ) : (
                            profiles.map(p => (
                                <div key={p.id}
                                     onClick={() => setSelectedActor(p)}
                                     style={{
                                         padding: '0.8rem 1rem',
                                         background: selectedActor?.id === p.id ? 'var(--bg-hover)' : 'var(--bg-input)',
                                         borderRadius: 'var(--radius-md)',
                                         border: selectedActor?.id === p.id ? '1px solid var(--saffron-border)' : '1px solid var(--border)',
                                         cursor: 'pointer',
                                         transition: 'all 0.2s',
                                         display: 'flex',
                                         justifyContent: 'space-between',
                                         alignItems: 'center'
                                     }}>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                                        <User size={16} color="var(--saffron-light)" />
                                        <span style={{ fontWeight: 700, fontSize: '0.85rem', fontFamily: 'JetBrains Mono, monospace' }}>{p.primary_handle}</span>
                                    </div>
                                    <span className={`badge ${p.threat_level >= 80 ? 'badge-critical' : (p.threat_level >= 60 ? 'badge-high' : 'badge-medium')}`}>
                                        Level {p.threat_level}
                                    </span>
                                </div>
                            ))
                        )}
                    </div>
                </div>

                {/* Persona Cross-Correlator */}
                <div className="card">
                    <h3 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '1rem', fontWeight: 700, marginBottom: '1rem' }}>
                        <Compass size={18} color="var(--indigo-cosmic)" />
                        Identity Cross-Correlator
                    </h3>
                    <p style={{ fontSize: '0.78rem', color: 'var(--text-2)', marginBottom: '1rem' }}>
                        Enter a unique cryptocurrency address, PGP signature, email or handle to find correlated personas sharing the same indicator.
                    </p>

                    <form onSubmit={handleCorrelate} style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem' }}>
                        <input type="text" value={correlateQuery} onChange={e => setCorrelateQuery(e.target.value)} placeholder="e.g. 1A1zP1eP5QGefi..." required />
                        <button type="submit" className="btn-primary">
                            <Search size={16} />
                        </button>
                    </form>

                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
                        {correlating ? (
                            <p style={{ color: 'var(--text-2)', textAlign: 'center', fontSize: '0.8rem' }}>Querying indicators catalog...</p>
                        ) : correlationResults.length > 0 ? (
                            correlationResults.map(res => (
                                <div key={res.id} 
                                     onClick={() => {
                                         setSelectedActor(res);
                                         setCorrelationResults([]);
                                         setCorrelateQuery('');
                                     }}
                                     style={{
                                         padding: '0.6rem 0.8rem',
                                         background: 'var(--bg-hover)',
                                         borderRadius: 'var(--radius-md)',
                                         border: '1px solid var(--saffron-border)',
                                         cursor: 'pointer',
                                         display: 'flex',
                                         justifyContent: 'space-between',
                                         fontSize: '0.8rem'
                                     }}>
                                    <span style={{ fontWeight: 700, fontFamily: 'JetBrains Mono, monospace' }}>{res.primary_handle}</span>
                                    <span style={{ color: 'var(--danger)', fontWeight: 600 }}>MATCH (Threat: {res.threat_level})</span>
                                </div>
                            ))
                        ) : correlateQuery && !correlating ? (
                            <p style={{ color: 'var(--text-3)', textAlign: 'center', fontSize: '0.8rem' }}>No direct persona correlations found.</p>
                        ) : null}
                    </div>
                </div>

            </div>

            {/* Right Column — Full Threat Actor Persona Details */}
            <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
                {fullProfile ? (
                    <>
                        {/* Profile Header */}
                        <div style={{ borderBottom: '1px solid var(--border)', paddingBottom: '1.2rem' }}>
                            <div className="flex-between">
                                <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                                    <Award size={22} color="var(--saffron)" />
                                    <h2 style={{ fontSize: '1.35rem', fontWeight: 800, fontFamily: 'JetBrains Mono, monospace' }}>{fullProfile.primary_handle}</h2>
                                </div>
                                <div style={{ display: 'flex', gap: '0.5rem' }}>
                                    <a href={`/actor/${fullProfile.id}/export?format=json`} target="_blank" rel="noreferrer" className="btn-secondary" style={{ padding: '0.4rem 0.8rem', fontSize: '0.78rem' }}>
                                        <Download size={12} /> JSON
                                    </a>
                                    <a href={`/actor/${fullProfile.id}/export?format=stix2`} target="_blank" rel="noreferrer" className="btn-secondary" style={{ padding: '0.4rem 0.8rem', fontSize: '0.78rem', borderColor: 'var(--saffron-border)' }}>
                                        <ShieldAlert size={12} /> STIX 2.1
                                    </a>
                                </div>
                            </div>
                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem', marginTop: '0.8rem' }}>
                                <span className="badge badge-critical" style={{ fontSize: '0.68rem', fontWeight: 800 }}>Risk rating: {fullProfile.threat_level}</span>
                                {fullProfile.linked_pseudonyms.map((alias, idx) => (
                                    <span key={idx} className="badge badge-medium" style={{ fontSize: '0.68rem', background: 'var(--bg-hover)', border: 'none' }}>{alias}</span>
                                ))}
                            </div>
                        </div>

                        {/* Behavior Writing Style & MITRE TTPs */}
                        <div className="grid-2">
                            {/* Heuristics */}
                            <div style={{ background: 'var(--bg-input)', padding: '1rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--border)' }}>
                                <h4 style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.85rem', fontWeight: 700, color: 'var(--saffron-light)', marginBottom: '0.6rem' }}>
                                    <BookOpen size={14} /> Behavioral Writing Styles
                                </h4>
                                <ul style={{ listStyle: 'none', fontSize: '0.8rem', color: 'var(--text-2)', display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
                                    <li>• Average Sentence: <b>{fullProfile.writing_style?.avg_sentence_length || 'N/A'} words</b></li>
                                    <li>• Pattern: <b>Interactive, Transactional</b></li>
                                    <li>• Signature Lexicon: <b>{fullProfile.writing_style?.common_phrases?.join(', ') || 'N/A'}</b></li>
                                </ul>
                            </div>
                            {/* MITRE TTPs */}
                            <div style={{ background: 'var(--bg-input)', padding: '1rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--border)' }}>
                                <h4 style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.85rem', fontWeight: 700, color: 'var(--danger)', marginBottom: '0.6rem' }}>
                                    <ShieldAlert size={14} /> Inferred MITRE ATT&CK TTPs
                                </h4>
                                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.3rem' }}>
                                    {fullProfile.ttp_tags.length === 0 ? (
                                        <span style={{ fontSize: '0.78rem', color: 'var(--text-3)' }}>No TTP codes inferred.</span>
                                    ) : (
                                        fullProfile.ttp_tags.map(t => (
                                            <span key={t} className="badge badge-critical" style={{ fontSize: '0.65rem' }}>{t}</span>
                                        ))
                                    )}
                                </div>
                            </div>
                        </div>

                        {/* Linked PII IOCs */}
                        <div>
                            <h4 style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-1)', marginBottom: '0.6rem' }}>
                                <Fingerprint size={14} /> Mapped Cryptographic & Digital Indicators
                            </h4>
                            <div style={{ maxHeight: '180px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                                {Object.entries(fullProfile.linked_iocs).length === 0 ? (
                                    <p style={{ fontSize: '0.78rem', color: 'var(--text-3)' }}>No linked indicators registered for this persona.</p>
                                ) : (
                                    Object.entries(fullProfile.linked_iocs).map(([type, vals]) => (
                                        <div key={type} style={{ padding: '0.5rem 0.8rem', background: 'var(--bg-input)', borderRadius: 'var(--radius-sm)', fontSize: '0.78rem' }}>
                                            <b style={{ color: 'var(--saffron-light)', textTransform: 'uppercase', marginRight: '0.5rem' }}>{type}:</b>
                                            <span style={{ fontFamily: 'JetBrains Mono, monospace', wordBreak: 'break-all' }}>{vals.join(', ')}</span>
                                        </div>
                                    ))
                                )}
                            </div>
                        </div>

                        {/* Activity timeline map */}
                        <div>
                            <h4 style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-1)', marginBottom: '0.8rem' }}>
                                <Calendar size={14} /> Chronological Action Timeline
                            </h4>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.8rem', maxHeight: '200px', overflowY: 'auto', paddingLeft: '0.5rem', borderLeft: '1px solid var(--border)' }}>
                                {fullProfile.timeline.map((event, idx) => (
                                    <div key={idx} style={{ position: 'relative', paddingLeft: '1rem', fontSize: '0.78rem' }}>
                                        <div style={{ position: 'absolute', left: '-5px', top: '4px', width: '9px', height: '9px', borderRadius: '50%', background: 'var(--saffron)', border: '2px solid var(--bg-card)' }} />
                                        <span style={{ fontWeight: 700, color: 'var(--text-2)' }}>{event.timestamp.substring(0, 16).replace('T', ' ')}</span>
                                        <p style={{ fontWeight: 600, color: 'var(--text-1)', marginTop: '0.1rem' }}>{event.event}</p>
                                        <p style={{ color: 'var(--text-2)', fontSize: '0.72rem', marginTop: '0.05rem' }}>{event.details}</p>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </>
                ) : (
                    <div style={{ textAlign: 'center', padding: '5rem', color: 'var(--text-2)' }}>
                        <Users size={36} style={{ margin: '0 auto 1rem', opacity: 0.5 }} />
                        <p>Select a tracked threat actor persona from the list to view the complete digital footprint.</p>
                    </div>
                )}
            </div>

        </div>
    );
};

export default ActorMode;
