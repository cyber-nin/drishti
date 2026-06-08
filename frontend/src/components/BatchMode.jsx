import React, { useState, useRef, useEffect } from 'react';
import { List, Play, Plus, Trash2, Download, CheckCircle, XCircle, Loader } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useToast } from './Toast';
import '../styles/BatchMode.css';

const BatchMode = ({ config }) => {
    const [queries, setQueries] = useState(['']);
    const [jobId, setJobId] = useState(null);
    const [job, setJob] = useState(null);
    const [isRunning, setIsRunning] = useState(false);
    const pollRef = useRef(null);
    const toast = useToast();

    const addQuery = () => setQueries(prev => [...prev, '']);
    const removeQuery = (i) => setQueries(prev => prev.filter((_, idx) => idx !== i));
    const updateQuery = (i, val) => setQueries(prev => prev.map((q, idx) => idx === i ? val : q));

    const handleSubmit = async (e) => {
        e.preventDefault();
        const valid = queries.map(q => q.trim()).filter(Boolean);
        if (!valid.length) {
            toast.warning('Add at least one query');
            return;
        }
        setIsRunning(true);
        setJob(null);
        try {
            const resp = await fetch('/batch', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ queries: valid, model: config.model, threads: config.threads })
            });
            const data = await resp.json();
            if (!resp.ok) throw new Error(data.error || 'Failed to start batch');
            setJobId(data.job_id);
            toast.info(`Batch started — ${data.total} queries queued`);
        } catch (err) {
            toast.error(err.message);
            setIsRunning(false);
        }
    };

    // Poll job status
    useEffect(() => {
        if (!jobId) return;
        pollRef.current = setInterval(async () => {
            try {
                const resp = await fetch(`/batch/${jobId}`);
                const data = await resp.json();
                setJob(data);
                if (data.status === 'complete' || data.status === 'failed') {
                    clearInterval(pollRef.current);
                    setIsRunning(false);
                    data.status === 'complete'
                        ? toast.success(`Batch complete — ${data.results.length} reports generated`)
                        : toast.error('Batch job failed');
                }
            } catch (err) {
                clearInterval(pollRef.current);
                setIsRunning(false);
            }
        }, 2000);
        return () => clearInterval(pollRef.current);
    }, [jobId]);

    const progress = job ? Math.round((job.done / job.total) * 100) : 0;

    return (
        <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 20 }}
            className="batch-mode"
        >
            <form onSubmit={handleSubmit} className="batch-form glass-panel">
                <div className="batch-header">
                    <List size={20} />
                    <h3>Batch Investigation</h3>
                    <span className="batch-subtitle">Run multiple queries in one job</span>
                </div>

                <div className="query-list">
                    <AnimatePresence>
                        {queries.map((q, i) => (
                            <motion.div
                                key={i}
                                initial={{ opacity: 0, y: -8 }}
                                animate={{ opacity: 1, y: 0 }}
                                exit={{ opacity: 0, y: -8 }}
                                className="query-row"
                            >
                                <span className="query-num">{i + 1}</span>
                                <input
                                    type="text"
                                    value={q}
                                    onChange={e => updateQuery(i, e.target.value)}
                                    placeholder={`Query ${i + 1}...`}
                                    className="query-input"
                                    disabled={isRunning}
                                />
                                {queries.length > 1 && (
                                    <button type="button" className="btn-remove" onClick={() => removeQuery(i)} disabled={isRunning}>
                                        <Trash2 size={14} />
                                    </button>
                                )}
                            </motion.div>
                        ))}
                    </AnimatePresence>
                </div>

                <div className="batch-actions">
                    <button type="button" className="btn-add" onClick={addQuery} disabled={isRunning}>
                        <Plus size={15} /> Add Query
                    </button>
                    <button type="submit" className="btn-primary" disabled={isRunning}>
                        {isRunning ? <><Loader size={15} className="spin" /> Running...</> : <><Play size={15} /> Run Batch</>}
                    </button>
                </div>
            </form>

            {job && (
                <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="batch-status glass-panel">
                    <div className="status-header">
                        <span className={`status-badge ${job.status}`}>{job.status.toUpperCase()}</span>
                        <span className="status-count">{job.done} / {job.total} completed</span>
                    </div>

                    <div className="progress-bar-wrap">
                        <div className="progress-bar" style={{ width: `${progress}%` }} />
                    </div>

                    {job.results.length > 0 && (
                        <div className="result-list">
                            <h4>Completed Reports</h4>
                            {job.results.map((r, i) => (
                                <div key={i} className="result-row">
                                    <CheckCircle size={14} className="icon-success" />
                                    <span className="result-query">{r.query}</span>
                                    <a href={`/download/${r.filename}`} className="btn-download" download>
                                        <Download size={13} /> Download
                                    </a>
                                </div>
                            ))}
                        </div>
                    )}

                    {job.errors.length > 0 && (
                        <div className="error-list">
                            <h4>Errors</h4>
                            {job.errors.map((e, i) => (
                                <div key={i} className="error-row">
                                    <XCircle size={14} className="icon-error" />
                                    <span className="error-query">{e.query}</span>
                                    <span className="error-msg">{e.error}</span>
                                </div>
                            ))}
                        </div>
                    )}
                </motion.div>
            )}
        </motion.div>
    );
};

export default BatchMode;
