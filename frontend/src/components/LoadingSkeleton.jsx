import React from 'react';
import { motion } from 'framer-motion';
import '../styles/LoadingSkeleton.css';

const SKELETON_WIDTHS = ['72%', '88%', '65%', '80%', '91%'];

export const TerminalSkeleton = () => {
    return (
        <div className="terminal-window glass-panel">
            <div className="terminal-header">
                <div className="terminal-title">
                    <div className="skeleton skeleton-icon"></div>
                    <div className="skeleton skeleton-text-small"></div>
                </div>
                <div className="terminal-controls">
                    <div className="dot red"></div>
                    <div className="dot yellow"></div>
                    <div className="dot green"></div>
                </div>
            </div>
            <div className="terminal-body">
                {SKELETON_WIDTHS.map((w, i) => (
                    <div key={i} className="skeleton-log-line">
                        <div className="skeleton skeleton-timestamp"></div>
                        <div className="skeleton skeleton-stage"></div>
                        <div className="skeleton skeleton-message" style={{ width: w }}></div>
                    </div>
                ))}
            </div>
        </div>
    );
};

export const StatCardSkeleton = () => {
    return (
        <div className="stat-card glass-panel">
            <div className="skeleton skeleton-text-small" style={{ width: '80px', marginBottom: '0.5rem' }}></div>
            <div className="skeleton skeleton-stat-value"></div>
        </div>
    );
};

export const LoadingSpinner = ({ size = 'medium', message }) => {
    const sizeClasses = {
        small: 'spinner-small',
        medium: 'spinner-medium',
        large: 'spinner-large'
    };

    return (
        <div className="loading-spinner-container">
            <motion.div
                className={`loading-spinner ${sizeClasses[size]}`}
                animate={{ rotate: 360 }}
                transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
            >
                <div className="spinner-ring"></div>
            </motion.div>
            {message && <p className="spinner-message">{message}</p>}
        </div>
    );
};

export const ProgressBar = ({ progress, label }) => {
    return (
        <div className="progress-bar-container">
            {label && <div className="progress-label">{label}</div>}
            <div className="progress-bar-track">
                <motion.div
                    className="progress-bar-fill"
                    initial={{ width: 0 }}
                    animate={{ width: `${progress}%` }}
                    transition={{ duration: 0.3 }}
                />
            </div>
            <div className="progress-percentage">{Math.round(progress)}%</div>
        </div>
    );
};
