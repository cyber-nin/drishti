import { useState, useEffect, useCallback } from 'react';

export const useConnectionStatus = (interval = 30000) => {
    const [isOnline, setIsOnline] = useState(true);
    const [lastChecked, setLastChecked] = useState(null);

    const checkConnection = useCallback(async () => {
        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 5000);

            const response = await fetch('/health', {
                signal: controller.signal,
                headers: { 'Cache-Control': 'no-cache' }
            });

            clearTimeout(timeoutId);

            if (response.ok) {
                setIsOnline(true);
                setLastChecked(new Date());
            } else {
                setIsOnline(false);
            }
        } catch (error) {
            console.error('Connection check failed:', error);
            setIsOnline(false);
        }
    }, []);

    useEffect(() => {
        checkConnection();
        const intervalId = setInterval(checkConnection, interval);
        return () => clearInterval(intervalId);
    }, [checkConnection, interval]);

    return { isOnline, lastChecked, checkConnection };
};
