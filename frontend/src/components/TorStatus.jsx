import React, { useState, useEffect, useCallback } from 'react';
import { Wifi, WifiOff, RefreshCw, Power, PowerOff, RotateCcw } from 'lucide-react';
import '../styles/TorStatus.css';

const TorStatus = () => {
    const [status, setStatus] = useState(null);
    const [loading, setLoading] = useState(false);
    const [message, setMessage] = useState('');

    const fetchStatus = useCallback(async () => {
        try {
            const r = await fetch('/tor/status');
            const data = await r.json();
            setStatus(data);
        } catch {
            setStatus(null);
        }
    }, []);

    // Poll every 5 seconds
    useEffect(() => {
        fetchStatus();
        const id = setInterval(fetchStatus, 5000);
        return () => clearInterval(id);
    }, [fetchStatus]);

    const handleConnect = async () => {
        setLoading(true);
        setMessage('Launching Tor...');
        try {
            const r = await fetch('/tor/connect', { method: 'POST' });
            const data = await r.json();
            setMessage(data.message);
            await fetchStatus();
        } catch (e) {
            setMessage('Failed to connect');
        }
        setLoading(false);
    };

    const handleDisconnect = async () => {
        setLoading(true);
        try {
            const r = await fetch('/tor/disconnect', { method: 'POST' });
            const data = await r.json();
            setMessage(data.message);
            await fetchStatus();
        } catch {
            setMessage('Failed to disconnect');
        }
        setLoading(false);
    };

    const handleRotate = async () => {
        setLoading(true);
        setMessage('Rotating circuit...');
        try {
            const r = await fetch('/tor/rotate', { method: 'POST' });
            const data = await r.json();
            setMessage(data.success ? 'Circuit rotated ✓' : data.message);
        } catch {
            setMessage('Rotation failed');
        }
        setLoading(false);
        setTimeout(() => setMessage(''), 3000);
    };

    const isRunning = status?.running;

    return (
        <div className="tor-status">
            {/* Header row */}
            <div className="tor-header">
                <div className={`tor-indicator ${isRunning ? 'online' : 'offline'}`}>
                    <span className="tor-dot" />
                    {isRunning ? <Wifi size={12} /> : <WifiOff size={12} />}
                    <span className="tor-label">TOR</span>
                    <span className="tor-state">{isRunning ? 'CONNECTED' : 'OFFLINE'}</span>
                </div>
                <button
                    className="tor-refresh"
                    onClick={fetchStatus}
                    title="Refresh status"
                >
                    <RefreshCw size={11} />
                </button>
            </div>

            {/* Message */}
            {message && (
                <div className="tor-message">{message}</div>
            )}

            {/* Actions */}
            <div className="tor-actions">
                {!isRunning ? (
                    <button
                        className="tor-btn tor-btn-connect"
                        onClick={handleConnect}
                        disabled={loading}
                    >
                        {loading ? <RefreshCw size={11} className="spin" /> : <Power size={11} />}
                        {loading ? 'Connecting...' : 'Auto Connect'}
                    </button>
                ) : (
                    <>
                        <button
                            className="tor-btn tor-btn-rotate"
                            onClick={handleRotate}
                            disabled={loading || !status?.stem_available}
                            title={!status?.stem_available ? 'Install stem: pip install stem' : 'Get new Tor circuit'}
                        >
                            <RotateCcw size={11} />
                            New Circuit
                        </button>
                        {status?.auto_launched && (
                            <button
                                className="tor-btn tor-btn-disconnect"
                                onClick={handleDisconnect}
                                disabled={loading}
                            >
                                <PowerOff size={11} />
                                Stop
                            </button>
                        )}
                    </>
                )}
            </div>

            {/* Info */}
            {status && (
                <div className="tor-info">
                    <span>{status.host}:{status.port}</span>
                    {status.auto_launched && <span className="tor-badge">auto</span>}
                </div>
            )}
        </div>
    );
};

export default TorStatus;
