import React, { useState, useRef, useEffect } from 'react';
import { Mail, MessageCircle, Bitcoin, Phone, Globe, Server, Share2, Code, FileText, Link as LinkIcon, Copy, Check, ShieldAlert, LayoutGrid, List } from 'lucide-react';
import '../styles/ArtifactsViewer.css';

const ENRICHABLE = ['ipv4', 'ips', 'domain', 'domains', 'md5', 'sha1', 'sha256'];

const SEV_COLORS = { CRITICAL: '#ff4b4b', HIGH: '#ff8a65', MEDIUM: '#fdd835', LOW: '#81c784', INFO: '#90a4ae' };
const SEV_ORDER  = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO'];

// ── Severity donut + bar chart ────────────────────────────────────────────────

const SeverityChart = ({ sections }) => {
    const [hovered, setHovered] = useState(null);

    const counts = SEV_ORDER.reduce((acc, s) => {
        acc[s] = sections.filter(sec => sec.severity === s && sec.items?.length > 0)
                         .reduce((sum, sec) => sum + sec.items.length, 0);
        return acc;
    }, {});

    const total = Object.values(counts).reduce((a, b) => a + b, 0);
    if (total === 0) return null;

    // Build donut arcs
    const R = 54, cx = 70, cy = 70, stroke = 14;
    const circumference = 2 * Math.PI * R;
    let offset = 0;
    const arcs = SEV_ORDER.filter(s => counts[s] > 0).map(s => {
        const pct = counts[s] / total;
        const arc = { s, pct, offset, color: SEV_COLORS[s], count: counts[s] };
        offset += pct;
        return arc;
    });

    return (
        <div className="severity-chart">
            <div className="donut-wrap">
                <svg width={140} height={140} viewBox="0 0 140 140">
                    {/* background ring */}
                    <circle cx={cx} cy={cy} r={R} fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth={stroke} />
                    {arcs.map(arc => (
                        <circle
                            key={arc.s}
                            cx={cx} cy={cy} r={R}
                            fill="none"
                            stroke={arc.color}
                            strokeWidth={hovered === arc.s ? stroke + 3 : stroke}
                            strokeDasharray={`${arc.pct * circumference} ${circumference}`}
                            strokeDashoffset={-arc.offset * circumference}
                            strokeLinecap="butt"
                            transform={`rotate(-90 ${cx} ${cy})`}
                            style={{ transition: 'stroke-width 0.15s', cursor: 'default' }}
                            onMouseEnter={() => setHovered(arc.s)}
                            onMouseLeave={() => setHovered(null)}
                        />
                    ))}
                    <text x={cx} y={cy - 8} textAnchor="middle" fill="#e8edf5" fontSize="22" fontWeight="800" fontFamily="JetBrains Mono, monospace">{total}</text>
                    <text x={cx} y={cy + 10} textAnchor="middle" fill="#3d5068" fontSize="9" fontWeight="600" letterSpacing="1" fontFamily="Inter, sans-serif">ARTIFACTS</text>
                    {hovered && (
                        <text x={cx} y={cy + 24} textAnchor="middle" fill={SEV_COLORS[hovered]} fontSize="8" fontWeight="700" fontFamily="Inter, sans-serif">{hovered}</text>
                    )}
                </svg>
            </div>

            <div className="sev-bars">
                {SEV_ORDER.filter(s => counts[s] > 0).map(s => (
                    <div
                        key={s}
                        className={`sev-bar-row ${hovered === s ? 'hovered' : ''}`}
                        onMouseEnter={() => setHovered(s)}
                        onMouseLeave={() => setHovered(null)}
                    >
                        <span className="sev-label" style={{ color: SEV_COLORS[s] }}>{s}</span>
                        <div className="sev-track">
                            <div
                                className="sev-fill"
                                style={{ width: `${(counts[s] / total) * 100}%`, background: SEV_COLORS[s] }}
                            />
                        </div>
                        <span className="sev-count">{counts[s]}</span>
                    </div>
                ))}
            </div>
        </div>
    );
};

// ── Rep badge ─────────────────────────────────────────────────────────────────

const RepBadge = ({ rep }) => {
    if (!rep) return null;
    const malicious = rep.malicious || 0;
    const suspicious = rep.suspicious || 0;
    const abuse = rep.abuse_score;
    const country = rep.country;

    if (malicious > 0) return <span className="rep-badge rep-malicious">🔴 {malicious} malicious</span>;
    if (suspicious > 0) return <span className="rep-badge rep-suspicious">🟡 {suspicious} suspicious</span>;
    if (abuse > 0) return <span className="rep-badge rep-abuse">⚠️ abuse {abuse}%{country ? ` · ${country}` : ''}</span>;
    return <span className="rep-badge rep-clean">✅ clean</span>;
};

// ── Card view ─────────────────────────────────────────────────────────────────

const ArtifactCard = ({ title, icon: Icon, items, color, severity, severityColor, enrichment }) => {
    const [copiedIndex, setCopiedIndex] = useState(null);

    const handleCopy = (text, index) => {
        navigator.clipboard.writeText(text);
        setCopiedIndex(index);
        setTimeout(() => setCopiedIndex(null), 2000);
    };

    if (!items || items.length === 0) return null;

    return (
        <div className="artifact-card glass-panel">
            <div className="artifact-header" style={{ borderBottomColor: color }}>
                <Icon size={18} style={{ color }} />
                <span className="artifact-title">{title}</span>
                {severity && (
                    <span className="artifact-severity" style={{ background: severityColor + '22', color: severityColor, border: `1px solid ${severityColor}55` }}>
                        {severity}
                    </span>
                )}
                <span className="artifact-count" style={{ background: color }}>{items.length}</span>
            </div>
            <div className="artifact-list">
                {items.map((item, index) => {
                    const text = typeof item === 'string' ? item : (item.action || JSON.stringify(item));
                    const rep = enrichment?.[text];
                    return (
                        <div key={index} className="artifact-item">
                            <span className="artifact-text" title={text}>{text}</span>
                            {rep !== undefined && <RepBadge rep={rep} />}
                            <button className="artifact-copy-btn" onClick={() => handleCopy(text, index)}>
                                {copiedIndex === index ? <Check size={12} /> : <Copy size={12} />}
                            </button>
                        </div>
                    );
                })}
            </div>
        </div>
    );
};

// ── List view ─────────────────────────────────────────────────────────────────

const ArtifactListView = ({ sections, enrichment }) => {
    const [copiedText, setCopiedText] = useState(null);

    const handleCopy = (text) => {
        navigator.clipboard.writeText(text);
        setCopiedText(text);
        setTimeout(() => setCopiedText(null), 2000);
    };

    const rows = [];
    sections.forEach(sec => {
        if (!sec.items?.length) return;
        sec.items.forEach((item, i) => {
            const text = typeof item === 'string' ? item : (item.action || JSON.stringify(item));
            rows.push({ text, section: sec, rep: enrichment?.[text], key: `${sec.title}-${i}` });
        });
    });

    return (
        <div className="artifact-list-view">
            <table className="artifact-table">
                <thead>
                    <tr>
                        <th>Type</th>
                        <th>Severity</th>
                        <th>Value</th>
                        <th>Rep</th>
                        <th></th>
                    </tr>
                </thead>
                <tbody>
                    {rows.map(row => (
                        <tr key={row.key}>
                            <td>
                                <span className="list-type-badge" style={{ color: row.section.color, borderColor: row.section.color + '44' }}>
                                    <row.section.icon size={11} />
                                    {row.section.title}
                                </span>
                            </td>
                            <td>
                                <span className="list-sev-badge" style={{ color: SEV_COLORS[row.section.severity], background: SEV_COLORS[row.section.severity] + '18' }}>
                                    {row.section.severity}
                                </span>
                            </td>
                            <td className="list-value" title={row.text}>{row.text}</td>
                            <td>{row.rep !== undefined && <RepBadge rep={row.rep} />}</td>
                            <td>
                                <button className="artifact-copy-btn" style={{ opacity: 1 }} onClick={() => handleCopy(row.text)}>
                                    {copiedText === row.text ? <Check size={12} /> : <Copy size={12} />}
                                </button>
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
};

// ── Main component ────────────────────────────────────────────────────────────

const ArtifactsViewer = ({ artifacts }) => {
    const [enrichment, setEnrichment] = useState({});
    const [enriching, setEnriching] = useState(false);
    const [enriched, setEnriched] = useState(false);
    const [viewMode, setViewMode] = useState('grid'); // 'grid' | 'list'

    if (!artifacts) return null;

    const sections = [
        { title: 'Crypto',        icon: Bitcoin,       items: artifacts.crypto || [...(artifacts.btc||[]), ...(artifacts.eth||[]), ...(artifacts.xmr||[])], color: '#ff4b4b', severity: 'CRITICAL', type: null },
        { title: 'Emails',        icon: Mail,          items: artifacts.emails || artifacts.email,   color: '#64b5f6', severity: 'HIGH',     type: null },
        { title: 'Telegram',      icon: MessageCircle, items: artifacts.telegram,                    color: '#29b6f6', severity: 'HIGH',     type: null },
        { title: 'IP Addresses',  icon: Server,        items: artifacts.ips || artifacts.ipv4,       color: '#e57373', severity: 'HIGH',     type: 'ipv4' },
        { title: 'Phones',        icon: Phone,         items: artifacts.phones || artifacts.phone,   color: '#81c784', severity: 'MEDIUM',   type: null },
        { title: 'Onion Domains', icon: Globe,         items: artifacts.onion,                       color: '#ff8a65', severity: 'MEDIUM',   type: null },
        { title: 'Domains',       icon: Globe,         items: artifacts.domains || artifacts.domain, color: '#ba68c8', severity: 'MEDIUM',   type: 'domain' },
        { title: 'Social Media',  icon: Share2,        items: artifacts.social,                      color: '#ff8a65', severity: 'MEDIUM',   type: null },
        { title: 'MD5 Hashes',    icon: FileText,      items: artifacts.md5,                         color: '#ef9a9a', severity: 'HIGH',     type: 'md5' },
        { title: 'SHA256 Hashes', icon: FileText,      items: artifacts.sha256,                      color: '#ef9a9a', severity: 'HIGH',     type: 'sha256' },
        { title: 'JS Files',      icon: Code,          items: artifacts.js_files,                    color: '#90a4ae', severity: 'LOW',      type: null },
        { title: 'Forms',         icon: FileText,      items: artifacts.forms,                       color: '#a1887f', severity: 'LOW',      type: null },
        { title: 'Links',         icon: LinkIcon,      items: artifacts.links,                       color: '#4db6ac', severity: 'INFO',     type: null },
    ];

    const severityColors = SEV_COLORS;
    const hasData = sections.some(s => s.items && s.items.length > 0);

    if (!hasData) {
        return <div className="no-artifacts glass-panel"><p>No artifacts found during the crawl.</p></div>;
    }

    const handleEnrich = async () => {
        setEnriching(true);
        const iocs = [];
        sections.forEach(s => {
            if (!s.type || !s.items) return;
            s.items.slice(0, 10).forEach(v => {
                if (typeof v === 'string') iocs.push({ type: s.type, value: v });
            });
        });
        if (!iocs.length) { setEnriching(false); return; }
        try {
            const resp = await fetch('/enrich', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ iocs })
            });
            const data = await resp.json();
            setEnrichment(data.results || {});
            setEnriched(true);
        } catch (e) {
            console.error('Enrichment failed:', e);
        }
        setEnriching(false);
    };

    return (
        <div>
            <SeverityChart sections={sections} />

            <div className="artifacts-toolbar">
                <button className="btn-enrich" onClick={handleEnrich} disabled={enriching}>
                    <ShieldAlert size={15} />
                    {enriching ? 'Enriching...' : enriched ? 'Re-enrich IOCs' : 'Enrich IOCs (VT + AbuseIPDB)'}
                </button>
                {enriched && <span className="enrich-note">{Object.keys(enrichment).length} IOCs enriched</span>}
                <div className="view-toggle">
                    <button className={viewMode === 'grid' ? 'active' : ''} onClick={() => setViewMode('grid')} title="Card view">
                        <LayoutGrid size={14} />
                    </button>
                    <button className={viewMode === 'list' ? 'active' : ''} onClick={() => setViewMode('list')} title="List view">
                        <List size={14} />
                    </button>
                </div>
            </div>

            {viewMode === 'grid' ? (
                <div className="artifacts-grid">
                    {sections.map(section => section.items && section.items.length > 0 && (
                        <ArtifactCard
                            key={section.title}
                            {...section}
                            severityColor={severityColors[section.severity]}
                            enrichment={enrichment}
                        />
                    ))}
                </div>
            ) : (
                <ArtifactListView sections={sections.filter(s => s.items?.length > 0)} enrichment={enrichment} />
            )}
        </div>
    );
};

export default ArtifactsViewer;
