import React from 'react';
import { Search, Globe, Settings, Activity, Clock, List, LayoutDashboard, Eye, Users, FileCheck } from 'lucide-react';
import ConnectionStatus from './ConnectionStatus';
import TorStatus from './TorStatus';
import '../styles/Sidebar.css';

const Sidebar = ({ activeTab, setActiveTab, config, setConfig }) => {
    const models = [
        // Ollama (local)
        { value: 'minimax-m2',    label: 'MiniMax M2 (Local)' },
        { value: 'minimax-m2.5', label: 'MiniMax M2.5 (Local)' },
        { value: 'kimi-k2.5',    label: 'Kimi K2.5 (Local)' },
        { value: 'llama3.2',     label: 'Llama 3.2 (Local)' },
        { value: 'llama3.1',     label: 'Llama 3.1 (Local)' },
        { value: 'gemma3',       label: 'Gemma 3 (Local)' },
        // OpenAI
        { value: 'gpt-4.1',      label: 'GPT-4.1' },
        { value: 'gpt-5.1',      label: 'GPT-5.1' },
        { value: 'gpt-5-mini',   label: 'GPT-5 Mini' },
        { value: 'gpt-5-nano',   label: 'GPT-5 Nano' },
        // Anthropic
        { value: 'claude-sonnet-4-5', label: 'Claude Sonnet 4.5' },
        { value: 'claude-sonnet-4-0', label: 'Claude Sonnet 4.0' },
        // Google
        { value: 'gemini-2.5-flash',      label: 'Gemini 2.5 Flash' },
        { value: 'gemini-2.5-flash-lite', label: 'Gemini 2.5 Flash Lite' },
        { value: 'gemini-2.5-pro',        label: 'Gemini 2.5 Pro' },
        { value: 'gemini-1.5-pro',        label: 'Gemini 1.5 Pro' },
        // DeepSeek
        { value: 'deepseek-r1', label: 'DeepSeek R1' },
        // Groq
        { value: 'llama-3.1-70b-groq', label: 'Llama 3.1 70B (Groq)' },
        { value: 'llama-3.1-8b-groq',  label: 'Llama 3.1 8B (Groq)' },
        { value: 'mixtral-8x7b-groq',  label: 'Mixtral 8x7B (Groq)' },
        // HuggingFace
        { value: 'llama-3.1-70b-hf', label: 'Llama 3.1 70B (HF)' },
        { value: 'llama-3.1-8b-hf',  label: 'Llama 3.1 8B (HF)' },
        { value: 'mistral-7b-hf',    label: 'Mistral 7B (HF)' },
        // NVIDIA NIM
        { value: 'nemotron-70b-nim',   label: 'Nemotron 70B (NIM)' },
        { value: 'nemotron-ultra-nim', label: 'Nemotron Ultra 340B (NIM)' },
        { value: 'mistral-large-nim',  label: 'Mistral Large 2 (NIM)' },
        { value: 'mistral-medium-nim', label: 'Mistral Medium 3.5 (NIM)' },
        { value: 'nemotron-mini-nim',  label: 'Nemotron Mini 4B (NIM)' },
        // OpenRouter (paid)
        { value: 'llama-4-scout-or',   label: 'Llama 4 Scout (OR)' },
        { value: 'llama-4-maverick-or',label: 'Llama 4 Maverick (OR)' },
        { value: 'deepseek-v3-or',     label: 'DeepSeek V3 (OR)' },
        { value: 'deepseek-r1-or',     label: 'DeepSeek R1 (OR)' },
        { value: 'qwen3-coder-or',     label: 'Qwen3 Coder (OR)' },
        { value: 'qwen3-max-or',       label: 'Qwen3 Max (OR)' },
        { value: 'mistral-medium-or',  label: 'Mistral Medium 3 (OR)' },
        { value: 'claude-3-7-or',      label: 'Claude 3.7 Sonnet (OR)' },
        // OpenRouter FREE tier — no credit card needed!
        { value: 'auto-free-or',             label: '⚡ Auto Best Free (OR)' },
        { value: 'llama-4-maverick-free-or', label: '🆓 Llama 4 Maverick' },
        { value: 'llama-4-scout-free-or',    label: '🆓 Llama 4 Scout' },
        { value: 'deepseek-r1-free-or',      label: '🆓 DeepSeek R1' },
        { value: 'deepseek-v4-flash-free-or',label: '🆓 DeepSeek V4 Flash' },
        { value: 'qwen3-coder-free-or',      label: '🆓 Qwen3 Coder' },
        { value: 'gemma-4-31b-free-or',      label: '🆓 Gemma 4 31B' },
        { value: 'llama-3-3-70b-free-or',    label: '🆓 Llama 3.3 70B' },
    ];

    const modelGroups = [
        { label: 'Local (Ollama)',  prefix: ['minimax', 'kimi', 'llama3', 'gemma'] },
        { label: 'OpenAI',         prefix: ['gpt'] },
        { label: 'Anthropic',      prefix: ['claude'] },
        { label: 'Google',         prefix: ['gemini'] },
        { label: 'DeepSeek',       prefix: ['deepseek'] },
        { label: 'Groq',           prefix: ['llama-3.1-70b-groq', 'llama-3.1-8b-groq', 'mixtral'] },
        { label: 'HuggingFace',    prefix: ['llama-3.1-70b-hf', 'llama-3.1-8b-hf', 'mistral-7b'] },
        { label: 'NVIDIA NIM',     prefix: ['-nim'] },
        { label: 'OpenRouter',     prefix: ['-or'] },
        { label: 'Free Tier ✨ (OpenRouter)', prefix: ['-free-or', 'auto-free'] },
    ];

    const getGroup = (val) => {
        if (['minimax-m2', 'minimax-m2.5', 'kimi-k2.5', 'llama3.2', 'llama3.1', 'gemma3'].includes(val)) return 'Local (Ollama)';
        if (val.startsWith('gpt')) return 'OpenAI';
        if (val.startsWith('claude') && !val.endsWith('-or')) return 'Anthropic';
        if (val.startsWith('gemini')) return 'Google';
        if (val.startsWith('deepseek') && !val.endsWith('-or') && !val.includes('-free')) return 'DeepSeek';
        if (val.endsWith('-groq')) return 'Groq';
        if (val.endsWith('-hf')) return 'HuggingFace';
        if (val.endsWith('-nim')) return 'NVIDIA NIM';
        // Free tier check must come before generic -or check
        if (val.endsWith('-free-or') || val === 'auto-free-or') return 'Free Tier ✨ (OpenRouter)';
        if (val.endsWith('-or')) return 'OpenRouter';
        return 'Other';
    };

    const grouped = models.reduce((acc, m) => {
        const g = getGroup(m.value);
        if (!acc[g]) acc[g] = [];
        acc[g].push(m);
        return acc;
    }, {});

    return (
        <aside className="sidebar glass-panel">
            <div className="sidebar-header">
                <div className="header-main">
                    <div className="logo-text gradient-text">DRISHTI</div>
                    <div className="version-badge">v2.0</div>
                </div>
            </div>

            <nav className="sidebar-nav">
                <div className="nav-section">
                    <div className="section-label">MONITORING</div>
                    <button
                        className={`nav-item ${activeTab === 'dashboard' ? 'active' : ''}`}
                        onClick={() => setActiveTab('dashboard')}
                    >
                        <LayoutDashboard size={18} />
                        <span>Intel Dashboard</span>
                    </button>
                    <button
                        className={`nav-item ${activeTab === 'watchlist' ? 'active' : ''}`}
                        onClick={() => setActiveTab('watchlist')}
                    >
                        <Eye size={18} />
                        <span>Monitored Watchlists</span>
                    </button>
                    <button
                        className={`nav-item ${activeTab === 'actor' ? 'active' : ''}`}
                        onClick={() => setActiveTab('actor')}
                    >
                        <Users size={18} />
                        <span>Threat Actors</span>
                    </button>
                    <button
                        className={`nav-item ${activeTab === 'seals' ? 'active' : ''}`}
                        onClick={() => setActiveTab('seals')}
                    >
                        <FileCheck size={18} />
                        <span>Evidence Seals</span>
                    </button>
                </div>

                <div className="nav-section">
                    <div className="section-label">INVESTIGATION</div>
                    <button
                        className={`nav-item ${activeTab === 'search' ? 'active' : ''}`}
                        onClick={() => setActiveTab('search')}
                    >
                        <Search size={18} />
                        <span>Active Scanner</span>
                    </button>
                    <button
                        className={`nav-item ${activeTab === 'crawl' ? 'active' : ''}`}
                        onClick={() => setActiveTab('crawl')}
                    >
                        <Globe size={18} />
                        <span>Deep Crawler</span>
                    </button>
                    <button
                        className={`nav-item ${activeTab === 'batch' ? 'active' : ''}`}
                        onClick={() => setActiveTab('batch')}
                    >
                        <List size={18} />
                        <span>Batch Scans</span>
                    </button>
                    <button
                        className={`nav-item ${activeTab === 'history' ? 'active' : ''}`}
                        onClick={() => setActiveTab('history')}
                    >
                        <Clock size={18} />
                        <span>History</span>
                    </button>
                </div>

                <div className="nav-section">
                    <div className="section-label">CONFIGURATION</div>
                    <div className="config-item">
                        <label><Settings size={14} /> Model</label>
                        <select
                            value={config.model}
                            onChange={(e) => setConfig({ ...config, model: e.target.value })}
                        >
                            {Object.entries(grouped).map(([group, items]) => (
                                <optgroup key={group} label={group}>
                                    {items.map(m => (
                                        <option key={m.value} value={m.value}>{m.label}</option>
                                    ))}
                                </optgroup>
                            ))}
                        </select>
                    </div>
                    <div className="config-item">
                        <label><Activity size={14} /> Threads: {config.threads}</label>
                        <input
                            type="range"
                            min="1"
                            max="16"
                            value={config.threads}
                            onChange={(e) => setConfig({ ...config, threads: parseInt(e.target.value) })}
                        />
                    </div>
                </div>
            </nav>

            <div className="sidebar-footer">
                <TorStatus />
                <ConnectionStatus />
            </div>
        </aside>
    );
};

export default Sidebar;
