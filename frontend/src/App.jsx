import React, { useState } from 'react';
import Sidebar from './components/Sidebar';
import SearchMode from './components/SearchMode';
import CrawlMode from './components/CrawlMode';
import HistoryMode from './components/HistoryMode';
import BatchMode from './components/BatchMode';
import DashboardMode from './components/DashboardMode';
import WatchlistMode from './components/WatchlistMode';
import ActorMode from './components/ActorMode';
import SealsMode from './components/SealsMode';
import ErrorBoundary from './components/ErrorBoundary';
import { ToastProvider } from './components/Toast';
import { Shield } from 'lucide-react';
import { AnimatePresence } from 'framer-motion';
import './styles/App.css';

function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [initialQuery, setInitialQuery] = useState('');
  const [config, setConfig] = useState({ model: 'gpt-5-mini', threads: 5 });

  const handleHistorySearch = (query) => {
    setInitialQuery(query);
    setActiveTab('search');
  };

  return (
    <ToastProvider>
      <ErrorBoundary>
        <div className="app-container">
          <Sidebar
            activeTab={activeTab}
            setActiveTab={setActiveTab}
            config={config}
            setConfig={setConfig}
          />
          <main className="main-content">
            <header className="app-header">
              <div className="header-content">
                <div className="header-logo">
                  <Shield size={18} color="var(--saffron-light)" />
                  <h1 className="header-title gradient-text">DRISHTI</h1>
                </div>
                <div className="header-divider" />
                <span className="header-subtitle">Dark Web OSINT Platform</span>
              </div>
              <div className="header-branding">
                <p className="branding-text">
                  Made with <span className="branding-heart">❤️</span> by{' '}
                  <span className="branding-name">Paras Jangid</span>
                </p>
              </div>
            </header>

            <div className="content-wrapper">
              <AnimatePresence mode="wait">
                {activeTab === 'dashboard' ? (
                  <DashboardMode key="dashboard" />
                ) : activeTab === 'watchlist' ? (
                  <WatchlistMode key="watchlist" />
                ) : activeTab === 'actor' ? (
                  <ActorMode key="actor" />
                ) : activeTab === 'seals' ? (
                  <SealsMode key="seals" />
                ) : activeTab === 'search' ? (
                  <SearchMode key="search" config={config} initialQuery={initialQuery} />
                ) : activeTab === 'crawl' ? (
                  <CrawlMode key="crawl" config={config} />
                ) : activeTab === 'batch' ? (
                  <BatchMode key="batch" config={config} />
                ) : (
                  <HistoryMode key="history" onSearch={handleHistorySearch} />
                )}
              </AnimatePresence>
            </div>
          </main>
        </div>
      </ErrorBoundary>
    </ToastProvider>
  );
}

export default App;

