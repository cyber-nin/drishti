import React, { useState, useRef } from 'react';
import { Globe, Play, Layers, XCircle, FileText, FileJson, Printer, FileCode, GitFork } from 'lucide-react';
import { motion } from 'framer-motion';
import Terminal from './Terminal';
import { useToast } from './Toast';
import ArtifactsViewer from './ArtifactsViewer';
import GraphView from './GraphView';
import '../styles/CrawlMode.css';

const CrawlMode = ({ config }) => {
    const [url, setUrl] = useState('');
    const [depth, setDepth] = useState(2);
    const [isCrawling, setIsCrawling] = useState(false);
    const [logs, setLogs] = useState([]);
    const [artifacts, setArtifacts] = useState(null);
    const toast = useToast();
    const eventSourceRef = useRef(null);

    const handleAbort = () => {
        if (eventSourceRef.current) {
            eventSourceRef.current.close();
            eventSourceRef.current = null;
            setIsCrawling(false);
            setLogs(prev => [...prev, {
                stage: 'error',
                message: 'Crawl cancelled by user'
            }]);
            toast.warning('Crawl cancelled');
        }
    };

    const [crawlStats, setCrawlStats] = useState({ pages: 0, artifacts: 0 });
    const [showGraph, setShowGraph] = useState(false);

    const handleExportJSON = () => {
        if (!artifacts) return;
        const data = { url, depth, timestamp: new Date().toISOString(), artifacts };
        const blobUrl = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' }));
        const el = document.createElement('a');
        el.href = blobUrl;
        el.download = `crawl_${url.replace(/[^a-z0-9]/gi, '_')}_${Date.now()}.json`;
        el.click();
        URL.revokeObjectURL(blobUrl);
    };

    const handleExportMarkdown = () => {
        if (!artifacts) return;
        const lines = [
            `# Deep Crawl Report`,
            `**Target:** ${url}`,
            `**Depth:** ${depth}`,
            `**Date:** ${new Date().toLocaleString()}`,
            `**Pages Crawled:** ${crawlStats.pages}`,
            '',
            '## Extracted Artifacts',
        ];
        Object.entries(artifacts).forEach(([type, values]) => {
            if (!values || values.length === 0) return;
            lines.push(`### ${type.charAt(0).toUpperCase() + type.slice(1)}`);
            (Array.isArray(values) ? values : []).forEach(v =>
                lines.push(`- ${typeof v === 'string' ? v : JSON.stringify(v)}`)
            );
            lines.push('');
        });
        const blobUrl = URL.createObjectURL(new Blob([lines.join('\n')], { type: 'text/markdown' }));
        const el = document.createElement('a');
        el.href = blobUrl;
        el.download = `crawl_${url.replace(/[^a-z0-9]/gi, '_')}_${Date.now()}.md`;
        el.click();
        URL.revokeObjectURL(blobUrl);
    };

    const handleExportHTML = () => {
        if (!artifacts) return;
        const rows = Object.entries(artifacts)
            .filter(([, v]) => Array.isArray(v) && v.length)
            .map(([type, values]) =>
                values.map(v => `<tr><td><span class="badge">${type}</span></td><td><code>${typeof v === 'string' ? v : JSON.stringify(v)}</code></td></tr>`).join('')
            ).join('');
        const html = `<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">
<title>DRISHTI Crawl Report</title>
<style>*{box-sizing:border-box;margin:0;padding:0}body{font-family:'Segoe UI',Arial,sans-serif;background:#0d0d0d;color:#e0e0e0;padding:2rem}.wrapper{max-width:960px;margin:0 auto}header{border-bottom:2px solid #ff4b4b;padding-bottom:1rem;margin-bottom:2rem}header h1{color:#ff4b4b;font-size:1.8rem}.meta{font-size:.8rem;color:#888;margin-top:.4rem}.query-box{margin-top:.8rem;background:#1a1a1a;border-left:3px solid #ff4b4b;padding:.5rem 1rem;color:#ccc;border-radius:0 4px 4px 0}h2{color:#ff8a65;margin:1.5rem 0 .75rem;border-bottom:1px solid #2a2a2a;padding-bottom:.3rem}table{width:100%;border-collapse:collapse;font-size:.85rem}th{background:#1a1a1a;color:#ff4b4b;padding:.6rem .8rem;text-align:left;border-bottom:2px solid #ff4b4b}td{padding:.5rem .8rem;border-bottom:1px solid #1e1e1e}tr:hover td{background:#161616}code{background:#1e1e1e;padding:2px 6px;border-radius:3px;font-family:Consolas,monospace;font-size:.82rem;color:#a9b7c6;word-break:break-all}.badge{background:rgba(255,75,75,.15);color:#ff8a65;border:1px solid rgba(255,75,75,.3);padding:2px 8px;border-radius:10px;font-size:.72rem}footer{margin-top:2rem;padding-top:1rem;border-top:1px solid #1e1e1e;font-size:.75rem;color:#555;text-align:center}@media print{body{background:#fff;color:#000}header h1,h2{color:#c00}.badge{background:#fee;color:#c00}code{background:#f4f4f4;color:#333}}</style>
</head><body><div class="wrapper">
<header><h1>&#x1F6E1; DRISHTI Crawl Report</h1>
<div class="meta">Generated: ${new Date().toUTCString()} &nbsp;|&nbsp; Classification: LAW ENFORCEMENT SENSITIVE</div>
<div class="query-box"><strong>Target:</strong> ${url} &nbsp;|&nbsp; <strong>Depth:</strong> ${depth} &nbsp;|&nbsp; <strong>Pages:</strong> ${crawlStats.pages} &nbsp;|&nbsp; <strong>Artifacts:</strong> ${crawlStats.artifacts}</div>
</header>
<h2>Extracted Artifacts</h2>
<table><thead><tr><th>Type</th><th>Value</th></tr></thead><tbody>${rows}</tbody></table>
<footer>Generated by DRISHTI Dark Web OSINT Platform</footer>
</div></body></html>`;
        const el = document.createElement('a');
        el.href = URL.createObjectURL(new Blob([html], { type: 'text/html' }));
        el.download = `crawl_${url.replace(/[^a-z0-9]/gi, '_')}_${Date.now()}.html`;
        el.click();
    };

    const handleCrawl = async (e) => {
        e.preventDefault();
        if (!url.trim()) {
            toast.warning('Please enter a URL to crawl');
            return;
        }

        setIsCrawling(true);
        setLogs([]);
        setArtifacts(null);
        setCrawlStats({ pages: 0, artifacts: 0 });

        toast.info('Starting deep crawl...');

        let crawlUrl = url.trim();
        if (!crawlUrl.startsWith('http://') && !crawlUrl.startsWith('https://')) {
            crawlUrl = 'http://' + crawlUrl;
        }

        const eventSource = new EventSource(`/crawl?url=${encodeURIComponent(crawlUrl)}&depth=${depth}`);
        eventSourceRef.current = eventSource;
        let completed = false;

        eventSource.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);

                if (data.stage !== 'complete') {
                    setLogs(prev => [...prev, { stage: data.stage, message: data.message || '' }]);
                }

                if (data.stage === 'complete') {
                    completed = true;
                    setArtifacts(data.artifacts);
                    const totalArtifacts = Object.values(data.artifacts || {}).reduce((sum, v) => sum + (Array.isArray(v) ? v.length : 0), 0);
                    setCrawlStats(prev => ({ pages: prev.pages, artifacts: totalArtifacts }));
                    eventSource.close();
                    eventSourceRef.current = null;
                    setIsCrawling(false);
                    toast.success('Crawl completed successfully!');
                } else if (data.stage === 'crawling') {
                    setCrawlStats(prev => ({ ...prev, pages: prev.pages + 1 }));
                } else if (data.stage === 'error') {
                    completed = true;
                    setLogs(prev => [...prev, { stage: 'error', message: data.message }]);
                    eventSource.close();
                    eventSourceRef.current = null;
                    setIsCrawling(false);
                    toast.error(`Crawl failed: ${data.message}`);
                }
            } catch (err) {
                console.error("Error parsing SSE:", err, event.data);
                toast.error('Error processing server response');
            }
        };

        eventSource.onerror = (err) => {
            if (completed) return;  // normal close after complete event
            console.error("SSE Error:", err);
            eventSource.close();
            eventSourceRef.current = null;
            setIsCrawling(false);
            toast.error('Connection to server lost. Please check if the backend is running.');
        };
    };

    return (
        <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 20 }}
            className="crawl-mode"
        >
            <form onSubmit={handleCrawl} className="crawl-form glass-panel">
                <div className="input-group">
                    <Globe className="input-icon" />
                    <input
                        type="text"
                        value={url}
                        onChange={(e) => setUrl(e.target.value)}
                        placeholder="Enter .onion URL to crawl..."
                        className="crawl-input"
                        disabled={isCrawling}
                    />
                </div>
                <div className="depth-control">
                    <label>Depth:</label>
                    <select value={depth} onChange={(e) => setDepth(Number(e.target.value))} disabled={isCrawling}>
                        <option value="1">1 (Fast)</option>
                        <option value="2">2 (Balanced)</option>
                        <option value="3">3 (Deep)</option>
                    </select>
                </div>
                {isCrawling ? (
                    <button
                        type="button"
                        className="btn-cancel"
                        onClick={handleAbort}
                    >
                        Cancel <XCircle size={16} />
                    </button>
                ) : (
                    <button type="submit" className="btn-primary">
                        Start Crawl <Play size={16} />
                    </button>
                )}
            </form>

            <div className="dashboard-grid">
                <div className="left-col">
                    <Terminal logs={logs} isActive={isCrawling} />
                </div>
                <div className="right-col">
                    {/* Placeholder for live stats if available, or just description */}
                    <div className="info-panel glass-panel">
                        <h3><Layers size={20} /> Crawler Capabilities</h3>
                        <ul>
                            <li>Extracts Emails, Crypto Addresses</li>
                            <li>Maps Internal Links</li>
                            <li>Identifies Social Media Profiles</li>
                            <li>Detects Hidden Services</li>
                        </ul>
                    </div>
                </div>
            </div>

            {artifacts && (
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="artifacts-section glass-panel"
                >
                    <div className="crawl-report-header">
                        <h2>Extracted Artifacts</h2>
                        <div className="crawl-stats-bar">
                            <span className="crawl-stat">🌐 <strong>{crawlStats.pages}</strong> pages crawled</span>
                            <span className="crawl-stat">🔍 <strong>{crawlStats.artifacts}</strong> artifacts found</span>
                            <span className="crawl-stat">🎯 Target: <strong>{url}</strong></span>
                        </div>
                        <div className="crawl-export-buttons">
                            <button className="export-btn" onClick={() => setShowGraph(true)} title="View Entity Graph">
                                <GitFork size={15} /> Graph
                            </button>
                            <button className="export-btn" onClick={handleExportMarkdown} title="Download Markdown Report">
                                <FileText size={15} /> Markdown
                            </button>
                            <button className="export-btn" onClick={handleExportHTML} title="Download HTML Report">
                                <FileCode size={15} /> HTML
                            </button>
                            <button className="export-btn" onClick={handleExportJSON} title="Download JSON">
                                <FileJson size={15} /> JSON
                            </button>
                            <button className="export-btn" onClick={() => window.print()} title="Print / Save as PDF">
                                <Printer size={15} /> PDF
                            </button>
                        </div>
                    </div>
                    <ArtifactsViewer artifacts={artifacts} />
                </motion.div>
            )}

            {showGraph && artifacts && (
                <GraphView
                    query={url}
                    artifacts={{ [url]: artifacts }}
                    onClose={() => setShowGraph(false)}
                />
            )}
        </motion.div>
    );
};

export default CrawlMode;
