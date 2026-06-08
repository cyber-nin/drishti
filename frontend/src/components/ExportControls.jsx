import React from 'react';
import { FileText, FileJson, Printer, Download, Shield, Table, FileCode } from 'lucide-react';
import '../styles/ExportControls.css';

const ExportControls = ({ content, query, stats, filename }) => {
    const getTimestamp = () => {
        return new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
    };

    const handleDownloadMarkdown = () => {
        const url = URL.createObjectURL(new Blob([content], { type: 'text/markdown' }));
        const element = document.createElement("a");
        element.href = url;
        element.download = `investigation_${query.replace(/\s+/g, '_')}_${getTimestamp()}.md`;
        document.body.appendChild(element);
        element.click();
        document.body.removeChild(element);
        URL.revokeObjectURL(url);
    };

    const handleDownloadJSON = () => {
        const data = { query, timestamp: new Date().toISOString(), stats, content };
        const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' }));
        const element = document.createElement("a");
        element.href = url;
        element.download = `investigation_${query.replace(/\s+/g, '_')}_${getTimestamp()}.json`;
        document.body.appendChild(element);
        element.click();
        document.body.removeChild(element);
        URL.revokeObjectURL(url);
    };

    const handleBackendExport = (format) => {
        if (!filename) return;
        const link = document.createElement('a');
        link.href = `/export/${filename}?format=${format}`;
        link.download = filename.replace('.md', `_export.${format === 'stix2' ? 'json' : format}`);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    };

    const handlePrintPDF = () => window.print();

    return (
        <div className="export-controls glass-panel">
            <div className="export-label">
                <Download size={16} />
                <span>Export Report</span>
            </div>
            <div className="export-buttons">
                <button onClick={handleDownloadMarkdown} className="export-btn" title="Download Markdown">
                    <FileText size={16} />
                    <span>Markdown</span>
                </button>
                <button onClick={handleDownloadJSON} className="export-btn" title="Download JSON">
                    <FileJson size={16} />
                    <span>JSON</span>
                </button>
                <button onClick={() => handleBackendExport('html')} className="export-btn" title="Download HTML Report" disabled={!filename}>
                    <FileCode size={16} />
                    <span>HTML</span>
                </button>
                <button onClick={() => handleBackendExport('csv')} className="export-btn" title="Download CSV" disabled={!filename}>
                    <Table size={16} />
                    <span>CSV</span>
                </button>
                <button onClick={() => handleBackendExport('stix2')} className="export-btn" title="Download STIX2 Bundle" disabled={!filename}>
                    <Shield size={16} />
                    <span>STIX2</span>
                </button>
                <button onClick={handlePrintPDF} className="export-btn" title="Print / Save as PDF">
                    <Printer size={16} />
                    <span>PDF</span>
                </button>
            </div>
        </div>
    );
};

export default ExportControls;
