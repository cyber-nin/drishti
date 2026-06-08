import { useState, useEffect } from 'react';

const MAX_HISTORY_ITEMS = 10;

export const useHistory = (key = 'search_history') => {
    const [history, setHistory] = useState(() => {
        try {
            const item = window.localStorage.getItem(key);
            return item ? JSON.parse(item) : [];
        } catch (error) {
            console.error('Error reading history from localStorage:', error);
            return [];
        }
    });

    useEffect(() => {
        try {
            window.localStorage.setItem(key, JSON.stringify(history));
        } catch (error) {
            console.error('Error saving history to localStorage:', error);
        }
    }, [history, key]);

    const addToHistory = (query) => {
        if (!query || !query.trim()) return;

        setHistory(prev => {
            // Remove duplicates and add new item to the top
            const filtered = prev.filter(item => item !== query);
            return [query, ...filtered].slice(0, MAX_HISTORY_ITEMS);
        });
    };

    const clearHistory = () => {
        setHistory([]);
    };

    const removeFromHistory = (queryToRemove) => {
        setHistory(prev => prev.filter(item => item !== queryToRemove));
    };

    return { history, addToHistory, clearHistory, removeFromHistory };
};
