"""
IOC Reputation Enrichment module.
Queries VirusTotal and AbuseIPDB for reputation data on extracted artifacts.
"""
import logging
import requests
from typing import Dict, Any

try:
    from backend.config import VIRUSTOTAL_API_KEY, ABUSEIPDB_API_KEY
except ModuleNotFoundError:
    from config import VIRUSTOTAL_API_KEY, ABUSEIPDB_API_KEY

logger = logging.getLogger(__name__)

_ENRICH_TIMEOUT = 10


def _vt_ip(ip: str) -> Dict[str, Any]:
    if not VIRUSTOTAL_API_KEY:
        return {}
    try:
        r = requests.get(
            f"https://www.virustotal.com/api/v3/ip_addresses/{ip}",
            headers={"x-apikey": VIRUSTOTAL_API_KEY},
            timeout=_ENRICH_TIMEOUT,
        )
        if r.status_code == 200:
            stats = r.json().get("data", {}).get("attributes", {}).get("last_analysis_stats", {})
            return {"malicious": stats.get("malicious", 0), "suspicious": stats.get("suspicious", 0), "source": "virustotal"}
    except Exception as e:
        logger.debug(f"VT IP lookup failed for {ip}: {e}")
    return {}


def _vt_domain(domain: str) -> Dict[str, Any]:
    if not VIRUSTOTAL_API_KEY:
        return {}
    try:
        r = requests.get(
            f"https://www.virustotal.com/api/v3/domains/{domain}",
            headers={"x-apikey": VIRUSTOTAL_API_KEY},
            timeout=_ENRICH_TIMEOUT,
        )
        if r.status_code == 200:
            stats = r.json().get("data", {}).get("attributes", {}).get("last_analysis_stats", {})
            return {"malicious": stats.get("malicious", 0), "suspicious": stats.get("suspicious", 0), "source": "virustotal"}
    except Exception as e:
        logger.debug(f"VT domain lookup failed for {domain}: {e}")
    return {}


def _vt_hash(hash_val: str) -> Dict[str, Any]:
    if not VIRUSTOTAL_API_KEY:
        return {}
    try:
        r = requests.get(
            f"https://www.virustotal.com/api/v3/files/{hash_val}",
            headers={"x-apikey": VIRUSTOTAL_API_KEY},
            timeout=_ENRICH_TIMEOUT,
        )
        if r.status_code == 200:
            stats = r.json().get("data", {}).get("attributes", {}).get("last_analysis_stats", {})
            return {"malicious": stats.get("malicious", 0), "suspicious": stats.get("suspicious", 0), "source": "virustotal"}
    except Exception as e:
        logger.debug(f"VT hash lookup failed for {hash_val}: {e}")
    return {}


def _abuseipdb(ip: str) -> Dict[str, Any]:
    if not ABUSEIPDB_API_KEY:
        return {}
    try:
        r = requests.get(
            "https://api.abuseipdb.com/api/v2/check",
            headers={"Key": ABUSEIPDB_API_KEY, "Accept": "application/json"},
            params={"ipAddress": ip, "maxAgeInDays": 90},
            timeout=_ENRICH_TIMEOUT,
        )
        if r.status_code == 200:
            data = r.json().get("data", {})
            return {
                "abuse_score": data.get("abuseConfidenceScore", 0),
                "total_reports": data.get("totalReports", 0),
                "country": data.get("countryCode", ""),
                "source": "abuseipdb",
            }
    except Exception as e:
        logger.debug(f"AbuseIPDB lookup failed for {ip}: {e}")
    return {}


def enrich_artifacts(artifacts: Dict[str, Dict[str, set]]) -> Dict[str, Dict[str, Dict[str, Any]]]:
    """
    Enrich extracted artifacts with reputation data.

    Args:
        artifacts: {url: {artifact_type: {values}}}

    Returns:
        {url: {artifact_type: {value: reputation_dict}}}
    """
    enriched = {}

    for url, art_by_type in artifacts.items():
        enriched[url] = {}
        for artifact_type, values in art_by_type.items():
            enriched[url][artifact_type] = {}
            for value in list(values)[:5]:  # limit to 5 per type to avoid rate limits
                rep = {}
                if artifact_type == "ipv4":
                    rep = _vt_ip(value)
                    abuse = _abuseipdb(value)
                    if abuse:
                        rep.update(abuse)
                elif artifact_type == "domain":
                    rep = _vt_domain(value)
                elif artifact_type in ("md5", "sha1", "sha256"):
                    rep = _vt_hash(value)

                if rep:
                    enriched[url][artifact_type][value] = rep

    return enriched


def format_enrichment(enriched: Dict[str, Dict[str, Dict[str, Any]]]) -> str:
    """Format enrichment results as a markdown section."""
    lines = ["## IOC Reputation Enrichment", ""]
    found_any = False

    for url, art_by_type in enriched.items():
        for artifact_type, value_reps in art_by_type.items():
            for value, rep in value_reps.items():
                if not rep:
                    continue
                found_any = True
                malicious = rep.get("malicious", 0)
                suspicious = rep.get("suspicious", 0)
                abuse_score = rep.get("abuse_score")
                country = rep.get("country", "")

                flags = []
                if malicious:
                    flags.append(f"🔴 {malicious} malicious detections")
                if suspicious:
                    flags.append(f"🟡 {suspicious} suspicious detections")
                if abuse_score is not None:
                    flags.append(f"abuse score: {abuse_score}%")
                if country:
                    flags.append(f"country: {country}")

                if flags:
                    lines.append(f"- `{value}` ({artifact_type}): {', '.join(flags)}")

    if not found_any:
        lines.append("No reputation data available (check API keys in .env).")

    return "\n".join(lines)
