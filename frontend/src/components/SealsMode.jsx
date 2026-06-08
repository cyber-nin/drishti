import React, { useState, useEffect } from 'react';
import { FileCheck, RefreshCw, FileText, Download, CheckCircle, AlertTriangle, ShieldCheck } from 'lucide-react';

const SealsMode = () => {
    const [seals, setSeals] = useState([]);
    const [loading, setLoading] = useState(true);
    const [selectedSeal, setSelectedSeal] = useState(null);
    
    // Verifier state
    const [verifyJson, setVerifyJson] = useState('');
    const [verifyResult, setVerifyResult] = useState(null);
    const [verifying, setVerifying] = useState(false);

    const fetchSeals = async () => {
        try {
            setLoading(true);
            const r = await fetch('/forensics/seals');
            if (r.ok) {
                const data = await r.json();
                setSeals(data);
                if (data.length > 0 && !selectedSeal) {
                    setSelectedSeal(data[0]);
                }
            }
        } catch (err) {
            console.error("Error loading forensic seals:", err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchSeals();
    }, []);

    const handleVerify = async (e) => {
        e.preventDefault();
        if (!selectedSeal || !verifyJson.trim()) return;

        try {
            setVerifying(true);
            setVerifyResult(null);
            
            let reportObj = {};
            try {
                reportObj = JSON.parse(verifyJson);
            } catch (err) {
                setVerifyResult({
                    success: false,
                    message: "Malformed JSON! Please make sure your report input is valid JSON format."
                });
                return;
            }

            const r = await fetch(`/forensics/verify/${selectedSeal.report_id}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ report_dict: reportObj })
            });

            if (r.ok) {
                const res = await r.json();
                setVerifyResult({
                    success: res.verified,
                    message: res.message
                });
            } else {
                setVerifyResult({
                    success: false,
                    message: "Verification failed. Report ID not found in database."
                });
            }
        } catch (err) {
            console.error("Error verifying report:", err);
            setVerifyResult({
                success: false,
                message: "Verification failed due to a server connection error."
            });
        } finally {
            setVerifying(false);
        }
    };

    if (loading && seals.length === 0) {
        return (
            <div className="fade-in space-y-4" style={{ padding: '2rem' }}>
                <div className="card card-saffron" style={{ textAlign: 'center', padding: '3rem' }}>
                    <p style={{ color: 'var(--text-2)', letterSpacing: '0.1em' }}>LOADING FORENSIC SEALS REGISTRY...</p>
                </div>
            </div>
        );
    }

    return (
        <div className="fade-in grid-2" style={{ padding: '2rem', gap: '2rem' }}>
            
            {/* Left Column — Sealed Reports List */}
            <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '1.2rem' }}>
                <div className="flex-between" style={{ borderBottom: '1px solid var(--border)', paddingBottom: '0.5rem' }}>
                    <h3 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '1rem', fontWeight: 700 }}>
                        <FileCheck size={18} color="var(--saffron)" />
                        Sealed Reports Registry
                    </h3>
                    <button className="btn-secondary" style={{ padding: '0.35rem 0.6rem', fontSize: '0.75rem' }} onClick={fetchSeals}>
                        <RefreshCw size={12} />
                    </button>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', maxHeight: '550px', overflowY: 'auto' }}>
                    {seals.length === 0 ? (
                        <p style={{ color: 'var(--text-2)', textAlign: 'center', padding: '2rem' }}>
                            No reports sealed inside forensic logs yet. Execute an investigation scanner run to seal a report.
                        </p>
                    ) : (
                        seals.map(s => (
                            <div key={s.id}
                                 onClick={() => {
                                     setSelectedSeal(s);
                                     setVerifyJson('');
                                     setVerifyResult(null);
                                 }}
                                 style={{
                                     padding: '1rem',
                                     background: selectedSeal?.id === s.id ? 'var(--bg-hover)' : 'var(--bg-input)',
                                     borderRadius: 'var(--radius-md)',
                                     border: selectedSeal?.id === s.id ? '1px solid var(--saffron-border)' : '1px solid var(--border)',
                                     cursor: 'pointer',
                                     transition: 'all 0.2s',
                                     display: 'flex',
                                     flexDirection: 'column',
                                     gap: '0.4rem'
                                 }}>
                                <div className="flex-between">
                                    <span style={{ fontWeight: 700, fontSize: '0.85rem' }}>{s.report_id}</span>
                                    <span className="badge badge-low" style={{
                                        background: s.seal_method === 'blockchain' ? 'var(--saffron-dim)' : 'var(--bg-hover)',
                                        color: s.seal_method === 'blockchain' ? 'var(--saffron)' : 'var(--text-2)',
                                        border: 'none'
                                    }}>
                                        {s.seal_method.toUpperCase()}
                                    </span>
                                </div>
                                <span style={{ fontSize: '0.72rem', color: 'var(--text-2)', fontFamily: 'JetBrains Mono, monospace', wordBreak: 'break-all' }}>
                                    Hash: {s.sha256_hash.substring(0, 32)}...
                                </span>
                                <span style={{ fontSize: '0.7rem', color: 'var(--text-3)', marginTop: '0.2rem' }}>
                                    Sealed: {s.timestamp.replace('T', ' ').substring(0, 19)}
                                </span>
                            </div>
                        ))
                    )}
                </div>
            </div>

            {/* Right Column — Verification & Certificate Downloads */}
            <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
                {selectedSeal ? (
                    <>
                        {/* Selected Seal Header */}
                        <div style={{ borderBottom: '1px solid var(--border)', paddingBottom: '1rem' }}>
                            <div className="flex-between">
                                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                    <ShieldCheck size={20} color="var(--success)" />
                                    <h2 style={{ fontSize: '1.2rem', fontWeight: 800 }}>Forensics Audit: {selectedSeal.report_id}</h2>
                                </div>
                                <a href={`/forensics/certificate/${selectedSeal.report_id}`} target="_blank" rel="noreferrer" className="btn-primary" style={{ padding: '0.4rem 0.9rem', fontSize: '0.82rem' }}>
                                    <Download size={14} style={{ marginRight: '0.2rem' }} /> Sec. 65B Cert (PDF)
                                </a>
                            </div>
                        </div>

                        {/* Seal details table */}
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem', fontSize: '0.82rem' }}>
                            <div className="flex-between" style={{ padding: '0.5rem 0.8rem', background: 'var(--bg-input)', borderRadius: '4px' }}>
                                <span style={{ color: 'var(--text-2)' }}>SHA-256 Hash:</span>
                                <span style={{ fontFamily: 'JetBrains Mono, monospace', fontWeight: 600 }}>{selectedSeal.sha256_hash}</span>
                            </div>
                            <div className="flex-between" style={{ padding: '0.5rem 0.8rem', background: 'var(--bg-input)', borderRadius: '4px' }}>
                                <span style={{ color: 'var(--text-2)' }}>Sealing Method:</span>
                                <span style={{ fontWeight: 700, color: 'var(--saffron-light)' }}>{selectedSeal.seal_method.toUpperCase()}</span>
                            </div>
                            {selectedSeal.tx_hash && (
                                <div className="flex-between" style={{ padding: '0.5rem 0.8rem', background: 'var(--bg-input)', borderRadius: '4px' }}>
                                    <span style={{ color: 'var(--text-2)' }}>Polygon Blockchain TX:</span>
                                    <span style={{ fontFamily: 'JetBrains Mono, monospace', wordBreak: 'break-all', fontWeight: 600 }}>{selectedSeal.tx_hash}</span>
                                </div>
                            )}
                            <div className="flex-between" style={{ padding: '0.5rem 0.8rem', background: 'var(--bg-input)', borderRadius: '4px' }}>
                                <span style={{ color: 'var(--text-2)' }}>Sealing Date:</span>
                                <span>{selectedSeal.timestamp}</span>
                            </div>
                        </div>

                        {/* Verification Form */}
                        <div style={{ borderTop: '1px solid var(--border)', paddingTop: '1.2rem' }}>
                            <h3 style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.9rem', fontWeight: 700, marginBottom: '0.6rem' }}>
                                <FileText size={16} color="var(--saffron)" />
                                Verify Local Document Integrity
                            </h3>
                            <p style={{ fontSize: '0.78rem', color: 'var(--text-2)', marginBottom: '1rem' }}>
                                Paste the exact JSON contents of the downloaded report to mathematically verify that it has not been modified or corrupted since it was sealed.
                            </p>

                            <form onSubmit={handleVerify} className="space-y-4">
                                <textarea
                                    value={verifyJson}
                                    onChange={e => setVerifyJson(e.target.value)}
                                    placeholder='Paste canonical JSON report here (e.g. {"query": "...", "summary": "..."})'
                                    rows={6}
                                    style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '0.78rem' }}
                                    required
                                />
                                <button type="submit" className="btn-secondary" style={{ width: '100%' }} disabled={verifying}>
                                    {verifying ? "Re-computing SHA-256 hash..." : "Execute Integrity Validation"}
                                </button>
                            </form>

                            {/* Verification Result */}
                            {verifyResult && (
                                <div style={{
                                    marginTop: '1.2rem',
                                    padding: '1rem',
                                    borderRadius: 'var(--radius-md)',
                                    background: verifyResult.success ? 'var(--success-dim)' : 'var(--danger-dim)',
                                    border: '1px solid ' + (verifyResult.success ? 'var(--success-border)' : 'var(--danger-border)'),
                                    display: 'flex',
                                    alignItems: 'flex-start',
                                    gap: '0.6rem'
                                }}>
                                    {verifyResult.success ? (
                                        <CheckCircle size={18} color="var(--success)" style={{ marginTop: '0.1rem', flexShrink: 0 }} />
                                    ) : (
                                        <AlertTriangle size={18} color="var(--danger)" style={{ marginTop: '0.1rem', flexShrink: 0 }} />
                                    )}
                                    <div style={{ fontSize: '0.82rem' }}>
                                        <b style={{ color: verifyResult.success ? 'var(--success)' : 'var(--danger)' }}>
                                            {verifyResult.success ? "INTEGRITY SECURED" : "INTEGRITY VIOLATION DETECTED"}
                                        </b>
                                        <p style={{ marginTop: '0.2rem', color: 'var(--text-1)' }}>{verifyResult.message}</p>
                                    </div>
                                </div>
                            )}
                        </div>
                    </>
                ) : (
                    <div style={{ textAlign: 'center', padding: '5rem', color: 'var(--text-2)' }}>
                        <FileCheck size={36} style={{ margin: '0 auto 1rem', opacity: 0.5 }} />
                        <p>Select a sealed report from the forensics register list to inspect cryptographic signatures.</p>
                    </div>
                )}
            </div>

        </div>
    );
};

export default SealsMode;
