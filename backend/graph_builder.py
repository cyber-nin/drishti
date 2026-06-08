"""
Entity Relationship Graph builder.
Builds a NetworkX graph from extracted artifacts linking:
  - Query node → Source URL nodes → Artifact nodes
  - Shared artifacts across sources get cross-edges (correlation)
"""
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

try:
    import networkx as nx
    _NX_AVAILABLE = True
except ImportError:
    _NX_AVAILABLE = False
    logger.warning("networkx not installed — graph features disabled. Run: pip install networkx")

# Artifact types to include as graph nodes (skip noisy ones)
_GRAPH_TYPES = {'email', 'ipv4', 'domain', 'onion', 'btc', 'eth', 'xmr', 'ltc',
                'telegram', 'md5', 'sha1', 'sha256', 'cve', 'aws_key', 'jwt',
                'pgp_key', 'xmpp', 'tox_id', 'session_id', 'technique'}

# Color map for node types (used by frontend renderer)
NODE_COLORS = {
    'query':      '#ff4b4b',
    'source':     '#64b5f6',
    'email':      '#81c784',
    'ipv4':       '#e57373',
    'domain':     '#ba68c8',
    'onion':      '#ff8a65',
    'btc':        '#fdd835',
    'eth':        '#fdd835',
    'xmr':        '#fdd835',
    'ltc':        '#fdd835',
    'telegram':   '#29b6f6',
    'md5':        '#ef9a9a',
    'sha1':       '#ef9a9a',
    'sha256':     '#ef9a9a',
    'cve':        '#ff7043',
    'aws_key':    '#ff4b4b',
    'jwt':        '#ff4b4b',
    'pgp_key':    '#ffb74d',
    'xmpp':       '#81c784',
    'tox_id':     '#4db6ac',
    'session_id': '#7986cb',
    'technique':  '#ab47bc',
    'default':    '#90a4ae',
}


def build_graph(query: str, artifacts: Dict[str, Dict[str, Any]]) -> dict:
    """
    Build entity relationship graph from artifacts.

    Args:
        query:     The original investigation query string
        artifacts: {source_url: {artifact_type: set/list of values}}

    Returns:
        {"nodes": [...], "edges": [...]} serializable dict
    """
    if not _NX_AVAILABLE:
        return {"nodes": [], "edges": [], "error": "networkx not installed"}

    G = nx.Graph()

    # Central query node
    query_id = f"query::{query}"
    G.add_node(query_id, label=query[:40], type='query', color=NODE_COLORS['query'])

    # Track artifact → [source_urls] for cross-source correlation
    artifact_sources: Dict[str, list] = {}

    for source_url, art_by_type in artifacts.items():
        if not art_by_type:
            continue

        # Source node
        source_id = f"source::{source_url}"
        short_label = source_url.replace('http://', '').replace('https://', '')[:35]
        G.add_node(source_id, label=short_label, type='source', color=NODE_COLORS['source'])
        G.add_edge(query_id, source_id, relation='searched')

        for artifact_type, values in art_by_type.items():
            if artifact_type not in _GRAPH_TYPES:
                continue
            if not values:
                continue

            val_list = list(values) if not isinstance(values, list) else values

            for value in val_list[:15]:  # cap per type per source
                value = str(value).strip()
                if not value:
                    continue

                artifact_id = f"{artifact_type}::{value}"
                if artifact_id not in G:
                    G.add_node(
                        artifact_id,
                        label=value[:40],
                        type=artifact_type,
                        color=NODE_COLORS.get(artifact_type, NODE_COLORS['default'])
                    )

                G.add_edge(source_id, artifact_id, relation='contains')

                # Track for cross-source edges
                if artifact_id not in artifact_sources:
                    artifact_sources[artifact_id] = []
                artifact_sources[artifact_id].append(source_id)

    # Add cross-source correlation edges for shared artifacts
    for artifact_id, sources in artifact_sources.items():
        if len(sources) > 1:
            for i in range(len(sources)):
                for j in range(i + 1, len(sources)):
                    if not G.has_edge(sources[i], sources[j]):
                        G.add_edge(sources[i], sources[j], relation='correlated')

    # Map MITRE techniques from query & artifacts
    try:
        from backend.mitre_mapper import extract_mitre_techniques
    except ModuleNotFoundError:
        from mitre_mapper import extract_mitre_techniques

    techniques = extract_mitre_techniques(query)
    
    flat_values = []
    for source_url, art_by_type in artifacts.items():
        for artifact_type, values in art_by_type.items():
            flat_values.extend(list(values))
            
    if flat_values:
        flat_text = " ".join(str(v) for v in flat_values)
        techniques.extend(extract_mitre_techniques(flat_text))
        
    unique_techs = {}
    for tech in techniques:
        unique_techs[tech["id"]] = tech
        
    for tid, tech in unique_techs.items():
        tech_node_id = f"technique::{tid}"
        if tech_node_id not in G:
            G.add_node(
                tech_node_id,
                label=f"{tid}: {tech['name']}",
                type='technique',
                color=NODE_COLORS['technique']
            )
            G.add_edge(query_id, tech_node_id, relation='associated_ttp')

    return _serialize(G)


def _serialize(G) -> dict:
    """Convert NetworkX graph to JSON-serializable nodes/edges."""
    nodes = []
    for node_id, data in G.nodes(data=True):
        nodes.append({
            'id':    node_id,
            'label': data.get('label', node_id[:30]),
            'type':  data.get('type', 'default'),
            'color': data.get('color', NODE_COLORS['default']),
        })

    edges = []
    for u, v, data in G.edges(data=True):
        edges.append({
            'source':   u,
            'target':   v,
            'relation': data.get('relation', ''),
        })

    return {'nodes': nodes, 'edges': edges}
