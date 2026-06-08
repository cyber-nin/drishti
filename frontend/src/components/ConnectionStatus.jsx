import React from 'react';
import { Wifi, WifiOff } from 'lucide-react';
import { useConnectionStatus } from '../hooks/useConnectionStatus';
import '../styles/ConnectionStatus.css';

const ConnectionStatus = () => {
    const { isOnline, checkConnection } = useConnectionStatus();

    return (
        <div
            className={`connection-status ${isOnline ? 'online' : 'offline'}`}
            onClick={checkConnection}
            title={isOnline ? "Backend Connected" : "Backend Disconnected - Click to retry"}
        >
            <div className="status-indicator">
                <div className="status-dot"></div>
                <div className="status-ping"></div>
            </div>
            <span className="status-text">
                {isOnline ? 'System Online' : 'System Offline'}
            </span>
            {isOnline ? <Wifi size={14} className="status-icon" /> : <WifiOff size={14} className="status-icon" />}
        </div>
    );
};

export default ConnectionStatus;
