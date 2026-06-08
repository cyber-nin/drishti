"""
Export module for DRISHTI investigation reports.
Supports HTML, STIX2, CSV, JSON, and Markdown formats.
"""
import csv
import json
import logging
import io
import re
from datetime import datetime, timezone
from typing import Dict, Any

logger = logging.getLogger(__name__)


def _build_ioc_rows(artifacts: Dict[str, Dict[str, set]]) -> list:
    """Flatten artifacts into a list of dicts for tabular export."""
    rows = []
    for source_url, art_by_type in artifacts.items():
        for artifact_type, values in art_by_type.items():
            for value in values:
                rows.append({
                    "source": source_url,
                    "type": artifact_type,
                    "value": value,
                    "extracted_at": datetime.now(timezone.utc).isoformat(),
                })
    return rows


def _md_to_html_body(md: str) -> str:
    """Minimal Markdown → HTML converter (no external deps)."""
    lines = md.split('\n')
    html = []
    in_ul = False

    for line in lines:
        # Headings
        if line.startswith('### '):
            if in_ul: html.append('</ul>'); in_ul = False
            html.append(f'<h3>{line[4:]}</h3>')
        elif line.startswith('## '):
            if in_ul: html.append('</ul>'); in_ul = False
            html.append(f'<h2>{line[3:]}</h2>')
        elif line.startswith('# '):
            if in_ul: html.append('</ul>'); in_ul = False
            html.append(f'<h1>{line[2:]}</h1>')
        # List items
        elif line.startswith('- '):
            if not in_ul: html.append('<ul>'); in_ul = True
            content = line[2:]
            # bold
            content = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', content)
            html.append(f'<li>{content}</li>')
        # Blank line
        elif line.strip() == '':
            if in_ul: html.append('</ul>'); in_ul = False
            html.append('<br>')
        # Normal paragraph
        else:
            if in_ul: html.append('</ul>'); in_ul = False
            content = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', line)
            html.append(f'<p>{content}</p>')

    if in_ul:
        html.append('</ul>')
    return '\n'.join(html)


def to_html(query: str, summary: str, artifacts: Dict[str, Dict[str, set]]) -> str:
    """Export investigation as a self-contained styled HTML report."""
    now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
    body = _md_to_html_body(summary)

    # Build artifacts table if provided
    artifact_table = ''
    rows = _build_ioc_rows(artifacts)
    if rows:
        artifact_table = '''
        <h2>Extracted IOCs</h2>
        <table>
            <thead><tr><th>Type</th><th>Value</th><th>Source</th></tr></thead>
            <tbody>
        '''
        for r in rows:
            artifact_table += f"<tr><td><span class='badge'>{r['type']}</span></td><td><code>{r['value']}</code></td><td class='source'>{r['source']}</td></tr>\n"
        artifact_table += '</tbody></table>'

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>DRISHTI Report — {query}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #0d0d0d; color: #e0e0e0; padding: 2rem; }}
  .report-wrapper {{ max-width: 960px; margin: 0 auto; }}
  header {{ border-bottom: 2px solid #ff4b4b; padding-bottom: 1.5rem; margin-bottom: 2rem; }}
  header h1 {{ font-size: 2rem; color: #ff4b4b; letter-spacing: 0.1em; }}
  header .meta {{ font-size: 0.85rem; color: #888; margin-top: 0.5rem; }}
  header .query-box {{ margin-top: 1rem; background: #1a1a1a; border-left: 3px solid #ff4b4b;
    padding: 0.6rem 1rem; font-size: 0.95rem; color: #ccc; border-radius: 0 4px 4px 0; }}
  h1 {{ font-size: 1.6rem; color: #ff4b4b; margin: 1.5rem 0 0.5rem; }}
  h2 {{ font-size: 1.25rem; color: #ff8a65; border-bottom: 1px solid #2a2a2a;
    padding-bottom: 0.4rem; margin: 1.5rem 0 0.75rem; }}
  h3 {{ font-size: 1rem; color: #fdd835; margin: 1rem 0 0.4rem; }}
  p {{ line-height: 1.7; color: #ccc; margin-bottom: 0.5rem; }}
  ul {{ padding-left: 1.5rem; margin-bottom: 0.75rem; }}
  li {{ line-height: 1.8; color: #bbb; }}
  code {{ background: #1e1e1e; padding: 2px 6px; border-radius: 3px;
    font-family: 'Consolas', monospace; font-size: 0.85rem; color: #a9b7c6; word-break: break-all; }}
  table {{ width: 100%; border-collapse: collapse; margin-top: 1rem; font-size: 0.85rem; }}
  th {{ background: #1a1a1a; color: #ff4b4b; padding: 0.6rem 0.8rem; text-align: left;
    border-bottom: 2px solid #ff4b4b; }}
  td {{ padding: 0.5rem 0.8rem; border-bottom: 1px solid #1e1e1e; vertical-align: top; }}
  tr:hover td {{ background: #161616; }}
  .badge {{ background: rgba(255,75,75,0.15); color: #ff8a65; border: 1px solid rgba(255,75,75,0.3);
    padding: 2px 8px; border-radius: 10px; font-size: 0.75rem; white-space: nowrap; }}
  .source {{ color: #666; font-size: 0.78rem; word-break: break-all; }}
  footer {{ margin-top: 3rem; padding-top: 1rem; border-top: 1px solid #1e1e1e;
    font-size: 0.75rem; color: #555; text-align: center; }}
  @media print {{
    body {{ background: #fff; color: #000; }}
    header h1, h1, h2 {{ color: #c00; }}
    h3 {{ color: #333; }}
    code {{ background: #f4f4f4; color: #333; }}
    .badge {{ background: #fee; color: #c00; border-color: #c00; }}
    table {{ font-size: 0.8rem; }}
  }}
</style>
</head>
<body>
<div class="report-wrapper">
  <header>
    <h1>&#x1F6E1; DRISHTI Intelligence Report</h1>
    <div class="meta">Generated: {now} &nbsp;|&nbsp; Classification: LAW ENFORCEMENT SENSITIVE</div>
    <div class="query-box"><strong>Query:</strong> {query}</div>
  </header>

  <div class="report-body">
    {body}
  </div>

  {artifact_table}

  <footer>Generated by DRISHTI Dark Web OSINT Platform &mdash; {now}</footer>
</div>
</body>
</html>'''


def to_csv(query: str, artifacts: Dict[str, Dict[str, set]]) -> str:
    """Export artifacts as CSV string."""
    rows = _build_ioc_rows(artifacts)
    if not rows:
        return "source,type,value,extracted_at\n"
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["source", "type", "value", "extracted_at"])
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def to_json(query: str, summary: str, artifacts: Dict[str, Dict[str, set]]) -> str:
    """Export full investigation as structured JSON."""
    return json.dumps({
        "query": query,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": summary,
        "artifacts": {
            url: {atype: list(vals) for atype, vals in art.items()}
            for url, art in artifacts.items()
        },
    }, indent=2)


def to_stix2(query: str, artifacts: Dict[str, Dict[str, set]]) -> str:
    """
    Export artifacts as a STIX2 bundle (JSON).
    Produces Indicator and ObservedData objects for supported IOC types.
    """
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    # STIX2 type mapping
    stix_type_map = {
        "ipv4":   ("ipv4-addr", "value"),
        "domain": ("domain-name", "value"),
        "email":  ("email-addr", "value"),
        "url":    ("url", "value"),
        "md5":    ("file", "hashes.MD5"),
        "sha1":   ("file", "hashes.SHA-1"),
        "sha256": ("file", "hashes.SHA-256"),
        "btc":    ("cryptocurrency-wallet", "address"),
        "eth":    ("cryptocurrency-wallet", "address"),
        "xmr":    ("cryptocurrency-wallet", "address"),
        "ltc":    ("cryptocurrency-wallet", "address"),
        "xmpp":   ("user-account", "user_id"),
        "tox_id": ("user-account", "user_id"),
        "session_id": ("user-account", "user_id"),
        "pgp_key": ("user-account", "credential"),
    }

    objects = []
    seen = set()

    # Map MITRE techniques to create attack-pattern objects
    try:
        from backend.mitre_mapper import extract_mitre_techniques
    except ModuleNotFoundError:
        from mitre_mapper import extract_mitre_techniques

    flat_text = query + " " + " ".join(
        str(v) for art in artifacts.values() for values in art.values() for v in values
    )
    techniques = extract_mitre_techniques(flat_text)
    
    attack_pattern_ids = []
    unique_techs = {t["id"]: t for t in techniques}
    
    for tid, tech in unique_techs.items():
        ap_id = f"attack-pattern--{_deterministic_uuid('ap:' + tid)}"
        attack_pattern_ids.append(ap_id)
        objects.append({
            "type": "attack-pattern",
            "spec_version": "2.1",
            "id": ap_id,
            "created": now,
            "modified": now,
            "name": tech["name"],
            "description": tech.get("description", ""),
            "external_references": [
                {
                    "source_name": "mitre-attack",
                    "external_id": tid,
                    "url": f"https://attack.mitre.org/techniques/{tid}"
                }
            ]
        })

    for source_url, art_by_type in artifacts.items():
        for artifact_type, values in art_by_type.items():
            if artifact_type not in stix_type_map:
                continue
            stix_obj_type, stix_field = stix_type_map[artifact_type]

            for value in values:
                dedup_key = f"{artifact_type}:{value}"
                if dedup_key in seen:
                    continue
                seen.add(dedup_key)

                obj_id = f"{stix_obj_type}--{_deterministic_uuid(dedup_key)}"

                # Build SCO (STIX Cyber Observable)
                if stix_obj_type == "file":
                    hash_key = stix_field.split(".")[1]  # e.g. "MD5"
                    sco = {"type": "file", "id": obj_id, "hashes": {hash_key: value}}
                else:
                    sco = {"type": stix_obj_type, "id": obj_id, stix_field: value}

                objects.append(sco)

                # Wrap in an Indicator
                indicator_id = f"indicator--{_deterministic_uuid('ind:' + dedup_key)}"
                objects.append({
                    "type": "indicator",
                    "spec_version": "2.1",
                    "id": indicator_id,
                    "created": now,
                    "modified": now,
                    "name": f"{artifact_type}: {value[:60]}",
                    "description": f"Extracted from {source_url} during DRISHTI investigation: {query}",
                    "pattern": f"[{stix_obj_type}:{stix_field} = '{value}']",
                    "pattern_type": "stix",
                    "valid_from": now,
                    "indicator_types": ["malicious-activity"],
                })

                # Link this indicator to all generated attack patterns
                for ap_id in attack_pattern_ids:
                    rel_id = f"relationship--{_deterministic_uuid('rel:' + indicator_id + ap_id)}"
                    objects.append({
                        "type": "relationship",
                        "spec_version": "2.1",
                        "id": rel_id,
                        "created": now,
                        "modified": now,
                        "source_ref": indicator_id,
                        "target_ref": ap_id,
                        "relationship_type": "indicates",
                    })

    bundle = {
        "type": "bundle",
        "id": f"bundle--{_deterministic_uuid(query + now)}",
        "objects": objects,
    }
    return json.dumps(bundle, indent=2)


def _deterministic_uuid(seed: str) -> str:
    """Generate a deterministic UUID v5-like hex string from a seed."""
    import hashlib
    h = hashlib.sha1(seed.encode()).hexdigest()
    return f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:32]}"


def export_report(fmt: str, query: str, summary: str, artifacts: Dict[str, Dict[str, set]]) -> tuple[str, str]:
    """
    Export investigation report in the requested format.

    Returns:
        (content_string, mime_type)
    """
    fmt = fmt.lower()
    if fmt == "csv":
        return to_csv(query, artifacts), "text/csv"
    elif fmt == "json":
        return to_json(query, summary, artifacts), "application/json"
    elif fmt == "stix2":
        return to_stix2(query, artifacts), "application/json"
    elif fmt == "html":
        return to_html(query, summary, artifacts), "text/html"
    else:
        return summary, "text/markdown"
