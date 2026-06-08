import React, { useState, useRef, useEffect } from 'react';
import { Search, Play, Download, FileText, XCircle, GitFork, ChevronDown, ChevronUp } from 'lucide-react';
import { motion } from 'framer-motion';
import Terminal from './Terminal';
import ReportView from './ReportView';
import { useToast } from './Toast';
import { TerminalSkeleton, StatCardSkeleton } from './LoadingSkeleton';
import ExportControls from './ExportControls';
import GraphView from './GraphView';
import ArtifactsViewer from './ArtifactsViewer';
import { useHistory } from '../hooks/useHistory';
import '../styles/SearchMode.css';

const SearchMode = ({ config, initialQuery }) => {
    const [query, setQuery] = useState(initialQuery || '');
    const [isSearching, setIsSearching] = useState(false);
    const [logs, setLogs] = useState([]);
    const [stats, setStats] = useState({ results: 0, filtered: 0 });
    const [report, setReport] = useState(null);
    const [refinedQuery, setRefinedQuery] = useState('');
    const [downloadUrl, setDownloadUrl] = useState(null);
    const [allArtifacts, setAllArtifacts] = useState(null);
    const [showGraph, setShowGraph] = useState(false);
    const [showArtifacts, setShowArtifacts] = useState(false);
    const toast = useToast();
    const eventSourceRef = useRef(null);
    const { addToHistory } = useHistory();

    useEffect(() => {
        if (initialQuery) {
            setQuery(initialQuery);
        }
    }, [initialQuery]);

    const handleAbort = () => {
        if (eventSourceRef.current) {
            eventSourceRef.current.close();
            eventSourceRef.current = null;
            setIsSearching(false);
            setLogs(prev => [...prev, {
                stage: 'error',
                message: 'Investigation cancelled by user'
            }]);
            toast.warning('Investigation cancelled');
        }
    };

    const handleSearch = async (e) => {
        e.preventDefault();
        if (!query.trim()) {
            toast.warning('Please enter a search query');
            return;
        }

        setIsSearching(true);
        setLogs([]);
        setStats({ results: 0, filtered: 0 });
        setReport(null);
        setRefinedQuery('');
        setDownloadUrl(null);
        setAllArtifacts(null);
        setShowGraph(false);
        setShowArtifacts(false);

        // Add to history
        addToHistory(query);

        toast.info('Starting investigation...');

        const eventSource = new EventSource(`/investigate?query=${encodeURIComponent(query)}&model=${config.model}&threads=${config.threads}`);
        eventSourceRef.current = eventSource;
        let completed = false;

        eventSource.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);

                setLogs(prev => [...prev, { stage: data.stage, message: data.message || '' }]);

                if (data.stage === 'refined') {
                    setRefinedQuery(data.data);
                } else if (data.stage === 'results') {
                    setStats(prev => ({ ...prev, results: data.data }));
                } else if (data.stage === 'filtered') {
                    setStats(prev => ({ ...prev, filtered: data.data }));
                } else if (data.stage === 'complete') {
                    completed = true;
                    setReport(data.summary);
                    setDownloadUrl(data.filename);
                    if (data.artifacts) setAllArtifacts(data.artifacts);
                    eventSource.close();
                    eventSourceRef.current = null;
                    setIsSearching(false);
                    toast.success('Investigation completed successfully!');
                } else if (data.stage === 'error') {
                    completed = true;
                    setLogs(prev => [...prev, { stage: 'error', message: data.message }]);
                    eventSource.close();
                    eventSourceRef.current = null;
                    setIsSearching(false);
                    toast.error(`Investigation failed: ${data.message}`);
                }
            } catch (err) {
                console.error("Error parsing SSE:", err);
                toast.error('Error processing server response');
            }
        };

        eventSource.onerror = (err) => {
            if (completed) return;
            console.error("SSE Error:", err);
            eventSource.close();
            eventSourceRef.current = null;
            setIsSearching(false);
            toast.error('Connection to server lost. Please check if the backend is running.');
        };
    };

    return (
        <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            className="search-mode"
        >
            <form onSubmit={handleSearch} className="search-form glass-panel">
                <Search className="search-icon" />
                <input
                    type="text"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    placeholder="Enter target, keyword, or topic to investigate..."
                    className="search-input"
                    disabled={isSearching}
                />
                {isSearching ? (
                    <button
                        type="button"
                        className="btn-cancel"
                        onClick={handleAbort}
                    >
                        Cancel <XCircle size={16} />
                    </button>
                ) : (
                    <button type="submit" className="btn-primary">
                        Investigate <Play size={16} />
                    </button>
                )}
            </form>

            {refinedQuery && (
                <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="refined-query glass-panel"
                >
                    <span className="label">Refined Target:</span>
                    <span className="value">{refinedQuery}</span>
                </motion.div>
            )}

            <div className="dashboard-grid">
                <div className="left-col">
                    {logs.length === 0 && !isSearching ? (
                        <TerminalSkeleton />
                    ) : (
                        <Terminal logs={logs} isActive={isSearching} />
                    )}
                </div>
                <div className="right-col">
                    <div className="stats-grid">
                        {logs.length === 0 && !isSearching ? (
                            <>
                                <StatCardSkeleton />
                                <StatCardSkeleton />
                            </>
                        ) : (
                            <>
                                <div className="stat-card glass-panel">
                                    <div className="stat-label">Raw Hits</div>
                                    <div className="stat-value">{stats.results}</div>
                                </div>
                                <div className="stat-card glass-panel">
                                    <div className="stat-label">Verified</div>
                                    <div className="stat-value">{stats.filtered}</div>
                                </div>
                            </>
                        )}
                    </div>
                </div>
            </div>

            {report && (
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="report-section glass-panel report-view"
                >
                    <div className="report-header">
                        <h2><FileText size={24} /> Investigation Report</h2>
                        <div className="report-header-actions">
                            <button
                                className="btn-graph"
                                onClick={() => setShowArtifacts(v => !v)}
                                disabled={!allArtifacts}
                                title={allArtifacts ? 'Toggle artifacts panel' : 'No artifacts found'}
                            >
                                {showArtifacts ? <ChevronUp size={15} /> : <ChevronDown size={15} />} Artifacts
                            </button>
                            <button
                                className="btn-graph"
                                onClick={() => setShowGraph(true)}
                                disabled={!allArtifacts}
                                title={allArtifacts ? 'View entity graph' : 'No artifacts found'}
                            >
                                <GitFork size={15} /> Entity Graph
                            </button>
                        </div>
                    </div>

                    {showArtifacts && allArtifacts && (
                        <div className="artifacts-inline">
                            <ArtifactsViewer artifacts={
                                Object.values(allArtifacts).reduce((acc, src) => {
                                    Object.entries(src).forEach(([type, vals]) => {
                                        acc[type] = [...(acc[type] || []), ...(Array.isArray(vals) ? vals : Array.from(vals))];
                                    });
                                    return acc;
                                }, {})
                            } />
                        </div>
                    )}

                    <ExportControls content={report} query={query} stats={stats} filename={downloadUrl} />

                    <ReportView content={report} />
                </motion.div>
            )}

            {showGraph && allArtifacts && (
                <GraphView
                    query={query}
                    artifacts={allArtifacts}
                    onClose={() => setShowGraph(false)}
                />
            )}
        </motion.div>
    );
};

export default SearchMode;
