"""
Drishti Dashboard Trend Analyzer.
Aggregates scraped OSINT metadata to compute trending topics, source domain risk ranks, and timelines.
"""
import sqlite3
import os
import re
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional

try:
    from backend.config import DATABASE_URL
except ModuleNotFoundError:
    try:
        from config import DATABASE_URL
    except ModuleNotFoundError:
        DATABASE_URL = None

logger = logging.getLogger(__name__)

class TrendAnalyzer:
    """Analyzes historical dark web data to provide trending, ranking, and activity timelines."""

    # Predefined taxonomy for Indian Law Enforcement monitoring target areas
    TAXONOMY = {
        "drugs": ["fentanyl", "cocaine", "meth", "heroin", "mdma", "weed", "cannabis", "opiates", "pill", "lsd"],
        "weapons": ["firearms", "explosives", "ammo", "glock", "pistol", "rifle", "grenade", "silencer"],
        "documents": ["passport", "id card", "driver license", "carding", "aadhaar", "pan card", "fake passport"],
        "financial": ["credit card dump", "bank logs", "fullz", "carding", "paypal", "cvv", "cloned card"],
        "malware": ["ransomware", "rat", "stealer", "botnet", "crypter", "exploits", "payload", "rootkit"],
        "data_breaches": ["database dump", "combo list", "leaked", "sql injection", "hacked database", "breached"]
    }

    def __init__(self, db_path: Optional[str] = None):
        if db_path:
            self.db_path = db_path
        elif DATABASE_URL and DATABASE_URL.startswith("sqlite:///"):
            self.db_path = DATABASE_URL.replace("sqlite:///", "")
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            self.db_path = os.path.join(base_dir, "data", "drishti.db")

        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Ensure scraped content persistence table exists."""
        try:
            with self._get_connection() as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS scraped_content (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        url TEXT UNIQUE NOT NULL,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        raw_text TEXT,
                        word_count INTEGER,
                        ioc_count INTEGER,
                        severity_score INTEGER DEFAULT 0,
                        language TEXT DEFAULT 'en'
                    )
                """)
                conn.commit()
            logger.info("Scraped Content metadata DB table initialized.")
        except Exception as e:
            logger.error(f"Failed to initialize Trend Analyzer DB: {e}")

    def ingest_metadata(
        self,
        url: str,
        raw_text: str,
        ioc_count: int,
        severity_score: int,
        language: str = "en"
    ) -> bool:
        """Store or update metadata for scraped dark web pages to run trends on."""
        if not url:
            return False
        word_count = len(raw_text.split()) if raw_text else 0
        time_str = datetime.now(timezone.utc).isoformat()
        
        try:
            with self._get_connection() as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO scraped_content (url, timestamp, raw_text, word_count, ioc_count, severity_score, language)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (url, time_str, raw_text, word_count, ioc_count, severity_score, language))
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error ingesting content metadata for {url}: {e}")
            return False

    def get_trending_topics(self, last_n_hours: int = 168, top_k: int = 5) -> Dict[str, Any]:
        """Calculate taxonomy category weights and key trending terms based on term frequencies."""
        cutoff_time = (datetime.now(timezone.utc) - timedelta(hours=last_n_hours)).isoformat()
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT raw_text FROM scraped_content WHERE timestamp >= ?",
                    (cutoff_time,)
                )
                rows = cursor.fetchall()
                
            # Initialize metrics
            category_scores = {cat: 0 for cat in self.TAXONOMY.keys()}
            term_frequencies = {}

            # Count matches
            for row in rows:
                text = (row["raw_text"] or "").lower()
                for cat, terms in self.TAXONOMY.items():
                    for term in terms:
                        pattern = r'\b' + re.escape(term) + r'\b'
                        matches = len(re.findall(pattern, text))
                        if matches > 0:
                            category_scores[cat] += matches
                            term_frequencies[term] = term_frequencies.get(term, 0) + matches

            # Sort keywords by frequency
            sorted_terms = sorted(term_frequencies.items(), key=lambda x: x[1], reverse=True)
            top_keywords = [{"keyword": k, "frequency": v} for k, v in sorted_terms[:top_k]]

            return {
                "timeframe_hours": last_n_hours,
                "categories": category_scores,
                "top_keywords": top_keywords
            }
        except Exception as e:
            logger.error(f"Error analyzing trends: {e}")
            return {"categories": {}, "top_keywords": []}

    def get_source_rankings(self, top_k: int = 10) -> List[Dict[str, Any]]:
        """Group and rank .onion sources based on severity, frequency, and density factors."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT url, ioc_count, severity_score FROM scraped_content")
                rows = cursor.fetchall()

            # Group metrics by base domain
            import urllib.parse
            domain_stats = {}

            for row in rows:
                url = row["url"]
                ioc_cnt = row["ioc_count"] or 0
                sev = row["severity_score"] or 0

                parsed = urllib.parse.urlparse(url)
                domain = parsed.netloc or url
                if not domain:
                    continue

                if domain not in domain_stats:
                    domain_stats[domain] = {
                        "domain": domain,
                        "finding_frequency": 0,
                        "total_iocs": 0,
                        "severity_scores": []
                    }
                
                stats = domain_stats[domain]
                stats["finding_frequency"] += 1
                stats["total_iocs"] += ioc_cnt
                stats["severity_scores"].append(sev)

            # Compile averages and rank
            rankings = []
            for domain, stats in domain_stats.items():
                avg_sev = sum(stats["severity_scores"]) / len(stats["severity_scores"])
                rankings.append({
                    "domain": domain,
                    "finding_frequency": stats["finding_frequency"],
                    "ioc_count": stats["total_iocs"],
                    "avg_severity_score": round(avg_sev, 1)
                })

            # Rank by frequency * average severity score descending
            rankings = sorted(rankings, key=lambda x: x["finding_frequency"] * x["avg_severity_score"], reverse=True)
            return rankings[:top_k]

        except Exception as e:
            logger.error(f"Error ranking sources: {e}")
            return []

    def get_activity_timeline(self, granularity: str = "daily") -> List[Dict[str, Any]]:
        """Return investigation history aggregated by day/hour with severity tier distributions."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                # Group format based on granularity
                if granularity.lower() == "hourly":
                    sql_group = "strftime('%Y-%m-%d %H:00', timestamp)"
                else:
                    sql_group = "date(timestamp)"

                cursor.execute(f"""
                    SELECT {sql_group} as time_slot,
                           count(id) as total_scans,
                           sum(case when severity_score >= 80 then 1 else 0 end) as critical_count,
                           sum(case when severity_score >= 60 and severity_score < 80 then 1 else 0 end) as high_count,
                           sum(case when severity_score >= 35 and severity_score < 60 then 1 else 0 end) as medium_count,
                           sum(case when severity_score < 35 then 1 else 0 end) as low_count
                    FROM scraped_content
                    GROUP BY time_slot
                    ORDER BY time_slot ASC
                """)
                
                timeline = []
                for row in cursor.fetchall():
                    timeline.append({
                        "time_slot": row["time_slot"],
                        "total_scans": row["total_scans"],
                        "distribution": {
                            "CRITICAL": row["critical_count"],
                            "HIGH": row["high_count"],
                            "MEDIUM": row["medium_count"],
                            "LOW": row["low_count"]
                        }
                    })
                return timeline
        except Exception as e:
            logger.error(f"Error building activity timeline: {e}")
            return []
