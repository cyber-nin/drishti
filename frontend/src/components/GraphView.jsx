import React, { useEffect, useRef, useState, useCallback } from 'react';
import { GitFork, ZoomIn, ZoomOut, Maximize2, X } from 'lucide-react';
import '../styles/GraphView.css';

// ── Force simulation ──────────────────────────────────────────────────────────

function buildPositions(nodes, width, height) {
    const pos = {};
    nodes.forEach((n, i) => {
        const angle = (2 * Math.PI * i) / nodes.length;
        const r = Math.min(width, height) * 0.3;
        pos[n.id] = { x: width / 2 + r * Math.cos(angle), y: height / 2 + r * Math.sin(angle), vx: 0, vy: 0 };
    });
    return pos;
}

function tickOnce(pos, edges, width, height) {
    const k = 0.05, repulsion = 3000, linkDist = 120, damping = 0.85;
    const ids = Object.keys(pos);

    for (let i = 0; i < ids.length; i++) {
        for (let j = i + 1; j < ids.length; j++) {
            const a = pos[ids[i]], b = pos[ids[j]];
            const dx = b.x - a.x, dy = b.y - a.y;
            const dist = Math.sqrt(dx * dx + dy * dy) || 1;
            const force = repulsion / (dist * dist);
            const fx = (dx / dist) * force, fy = (dy / dist) * force;
            a.vx -= fx; a.vy -= fy; b.vx += fx; b.vy += fy;
        }
    }

    edges.forEach(e => {
        const a = pos[e.source], b = pos[e.target];
        if (!a || !b) return;
        const dx = b.x - a.x, dy = b.y - a.y;
        const dist = Math.sqrt(dx * dx + dy * dy) || 1;
        const force = (dist - linkDist) * k;
        const fx = (dx / dist) * force, fy = (dy / dist) * force;
        a.vx += fx; a.vy += fy; b.vx -= fx; b.vy -= fy;
    });

    ids.forEach(id => {
        const p = pos[id];
        p.vx += (width / 2 - p.x) * 0.002;
        p.vy += (height / 2 - p.y) * 0.002;
        p.vx *= damping; p.vy *= damping;
        p.x += p.vx; p.y += p.vy;
        p.x = Math.max(30, Math.min(width - 30, p.x));
        p.y = Math.max(30, Math.min(height - 30, p.y));
    });
}

// ── Canvas renderer ───────────────────────────────────────────────────────────

const NODE_RADIUS = { query: 18, source: 12, default: 8 };

function drawGraph(ctx, W, H, nodes, edges, pos, hoveredId, scale, offsetX, offsetY) {
    ctx.clearRect(0, 0, W, H);
    ctx.save();
    ctx.translate(offsetX, offsetY);
    ctx.scale(scale, scale);

    edges.forEach(e => {
        const a = pos[e.source], b = pos[e.target];
        if (!a || !b) return;
        ctx.beginPath();
        ctx.moveTo(a.x, a.y);
        ctx.lineTo(b.x, b.y);
        ctx.strokeStyle = e.relation === 'correlated' ? 'rgba(255,75,75,0.4)' : 'rgba(255,255,255,0.12)';
        ctx.lineWidth = e.relation === 'correlated' ? 1.5 : 1;
        ctx.stroke();
    });

    nodes.forEach(n => {
        const p = pos[n.id];
        if (!p) return;
        const r = NODE_RADIUS[n.type] || NODE_RADIUS.default;
        const isHovered = n.id === hoveredId;

        if (isHovered) {
            ctx.beginPath();
            ctx.arc(p.x, p.y, r + 6, 0, Math.PI * 2);
            ctx.fillStyle = n.color + '33';
            ctx.fill();
        }

        ctx.beginPath();
        ctx.arc(p.x, p.y, r, 0, Math.PI * 2);
        ctx.fillStyle = n.color;
        ctx.fill();
        ctx.strokeStyle = isHovered ? '#fff' : 'rgba(0,0,0,0.4)';
        ctx.lineWidth = isHovered ? 2 : 1;
        ctx.stroke();

        ctx.fillStyle = isHovered ? '#fff' : 'rgba(220,220,220,0.85)';
        ctx.font = `${n.type === 'query' ? 'bold ' : ''}${n.type === 'query' ? 11 : 9}px monospace`;
        ctx.textAlign = 'center';
        ctx.fillText(n.label.length > 22 ? n.label.slice(0, 20) + '…' : n.label, p.x, p.y + r + 12);
    });

    ctx.restore();
}

// ── Main component ────────────────────────────────────────────────────────────

const GraphView = ({ query, artifacts, onClose }) => {
    const canvasRef   = useRef(null);
    const wrapRef     = useRef(null);
    const animRef     = useRef(null);
    const posRef      = useRef({});
    const sizeRef     = useRef({ w: 0, h: 0 });
    const dragRef     = useRef(null);
    const settledRef  = useRef(false);

    const [graphData, setGraphData] = useState(null);
    const [loading, setLoading]     = useState(true);
    const [error, setError]         = useState(null);
    const [hoveredId, setHoveredId] = useState(null);
    const [tooltip, setTooltip]     = useState(null);
    const [scale, setScale]         = useState(1);
    const [offset, setOffset]       = useState({ x: 0, y: 0 });

    // ── Fetch graph data ──────────────────────────────────────────────────────
    useEffect(() => {
        setLoading(true);
        fetch('/graph', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query, artifacts })
        })
            .then(r => r.json())
            .then(data => { setGraphData(data); setLoading(false); })
            .catch(e => { setError(e.message); setLoading(false); });
    }, [query, artifacts]);

    // ── ResizeObserver — keep canvas resolution in sync with container ────────
    useEffect(() => {
        if (!wrapRef.current) return;
        const ro = new ResizeObserver(entries => {
            const { width, height } = entries[0].contentRect;
            if (!width || !height) return;
            sizeRef.current = { w: Math.round(width), h: Math.round(height) };
            if (canvasRef.current) {
                canvasRef.current.width  = sizeRef.current.w;
                canvasRef.current.height = sizeRef.current.h;
            }
            // Re-initialise positions when size changes
            if (graphData?.nodes.length) {
                posRef.current = buildPositions(graphData.nodes, sizeRef.current.w, sizeRef.current.h);
                settledRef.current = false;
            }
        });
        ro.observe(wrapRef.current);
        return () => ro.disconnect();
    }, [graphData]);

    // ── Simulation + render loop ──────────────────────────────────────────────
    useEffect(() => {
        if (!graphData || !canvasRef.current) return;

        const { w, h } = sizeRef.current;
        if (!posRef.current || Object.keys(posRef.current).length !== graphData.nodes.length) {
            posRef.current = buildPositions(graphData.nodes, w || 800, h || 500);
        }
        settledRef.current = false;

        let frame = 0;
        const SETTLE_FRAMES = 300;

        const loop = () => {
            const canvas = canvasRef.current;
            if (!canvas) return;
            const ctx = canvas.getContext('2d');
            const cw = canvas.width, ch = canvas.height;

            if (frame < SETTLE_FRAMES) {
                tickOnce(posRef.current, graphData.edges, cw, ch);
                frame++;
                drawGraph(ctx, cw, ch, graphData.nodes, graphData.edges, posRef.current, hoveredId, scale, offset.x, offset.y);
                animRef.current = requestAnimationFrame(loop);
            } else {
                // Settled — draw once and stop
                settledRef.current = true;
                drawGraph(ctx, cw, ch, graphData.nodes, graphData.edges, posRef.current, hoveredId, scale, offset.x, offset.y);
            }
        };

        animRef.current = requestAnimationFrame(loop);
        return () => cancelAnimationFrame(animRef.current);
    }, [graphData]); // only re-run when data changes

    // ── Redraw on interaction (hover / zoom / pan) after settling ─────────────
    useEffect(() => {
        if (!settledRef.current || !canvasRef.current || !graphData) return;
        const canvas = canvasRef.current;
        const ctx = canvas.getContext('2d');
        drawGraph(ctx, canvas.width, canvas.height, graphData.nodes, graphData.edges, posRef.current, hoveredId, scale, offset.x, offset.y);
    }, [hoveredId, scale, offset, graphData]);

    // ── Mouse handlers — coords corrected for canvas DPI scaling ─────────────
    const handleMouseMove = useCallback((e) => {
        if (!graphData || !canvasRef.current) return;
        const canvas = canvasRef.current;
        const rect = canvas.getBoundingClientRect();
        // Scale mouse coords from CSS pixels to canvas pixels
        const scaleX = canvas.width  / rect.width;
        const scaleY = canvas.height / rect.height;
        const mx = ((e.clientX - rect.left) * scaleX - offset.x) / scale;
        const my = ((e.clientY - rect.top)  * scaleY - offset.y) / scale;

        if (dragRef.current) {
            setOffset({ x: e.clientX - dragRef.current.sx, y: e.clientY - dragRef.current.sy });
            return;
        }

        let closest = null, minDist = 20;
        graphData.nodes.forEach(n => {
            const p = posRef.current[n.id];
            if (!p) return;
            const d = Math.sqrt((p.x - mx) ** 2 + (p.y - my) ** 2);
            if (d < minDist) { minDist = d; closest = n; }
        });
        setHoveredId(closest?.id || null);
        setTooltip(closest ? { x: e.clientX - rect.left, y: e.clientY - rect.top, node: closest } : null);
    }, [graphData, scale, offset]);

    const handleMouseDown = (e) => { dragRef.current = { sx: e.clientX - offset.x, sy: e.clientY - offset.y }; };
    const handleMouseUp   = () => { dragRef.current = null; };
    const handleWheel     = (e) => { e.preventDefault(); setScale(s => Math.max(0.3, Math.min(3, s - e.deltaY * 0.001))); };

    return (
        <div className="graph-overlay">
            <div className="graph-panel glass-panel">
                <div className="graph-header">
                    <GitFork size={18} />
                    <span>Entity Relationship Graph</span>
                    <span className="graph-meta">
                        {graphData ? `${graphData.nodes.length} nodes · ${graphData.edges.length} edges` : ''}
                    </span>
                    <div className="graph-controls">
                        <button onClick={() => setScale(s => Math.min(3, s + 0.2))} title="Zoom in"><ZoomIn size={15} /></button>
                        <button onClick={() => setScale(s => Math.max(0.3, s - 0.2))} title="Zoom out"><ZoomOut size={15} /></button>
                        <button onClick={() => { setScale(1); setOffset({ x: 0, y: 0 }); }} title="Reset view"><Maximize2 size={15} /></button>
                        <button onClick={onClose} title="Close"><X size={15} /></button>
                    </div>
                </div>

                <div className="graph-canvas-wrap" ref={wrapRef}>
                    {loading && <div className="graph-loading">Building graph...</div>}
                    {error   && <div className="graph-error">Error: {error}</div>}
                    {!loading && !error && graphData?.nodes.length === 0 && (
                        <div className="graph-loading">No graph data — run an investigation first.</div>
                    )}
                    <canvas
                        ref={canvasRef}
                        onMouseMove={handleMouseMove}
                        onMouseDown={handleMouseDown}
                        onMouseUp={handleMouseUp}
                        onMouseLeave={handleMouseUp}
                        onWheel={handleWheel}
                        style={{ cursor: hoveredId ? 'pointer' : 'grab', display: 'block', width: '100%', height: '100%' }}
                    />
                    {tooltip && (
                        <div className="graph-tooltip" style={{ left: tooltip.x + 12, top: tooltip.y - 10 }}>
                            <span className="tooltip-type">{tooltip.node.type}</span>
                            <span className="tooltip-label">{tooltip.node.label}</span>
                        </div>
                    )}
                </div>

                <div className="graph-legend">
                    {[
                        { type: 'query',  color: '#ff4b4b', label: 'Query' },
                        { type: 'source', color: '#64b5f6', label: 'Source' },
                        { type: 'ipv4',   color: '#e57373', label: 'IP' },
                        { type: 'domain', color: '#ba68c8', label: 'Domain' },
                        { type: 'email',  color: '#81c784', label: 'Email' },
                        { type: 'btc',    color: '#fdd835', label: 'Crypto' },
                        { type: 'md5',    color: '#ef9a9a', label: 'Hash' },
                        { type: 'cve',    color: '#ff7043', label: 'CVE' },
                    ].map(l => (
                        <span key={l.type} className="legend-item">
                            <span className="legend-dot" style={{ background: l.color }} />
                            {l.label}
                        </span>
                    ))}
                    <span className="legend-item">
                        <span className="legend-line correlated" /> Correlated
                    </span>
                </div>
            </div>
        </div>
    );
};

export default GraphView;
