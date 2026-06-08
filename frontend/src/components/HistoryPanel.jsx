import React from 'react';
import { Clock, X, Trash2 } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import '../styles/HistoryPanel.css';

const HistoryPanel = ({ history, onSelect, onClear, onRemove }) => {
    if (history.length === 0) return null;

    return (
        <div className="history-panel glass-panel">
            <div className="history-header">
                <div className="history-title">
                    <Clock size={16} />
                    <span>Recent Searches</span>
                </div>
                <button onClick={onClear} className="clear-history-btn" title="Clear all">
                    <Trash2 size={14} />
                </button>
            </div>
            <div className="history-list">
                <AnimatePresence>
                    {history.map((item, index) => (
                        <motion.div
                            key={item}
                            initial={{ opacity: 0, x: -10 }}
                            animate={{ opacity: 1, x: 0 }}
                            exit={{ opacity: 0, x: 10 }}
                            transition={{ delay: index * 0.05 }}
                            className="history-item"
                        >
                            <span onClick={() => onSelect(item)} className="history-text">
                                {item}
                            </span>
                            <button
                                onClick={(e) => {
                                    e.stopPropagation();
                                    onRemove(item);
                                }}
                                className="remove-item-btn"
                            >
                                <X size={12} />
                            </button>
                        </motion.div>
                    ))}
                </AnimatePresence>
            </div>
        </div>
    );
};

export default HistoryPanel;
