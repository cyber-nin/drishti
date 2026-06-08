"""
Drishti Severity Scoring Engine.
Computes a risk-prioritized severity score (0-100) and maps findings to action tiers.
"""
import logging
import re
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class SeverityScorer:
    """Calculates risk severity scores for threat intelligence findings."""

    def __init__(self, weights: Optional[Dict[str, float]] = None):
        # Default weights matching functional requirements
        self.weights = weights or {
            "ioc_reputation": 0.35,
            "keyword_match": 0.25,
            "mitre_ttp": 0.20,
            "source_credibility": 0.10,
            "recency": 0.10
        }
        # Normalize weights to sum to 1.0
        total_weight = sum(self.weights.values())
        if total_weight > 0:
            self.weights = {k: v / total_weight for k, v in self.weights.items()}

    def calculate(
        self,
        artifacts: Dict[str, Any],
        source_metadata: Dict[str, Any],
        summary: str,
        watchlist_keywords: Optional[List[str]] = None,
        mitre_techniques: Optional[List[Dict[str, Any]]] = None,
        enrichment_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Calculate threat severity scoring from 0 to 100.

        Args:
            artifacts: Dict of extracted IOCs {source_url: {type: [values]}}
            source_metadata: Dict with url, credibility_score, timestamp
            summary: Brief text analysis or raw scraped text
            watchlist_keywords: List of target keywords to monitor
            mitre_techniques: List of mapped MITRE ATT&CK techniques
            enrichment_data: Reputation data for extracted IOCs from VT/AbuseIPDB

        Returns:
            Dict containing:
                score: int (0-100)
                tier: str ("CRITICAL" | "HIGH" | "MEDIUM" | "LOW")
                breakdown: dict of subscores
                triggered_keywords: list of matched keywords
                recommended_action: str
        """
        # 1. IOC Reputation Score (35%)
        ioc_score = 0.0
        reps = []
        
        # Extract from enrichment_data if provided
        if enrichment_data:
            for ioc_val, data in enrichment_data.items():
                if not data:
                    continue
                malicious = data.get("malicious", 0)
                suspicious = data.get("suspicious", 0)
                abuse_score = data.get("abuse_score", 0)
                
                # Compute subscore for this reputation profile
                rep_sub = max(malicious * 15.0, suspicious * 5.0, abuse_score)
                reps.append(rep_sub)
        
        # Fallback to counting high-risk IOC types if enrichment is absent
        if not reps and artifacts:
            high_risk_types = {"btc", "xmr", "eth", "session_id", "tox_id", "pgp_key", "aws_key", "api_key", "jwt"}
            found_high_risk = 0
            for url, types in artifacts.items():
                for t, vals in types.items():
                    if t in high_risk_types and vals:
                        found_high_risk += len(vals)
            ioc_score = min(100.0, found_high_risk * 15.0)
        elif reps:
            ioc_score = min(100.0, max(reps))

        # 2. Keyword Match Score (25%)
        keyword_score = 0.0
        triggered_keywords = []
        combined_text = (summary + " " + " ".join(str(v) for v in source_metadata.values() if v is not None)).lower()
        
        if watchlist_keywords:
            for kw in watchlist_keywords:
                kw_clean = kw.strip().lower()
                if not kw_clean:
                    continue
                # Word boundary match to reduce false positives
                pattern = r'\b' + re.escape(kw_clean) + r'\b'
                if re.search(pattern, combined_text) or kw_clean in combined_text:
                    triggered_keywords.append(kw)
            
            # 1 match = 30, 2 matches = 60, 3+ matches = 100
            if triggered_keywords:
                keyword_score = min(100.0, len(triggered_keywords) * 35.0)

        # 3. MITRE ATT&CK TTP Score (20%)
        mitre_score = 0.0
        if mitre_techniques:
            # 1 TTP = 40, 2 TTPs = 80, 3+ TTPs = 100
            mitre_score = min(100.0, len(mitre_techniques) * 40.0)
        elif "ransomware" in combined_text or "lockbit" in combined_text:
            mitre_score = 50.0  # Heuristic fallback for obvious ransomware

        # 4. Source Credibility Score (10%)
        source_score = float(source_metadata.get("credibility_score", 50.0))
        url = source_metadata.get("url", "")
        # Heuristics based on URL
        if ".onion" in url:
            if any(term in url.lower() for term in ["market", "shop", "leak", "forum"]):
                source_score = max(source_score, 90.0)
            else:
                source_score = max(source_score, 70.0)
        elif any(term in url.lower() for term in ["pastebin", "ghostbin", "github"]):
            source_score = max(source_score, 80.0)

        # 5. Recency Score (10%)
        recency_score = 100.0
        timestamp = source_metadata.get("timestamp")
        if timestamp:
            try:
                if isinstance(timestamp, str):
                    dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                elif isinstance(timestamp, datetime):
                    dt = timestamp
                else:
                    dt = None

                if dt:
                    now = datetime.now(dt.tzinfo or timezone.utc)
                    age_hours = (now - dt).total_seconds() / 3600.0
                    if age_hours <= 24:
                        recency_score = 100.0
                    elif age_hours <= 72:
                        recency_score = 80.0
                    elif age_hours <= 168:  # 1 week
                        recency_score = 60.0
                    elif age_hours <= 720:  # 1 month
                        recency_score = 40.0
                    else:
                        recency_score = 20.0
            except Exception as ex:
                logger.warning(f"Error parsing timestamp in severity calculation: {ex}")
                recency_score = 100.0  # Safe fallback default

        # Calculate final weighted score
        final_score_raw = (
            (ioc_score * self.weights["ioc_reputation"]) +
            (keyword_score * self.weights["keyword_match"]) +
            (mitre_score * self.weights["mitre_ttp"]) +
            (source_score * self.weights["source_credibility"]) +
            (recency_score * self.weights["recency"])
        )
        final_score = int(round(final_score_raw))

        # Map to threat tiers
        if final_score >= 80:
            tier = "CRITICAL"
            recommended_action = "IMMEDIATE ESCALATION: Alert duty officer, log evidence seal, and generate FIR complaint draft for Cyber Cell."
        elif final_score >= 60:
            tier = "HIGH"
            recommended_action = "PRIORITY INVESTIGATION: Log detailed findings, enrich all threat actor pseudonyms, and prepare Cert-In advisory."
        elif final_score >= 35:
            tier = "MEDIUM"
            recommended_action = "MONITOR & RECORD: Flag indicators in intelligence logs and check correlation against existing actor profiles."
        else:
            tier = "LOW"
            recommended_action = "ROUTINE REVIEW: Archive scraped content and continue periodic watchlist matching."

        return {
            "score": final_score,
            "tier": tier,
            "breakdown": {
                "ioc_reputation_score": int(round(ioc_score)),
                "keyword_match_score": int(round(keyword_score)),
                "mitre_ttp_score": int(round(mitre_score)),
                "source_credibility_score": int(round(source_score)),
                "recency_score": int(round(recency_score))
            },
            "triggered_keywords": triggered_keywords,
            "recommended_action": recommended_action
        }
