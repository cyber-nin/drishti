import React from 'react';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { Copy, Check } from 'lucide-react';
import '../styles/ReportView.css';

const ReportView = ({ content }) => {
    const [copiedCode, setCopiedCode] = React.useState(null);

    const copyToClipboard = (code, index) => {
        navigator.clipboard.writeText(code);
        setCopiedCode(index);
        setTimeout(() => setCopiedCode(null), 2000);
    };

    return (
        <div className="markdown-content">
            <ReactMarkdown
                components={{
                    code({ node, inline, className, children, ...props }) {
                        const match = /language-(\w+)/.exec(className || '');
                        const codeString = String(children).replace(/\n$/, '');
                        const codeIndex = `${match?.[1]}-${codeString.substring(0, 20)}`;

                        return !inline && match ? (
                            <div className="code-block-wrapper">
                                <div className="code-block-header">
                                    <span className="code-language">{match[1]}</span>
                                    <button
                                        className="copy-button"
                                        onClick={() => copyToClipboard(codeString, codeIndex)}
                                        title="Copy code"
                                    >
                                        {copiedCode === codeIndex ? (
                                            <>
                                                <Check size={14} />
                                                <span>Copied!</span>
                                            </>
                                        ) : (
                                            <>
                                                <Copy size={14} />
                                                <span>Copy</span>
                                            </>
                                        )}
                                    </button>
                                </div>
                                <SyntaxHighlighter
                                    style={vscDarkPlus}
                                    language={match[1]}
                                    PreTag="div"
                                    {...props}
                                >
                                    {codeString}
                                </SyntaxHighlighter>
                            </div>
                        ) : (
                            <code className={className} {...props}>
                                {children}
                            </code>
                        );
                    },
                    h1: ({ children }) => (
                        <h1 className="report-h1">{children}</h1>
                    ),
                    h2: ({ children }) => (
                        <h2 className="report-h2">{children}</h2>
                    ),
                    h3: ({ children }) => (
                        <h3 className="report-h3">{children}</h3>
                    ),
                    blockquote: ({ children }) => (
                        <blockquote className="report-blockquote">{children}</blockquote>
                    ),
                    a: ({ href, children }) => (
                        <a href={href} className="report-link" target="_blank" rel="noopener noreferrer">
                            {children}
                        </a>
                    ),
                    ul: ({ children }) => (
                        <ul className="report-list">{children}</ul>
                    ),
                    ol: ({ children }) => (
                        <ol className="report-list-ordered">{children}</ol>
                    ),
                    table: ({ children }) => (
                        <div className="table-wrapper">
                            <table className="report-table">{children}</table>
                        </div>
                    ),
                }}
            >
                {content}
            </ReactMarkdown>
        </div>
    );
};

export default ReportView;
