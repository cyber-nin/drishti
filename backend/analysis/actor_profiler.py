"""
Drishti Threat Actor Profiler.
Ingests intelligence, tracks handles, correlates identities, and profiles threat actors.
"""
import os
import sqlite3
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

try:
    from backend.config import DATABASE_URL
    from backend.mitre_mapper import map_text_heuristically
except ModuleNotFoundError:
    try:
        from config import DATABASE_URL
        from mitre_mapper import map_text_heuristically
    except ModuleNotFoundError:
        DATABASE_URL = None
        map_text_heuristically = lambda x: []

logger = logging.getLogger(__name__)

class ActorProfiler:
    """Ingests threat findings to construct and correlate digital footprints of actors."""

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
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def _init_db(self):
        """Ensure threat profiling tables exist in SQLite."""
        try:
            with self._get_connection() as conn:
                # Profiles table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS actor_profiles (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        primary_handle TEXT NOT NULL UNIQUE,
                        aliases TEXT, -- JSON list of pseudonyms
                        description TEXT,
                        writing_style TEXT, -- JSON dict of attributes
                        ttp_tags TEXT, -- JSON list of MITRE IDs
                        threat_level INTEGER DEFAULT 50,
                        first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                # Artifacts table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS actor_artifacts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        actor_id INTEGER NOT NULL,
                        source_url TEXT,
                        artifact_type TEXT NOT NULL, -- btc, email, telegram, xmpp, etc.
                        artifact_value TEXT NOT NULL,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (actor_id) REFERENCES actor_profiles(id) ON DELETE CASCADE,
                        UNIQUE(actor_id, artifact_type, artifact_value, source_url)
                    )
                """)
                conn.commit()
            logger.info("Threat Actor Profiler DB initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize Actor Profiler DB: {e}")

    def ingest_finding(
        self,
        source_url: str,
        artifacts: Dict[str, List[str]],
        raw_text: str,
        timestamp: Optional[str] = None
    ) -> int:
        """
        Analyze extracted artifacts and text to auto-create or update actor profiles.

        Returns:
            The primary actor_id associated with this ingest run, or -1 if none found.
        """
        time_str = timestamp or datetime.now(timezone.utc).isoformat()
        
        # 1. Identify handles to group profile
        handles = []
        if "telegram" in artifacts:
            handles.extend(artifacts["telegram"])
        if "xmpp" in artifacts:
            handles.extend(artifacts["xmpp"])
        if "email" in artifacts:
            handles.extend(artifacts["email"])
        
        if not handles:
            logger.debug(f"No threat actor handles found in artifacts for {source_url}. Skipping profile ingest.")
            return -1

        # Use the first handle as primary handle
        primary_handle = handles[0]
        aliases = list(set(handles))

        # Calculate basic writing style heuristics
        words = raw_text.split()
        sentences = [s.strip() for s in raw_text.split('.') if s.strip()]
        avg_sentence_len = len(words) / max(1, len(sentences))
        
        common_phrases_list = ["contact me", "pm me", "price", "escrow", "leak", "hacked"]
        common_phrases_found = [p for p in common_phrases_list if p in raw_text.lower()]
        
        writing_style = {
            "avg_sentence_length": int(round(avg_sentence_len)),
            "common_phrases": common_phrases_found,
            "language_patterns": ["English"]
        }

        # Calculate inferred MITRE TTPs
        ttps = map_text_heuristically(raw_text)
        ttp_ids = list({t["id"] for t in ttps})

        # Calculate heuristic threat level
        threat_level = min(100, 30 + len(ttp_ids) * 15 + len(artifacts.keys()) * 10)

        # 2. Persist to SQLite
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Check if profile already exists
                cursor.execute("SELECT id, aliases, ttp_tags, writing_style FROM actor_profiles WHERE primary_handle = ?", (primary_handle,))
                existing = cursor.fetchone()
                
                if existing:
                    actor_id = existing["id"]
                    # Merge aliases
                    exist_aliases = json.loads(existing["aliases"] or "[]")
                    new_aliases = list(set(exist_aliases + aliases))
                    
                    # Merge TTPs
                    exist_ttps = json.loads(existing["ttp_tags"] or "[]")
                    new_ttps = list(set(exist_ttps + ttp_ids))
                    
                    cursor.execute("""
                        UPDATE actor_profiles 
                        SET aliases = ?, ttp_tags = ?, last_seen = ?
                        WHERE id = ?
                    """, (json.dumps(new_aliases), json.dumps(new_ttps), time_str, actor_id))
                else:
                    cursor.execute("""
                        INSERT INTO actor_profiles (primary_handle, aliases, description, writing_style, ttp_tags, threat_level, first_seen, last_seen)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        primary_handle,
                        json.dumps(aliases),
                        f"Auto-generated profile for handle {primary_handle}",
                        json.dumps(writing_style),
                        json.dumps(ttp_ids),
                        threat_level,
                        time_str,
                        time_str
                    ))
                    actor_id = cursor.lastrowid

                # Ingest other IOC artifacts
                for art_type, vals in artifacts.items():
                    # We exclude handles that we used for indexing
                    if art_type in ("telegram", "xmpp"):
                        continue
                    for val in vals:
                        cursor.execute("""
                            INSERT OR IGNORE INTO actor_artifacts (actor_id, source_url, artifact_type, artifact_value, timestamp)
                            VALUES (?, ?, ?, ?, ?)
                        """, (actor_id, source_url, art_type, val, time_str))

                conn.commit()
                logger.info(f"Ingested findings for threat actor '{primary_handle}' (ID: {actor_id}).")
                return actor_id

        except Exception as e:
            logger.error(f"Error ingesting threat actor finding: {e}", exc_info=True)
            return -1

    def build_profile(self, actor_id: int) -> Optional[Dict[str, Any]]:
        """Query SQLite and compile the complete, structured threat actor footprint."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM actor_profiles WHERE id = ?", (actor_id,))
                prof_row = cursor.fetchone()
                if not prof_row:
                    return None
                
                profile = dict(prof_row)
                
                # Fetch all linked artifacts
                cursor.execute("SELECT * FROM actor_artifacts WHERE actor_id = ? ORDER BY timestamp DESC", (actor_id,))
                art_rows = cursor.fetchall()
                
                # Format variables
                profile["linked_pseudonyms"] = json.loads(profile["aliases"] or "[]")
                profile["writing_style"] = json.loads(profile["writing_style"] or "{}")
                profile["ttp_tags"] = json.loads(profile["ttp_tags"] or "[]")
                
                linked_iocs = {}
                transaction_trail = []
                platform_presence = []
                timeline = []
                
                # Timeline event from profile registration
                timeline.append({
                    "timestamp": profile["first_seen"],
                    "event": "Profile created",
                    "details": "First identified handle in Drishti intelligence scans."
                })

                for row in art_rows:
                    art_type = row["artifact_type"]
                    art_val = row["artifact_value"]
                    src_url = row["source_url"]
                    t_str = row["timestamp"]
                    
                    # Group IOCs
                    if art_type not in linked_iocs:
                        linked_iocs[art_type] = []
                    if art_val not in linked_iocs[art_type]:
                        linked_iocs[art_type].append(art_val)
                        
                    # Transaction trail (crypto wallets)
                    if art_type in ("btc", "xmr", "eth", "ltc"):
                        transaction_trail.append({
                            "address": art_val,
                            "currency": art_type.upper(),
                            "first_seen": t_str,
                            "last_seen": t_str
                        })
                        
                    # Footprints / Platform presence
                    import urllib.parse
                    parsed = urllib.parse.urlparse(src_url)
                    domain = parsed.netloc or src_url
                    
                    presence_match = next((p for p in platform_presence if p["url"] == src_url), None)
                    if not presence_match:
                        platform_presence.append({
                            "platform": domain,
                            "url": src_url,
                            "first_seen": t_str,
                            "last_seen": t_str
                        })
                    
                    timeline.append({
                        "timestamp": t_str,
                        "event": f"Extracted indicator: {art_type}",
                        "details": f"Value: {art_val} found at source {src_url}"
                    })

                profile["linked_iocs"] = linked_iocs
                profile["transaction_trail"] = transaction_trail
                profile["platform_presence"] = platform_presence
                # Sort timeline chronologically
                profile["timeline"] = sorted(timeline, key=lambda x: x["timestamp"])
                
                return profile
        except Exception as e:
            logger.error(f"Error building actor profile {actor_id}: {e}", exc_info=True)
            return None

    def get_all_profiles(self) -> List[Dict[str, Any]]:
        """Fetch basic details of all tracked threat actors."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id, primary_handle, threat_level, first_seen, last_seen FROM actor_profiles")
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error fetching profiles: {e}")
            return []

    def correlate_across_sources(self, artifact_value: str) -> List[Dict[str, Any]]:
        """Identify all actor profiles that share the exact same IOC value (e.g. BTC wallet)."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT DISTINCT p.id, p.primary_handle, p.threat_level 
                    FROM actor_profiles p
                    JOIN actor_artifacts a ON p.id = a.actor_id
                    WHERE a.artifact_value = ?
                """, (artifact_value,))
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error correlating artifact: {e}")
            return []

    def export_profile(self, actor_id: int, export_format: str = "json") -> str:
        """Export profile in JSON or STIX 2.1 Threat Actor representation."""
        profile = self.build_profile(actor_id)
        if not profile:
            return "{}"

        if export_format.lower() == "stix2":
            # Map compiled profile to STIX 2.1 JSON structure
            import uuid
            actor_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"drishti.threatactor.{profile['primary_handle']}"))
            
            stix_ta = {
                "type": "threat-actor",
                "spec_version": "2.1",
                "id": f"threat-actor--{actor_uuid}",
                "created": profile["first_seen"],
                "modified": profile["last_seen"],
                "name": profile["primary_handle"],
                "description": profile["description"],
                "threat_actor_types": ["cyber-attacker"],
                "aliases": profile["linked_pseudonyms"],
                "goals": ["Financial Gain", "Espionage"],
                "sophistication": "intermediate",
                "resource_level": "individual",
                "external_references": [
                    {"source_name": "drishti-platform", "external_id": str(actor_id)}
                ],
                "custom_properties": {
                    "x_drishti_threat_level": profile["threat_level"],
                    "x_drishti_writing_style": profile["writing_style"],
                    "x_drishti_ttp_tags": profile["ttp_tags"]
                }
            }
            return json.dumps(stix_ta, indent=2)
        
        # Default JSON
        return json.dumps(profile, indent=2)
