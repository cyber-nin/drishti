"""
Drishti Watchlist Manager.
Handles persistent watchlists, monitored keywords, and security alerts using SQLite.
"""
import os
import sqlite3
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

try:
    from backend.config import DATABASE_URL
except ModuleNotFoundError:
    try:
        from config import DATABASE_URL
    except ModuleNotFoundError:
        DATABASE_URL = None

logger = logging.getLogger(__name__)

class WatchlistManager:
    """Manages watchlists, search keywords, and security alert logs."""

    def __init__(self, db_path: Optional[str] = None):
        if db_path:
            self.db_path = db_path
        elif DATABASE_URL and DATABASE_URL.startswith("sqlite:///"):
            self.db_path = DATABASE_URL.replace("sqlite:///", "")
        else:
            # Fallback default path in the data folder
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
        """Initialize watchlist tables on startup."""
        try:
            with self._get_connection() as conn:
                # Create watchlists table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS watchlists (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL UNIQUE,
                        alert_email TEXT,
                        webhook_url TEXT,
                        severity_threshold INTEGER DEFAULT 35,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                # Create watchlist keywords table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS watchlist_keywords (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        watchlist_id INTEGER NOT NULL,
                        keyword TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (watchlist_id) REFERENCES watchlists(id) ON DELETE CASCADE,
                        UNIQUE(watchlist_id, keyword)
                    )
                """)
                # Create watchlist alerts table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS watchlist_alerts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        watchlist_id INTEGER NOT NULL,
                        finding_summary TEXT,
                        severity_score INTEGER,
                        source_url TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (watchlist_id) REFERENCES watchlists(id) ON DELETE CASCADE
                    )
                """)
                conn.commit()
            logger.info("Watchlist Database initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize Watchlist DB: {e}")

    def create_watchlist(
        self,
        name: str,
        keywords: List[str],
        alert_email: Optional[str] = None,
        webhook_url: Optional[str] = None,
        severity_threshold: int = 35
    ) -> int:
        """Create a new watchlist and associate a list of keywords."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO watchlists (name, alert_email, webhook_url, severity_threshold) VALUES (?, ?, ?, ?)",
                    (name, alert_email, webhook_url, severity_threshold)
                )
                watchlist_id = cursor.lastrowid
                
                # Insert keywords
                for kw in keywords:
                    kw_clean = kw.strip()
                    if kw_clean:
                        cursor.execute(
                            "INSERT OR IGNORE INTO watchlist_keywords (watchlist_id, keyword) VALUES (?, ?)",
                            (watchlist_id, kw_clean)
                        )
                conn.commit()
                logger.info(f"Watchlist '{name}' created with ID {watchlist_id}.")
                return watchlist_id
        except sqlite3.IntegrityError:
            logger.warning(f"Watchlist with name '{name}' already exists.")
            # Retrieve existing id
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id FROM watchlists WHERE name = ?", (name,))
                row = cursor.fetchone()
                return row[0] if row else -1
        except Exception as e:
            logger.error(f"Error creating watchlist: {e}")
            return -1

    def get_all_watchlists(self) -> List[Dict[str, Any]]:
        """Retrieve all watchlists with their respective keywords."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM watchlists")
                watchlists = [dict(row) for row in cursor.fetchall()]
                
                for wl in watchlists:
                    cursor.execute("SELECT keyword FROM watchlist_keywords WHERE watchlist_id = ?", (wl["id"],))
                    wl["keywords"] = [row["keyword"] for row in cursor.fetchall()]
                
                return watchlists
        except Exception as e:
            logger.error(f"Error fetching watchlists: {e}")
            return []

    def get_watchlist(self, watchlist_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve a specific watchlist with its keywords."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM watchlists WHERE id = ?", (watchlist_id,))
                row = cursor.fetchone()
                if not row:
                    return None
                wl = dict(row)
                cursor.execute("SELECT keyword FROM watchlist_keywords WHERE watchlist_id = ?", (wl["id"],))
                wl["keywords"] = [row["keyword"] for row in cursor.fetchall()]
                return wl
        except Exception as e:
            logger.error(f"Error fetching watchlist {watchlist_id}: {e}")
            return None

    def add_keyword(self, watchlist_id: int, keyword: str) -> bool:
        """Add a keyword to an existing watchlist."""
        kw_clean = keyword.strip()
        if not kw_clean:
            return False
        try:
            with self._get_connection() as conn:
                conn.execute(
                    "INSERT OR IGNORE INTO watchlist_keywords (watchlist_id, keyword) VALUES (?, ?)",
                    (watchlist_id, kw_clean)
                )
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error adding keyword to watchlist {watchlist_id}: {e}")
            return False

    def remove_keyword(self, watchlist_id: int, keyword: str) -> bool:
        """Remove a keyword from a watchlist."""
        try:
            with self._get_connection() as conn:
                conn.execute(
                    "DELETE FROM watchlist_keywords WHERE watchlist_id = ? AND keyword = ?",
                    (watchlist_id, keyword)
                )
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error removing keyword from watchlist {watchlist_id}: {e}")
            return False

    def remove_watchlist(self, watchlist_id: int) -> bool:
        """Delete an entire watchlist (cascades keywords and alerts)."""
        try:
            with self._get_connection() as conn:
                conn.execute("DELETE FROM watchlists WHERE id = ?", (watchlist_id,))
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error removing watchlist {watchlist_id}: {e}")
            return False

    def record_alert(
        self,
        watchlist_id: int,
        finding_summary: str,
        severity_score: int,
        source_url: str
    ) -> bool:
        """Log a new triggered alert."""
        try:
            with self._get_connection() as conn:
                conn.execute(
                    "INSERT INTO watchlist_alerts (watchlist_id, finding_summary, severity_score, source_url) VALUES (?, ?, ?, ?)",
                    (watchlist_id, finding_summary, severity_score, source_url)
                )
                conn.commit()
            logger.info(f"Recorded alert for Watchlist ID {watchlist_id} with score {severity_score}.")
            return True
        except Exception as e:
            logger.error(f"Error recording alert: {e}")
            return False

    def get_alerts(self, watchlist_id: int, since_timestamp: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieve historical alerts for a watchlist."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                if since_timestamp:
                    cursor.execute(
                        "SELECT * FROM watchlist_alerts WHERE watchlist_id = ? AND created_at >= ? ORDER BY created_at DESC",
                        (watchlist_id, since_timestamp)
                    )
                else:
                    cursor.execute(
                        "SELECT * FROM watchlist_alerts WHERE watchlist_id = ? ORDER BY created_at DESC",
                        (watchlist_id,)
                    )
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error retrieving alerts: {e}")
            return []
