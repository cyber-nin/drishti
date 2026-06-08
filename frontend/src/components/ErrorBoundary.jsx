import React from 'react';
import { AlertTriangle } from 'lucide-react';
import '../styles/ErrorBoundary.css';

class ErrorBoundary extends React.Component {
    constructor(props) {
        super(props);
        this.state = { hasError: false, error: null, errorInfo: null };
    }

    static getDerivedStateFromError(error) {
        return { hasError: true };
    }

    componentDidCatch(error, errorInfo) {
        console.error('Error caught by boundary:', error, errorInfo);
        this.setState({ error, errorInfo });
    }

    render() {
        if (this.state.hasError) {
            return (
                <div className="error-boundary">
                    <div className="error-content glass-panel">
                        <AlertTriangle size={48} color="#ff4b4b" />
                        <h1>Something went wrong</h1>
                        <p>The application encountered an unexpected error.</p>
                        <button
                            className="btn-primary"
                            onClick={() => window.location.reload()}
                        >
                            Reload Application
                        </button>
                        {process.env.NODE_ENV === 'development' && this.state.error && (
                            <details className="error-details">
                                <summary>Error Details</summary>
                                <pre>{this.state.error.toString()}</pre>
                                <pre>{this.state.errorInfo?.componentStack}</pre>
                            </details>
                        )}
                    </div>
                </div>
            );
        }

        return this.props.children;
    }
}

export default ErrorBoundary;
