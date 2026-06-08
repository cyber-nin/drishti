import React, { useEffect, useRef } from 'react';
import { Terminal as TerminalIcon } from 'lucide-react';
import '../styles/Terminal.css';

const Terminal = ({ logs, isActive }) => {
    const bottomRef = useRef(null);
    const timestampsRef = useRef([]);

    // Capture timestamp when a new log arrives, not at render time
    if (timestampsRef.current.length < logs.length) {
        for (let i = timestampsRef.current.length; i < logs.length; i++) {
            timestampsRef.current.push(new Date().toLocaleTimeString());
        }
    } else if (logs.length === 0) {
        timestampsRef.current = [];
    }

    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [logs]);

    return (
        <div className="terminal-window glass-panel">
            <div className="terminal-header">
                <div className="terminal-title">
                    <TerminalIcon size={16} />
                    <span>SYSTEM_LOG</span>
                </div>
                <div className="terminal-controls">
                    <div className="dot red"></div>
                    <div className="dot yellow"></div>
                    <div className="dot green"></div>
                </div>
            </div>
            <div className="terminal-body">
                {logs.length === 0 && (
                    <div className="terminal-placeholder">
                        {isActive ? 'Initializing system...' : 'Ready for input...'}
                    </div>
                )}
                {logs.map((log, index) => (
                    <div key={index} className={`log-line ${log.stage}`}>
                        <span className="timestamp">[{timestampsRef.current[index] || ''}]</span>
                        <span className="stage">[{log.stage.toUpperCase()}]</span>
                        <span className="message">{log.message}</span>
                    </div>
                ))}
                {isActive && (
                    <div className="log-line active-cursor">
                        <span className="cursor">_</span>
                    </div>
                )}
                <div ref={bottomRef} />
            </div>
        </div>
    );
};

export default Terminal;
