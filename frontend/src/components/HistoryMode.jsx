import React from 'react';
import { Clock, Trash2, Search, X, ArrowRight } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useHistory } from '../hooks/useHistory';
import '../styles/HistoryMode.css';

const HistoryMode = ({ onSearch }) => {
    const { history, clearHistory, removeFromHistory } = useHistory();

    return (
        <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 20 }}
            className="history-mode"
        >
            <div className="history-container glass-panel">
                <div className="history-header-main">
                    <div className="header-left">
                        <Clock size={24} className="header-icon" />
                        <h2>Search History</h2>
                    </div>
                    {history.length > 0 && (
                        <button onClick={clearHistory} className="btn-clear-all">
                            <Trash2 size={16} /> Clear All
                        </button>
                    )}
                </div>

                <div className="history-content">
                    {history.length === 0 ? (
                        <div className="empty-state">
                            <Clock size={48} />
                            <p>No search history yet</p>
                            <span className="sub-text">Your recent investigations will appear here</span>
                        </div>
                    ) : (
                        <div className="history-grid">
                            <AnimatePresence>
                                {history.map((query, index) => (
                                    <motion.div
                                        key={query}
                                        initial={{ opacity: 0, y: 20 }}
                                        animate={{ opacity: 1, y: 0 }}
                                        exit={{ opacity: 0, scale: 0.9 }}
                                        transition={{ delay: index * 0.05 }}
                                        className="history-card"
                                        onClick={() => onSearch(query)}
                                    >
                                        <div className="card-content">
                                            <Search size={16} className="card-icon" />
                                            <span className="query-text">{query}</span>
                                        </div>
                                        <div className="card-actions">
                                            <button
                                                className="btn-action btn-delete"
                                                onClick={(e) => {
                                                    e.stopPropagation();
                                                    removeFromHistory(query);
                                                }}
                                                title="Remove from history"
                                            >
                                                <X size={14} />
                                            </button>
                                            <button className="btn-action btn-go" title="Run investigation">
                                                <ArrowRight size={14} />
                                            </button>
                                        </div>
                                    </motion.div>
                                ))}
                            </AnimatePresence>
                        </div>
                    )}
                </div>
            </div>
        </motion.div>
    );
};

export default HistoryMode;
