"""
Drishti Alert Dispatcher.
Routes security threat alerts to Webhooks, Slack channels, and SMTP Email, keeping persistent logs.
"""
import hmac
import hashlib
import json
import time
import smtplib
import sqlite3
import os
import logging
from email.mime.text import MIMEText
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import requests

try:
    from backend.config import (
        DATABASE_URL, ALERT_WEBHOOK_URL, ALERT_SLACK_URL,
        ALERT_SMTP_HOST, ALERT_SMTP_PORT, ALERT_SMTP_USER, ALERT_SMTP_PASSWORD, ALERT_SMTP_FROM,
        AUTH_SECRET_KEY
    )
except ModuleNotFoundError:
    try:
        from config import (
            DATABASE_URL, ALERT_WEBHOOK_URL, ALERT_SLACK_URL,
            ALERT_SMTP_HOST, ALERT_SMTP_PORT, ALERT_SMTP_USER, ALERT_SMTP_PASSWORD, ALERT_SMTP_FROM,
            AUTH_SECRET_KEY
        )
    except ModuleNotFoundError:
        DATABASE_URL = ALERT_WEBHOOK_URL = ALERT_SLACK_URL = None
        ALERT_SMTP_HOST = ALERT_SMTP_PORT = ALERT_SMTP_USER = ALERT_SMTP_PASSWORD = ALERT_SMTP_FROM = None
        AUTH_SECRET_KEY = "drishti-fallback-secret-key"

logger = logging.getLogger(__name__)

class AlertDispatcher:
    """Handles dispatching of alerts to external sinks like SIEM, Slack, and email."""

    def __init__(self, db_path: Optional[str] = None):
        if db_path:
            self.db_path = db_path
        elif DATABASE_URL and DATABASE_URL.startswith("sqlite:///"):
            self.db_path = DATABASE_URL.replace("sqlite:///", "")
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            self.db_path = os.path.join(base_dir, "data", "drishti.db")

        self.webhook_secret = AUTH_SECRET_KEY or "drishti-alert-secret"
        self._init_db()

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Ensure alert dispatch history logging table exists."""
        try:
            with self._get_connection() as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS alert_dispatch_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        alert_id TEXT NOT NULL,
                        channel TEXT NOT NULL,
                        status TEXT NOT NULL,
                        attempts INTEGER DEFAULT 1,
                        error_message TEXT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to initialize Alert Dispatch DB: {e}")

    def _log_dispatch(self, alert_id: str, channel: str, status: str, attempts: int, error_msg: Optional[str] = None):
        """Persist alert log to sqlite."""
        try:
            with self._get_connection() as conn:
                conn.execute(
                    "INSERT INTO alert_dispatch_logs (alert_id, channel, status, attempts, error_message) VALUES (?, ?, ?, ?, ?)",
                    (alert_id, channel, status, attempts, error_msg)
                )
                conn.commit()
        except Exception as e:
            logger.error(f"Error persisting dispatch log: {e}")

    def dispatch(self, alert_payload: Dict[str, Any], destination_overrides: Optional[Dict[str, str]] = None):
        """
        Dispatch the threat alert to configured destinations.

        Args:
            alert_payload: Payload schema matching requirements
            destination_overrides: Optional dictionary with custom alert_email and webhook_url
        """
        alert_id = alert_payload["alert_id"]
        logger.info(f"Dispatching alert ID: {alert_id}")

        overrides = destination_overrides or {}

        # 1. Custom Webhook dispatch
        webhook_target = overrides.get("webhook") or ALERT_WEBHOOK_URL
        if webhook_target:
            self._dispatch_webhook(alert_id, webhook_target, alert_payload)

        # 2. Slack Integration dispatch
        slack_target = ALERT_SLACK_URL
        if slack_target:
            self._dispatch_slack(alert_id, slack_target, alert_payload)

        # 3. Email Integration dispatch
        email_target = overrides.get("email") or ALERT_SMTP_FROM
        if email_target and ALERT_SMTP_HOST:
            self._dispatch_email(alert_id, email_target, alert_payload)

        # If no dispatch targets were matched, log a local bypass/skipped entry
        if not webhook_target and not slack_target and not (email_target and ALERT_SMTP_HOST):
            logger.warning(f"No dispatch channels configured for alert {alert_id}. Logged local bypass.")
            self._log_dispatch(alert_id, "local_bypass", "skipped", 1, "No channels configured")


    def _dispatch_webhook(self, alert_id: str, url: str, payload: Dict[str, Any]):
        """Post JSON to Webhook with HMAC signature and exponential backoff retry."""
        payload_str = json.dumps(payload, sort_keys=True)
        # Compute signature
        signature = hmac.new(
            self.webhook_secret.encode("utf-8"),
            payload_str.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

        headers = {
            "Content-Type": "application/json",
            "X-Drishti-Signature": signature
        }

        attempts = 0
        max_attempts = 3
        delay = 1.0  # initial 1 second delay
        success = False
        error_msg = None

        while attempts < max_attempts and not success:
            attempts += 1
            try:
                r = requests.post(url, data=payload_str, headers=headers, timeout=10)
                if r.status_code in (200, 201, 202, 204):
                    success = True
                    error_msg = None
                    logger.info(f"Webhook dispatch succeeded for alert {alert_id} on attempt {attempts}.")
                else:
                    error_msg = f"HTTP {r.status_code}: {r.text}"
                    logger.warning(f"Webhook dispatch failed: {error_msg}. Retrying...")
            except Exception as e:
                error_msg = str(e)
                logger.warning(f"Webhook connection failure: {error_msg}. Retrying...")

            if not success and attempts < max_attempts:
                time.sleep(delay)
                delay *= 2.0  # exponential backoff

        status = "delivered" if success else "failed"
        self._log_dispatch(alert_id, f"webhook:{url}", status, attempts, error_msg)

    def _dispatch_slack(self, alert_id: str, webhook_url: str, payload: Dict[str, Any]):
        """Publish alert to Slack using rich Blocks layout."""
        severity = payload["severity"]
        color = "#ff0000" if severity["tier"] == "CRITICAL" else ("#ff8c00" if severity["tier"] == "HIGH" else "#ffcc00")
        emoji = "🚨" if severity["tier"] == "CRITICAL" else ("⚠️" if severity["tier"] == "HIGH" else "📌")

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{emoji} Drishti Threat Alert: {payload['watchlist_name']}",
                    "emoji": True
                }
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Severity Score:* `{severity['score']}` ({severity['tier']})"},
                    {"type": "mrkdwn", "text": f"*Triggered Keyword:* `{payload['triggered_keyword']}`"}
                ]
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Source Dark Web URL:*\n<{payload['source_url']}|{payload['source_url']}>"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Summary finding:*\n>{payload['summary']}"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Recommended Action:*\n_{payload['recommended_action']}_"
                }
            },
            {"type": "divider"}
        ]

        slack_payload = {
            "attachments": [
                {
                    "color": color,
                    "blocks": blocks
                }
            ]
        }

        try:
            r = requests.post(webhook_url, json=slack_payload, timeout=10)
            if r.status_code == 200:
                logger.info(f"Slack dispatch succeeded for alert {alert_id}.")
                self._log_dispatch(alert_id, "slack", "delivered", 1)
            else:
                logger.error(f"Slack dispatch HTTP error: {r.status_code} - {r.text}")
                self._log_dispatch(alert_id, "slack", "failed", 1, f"HTTP {r.status_code}")
        except Exception as e:
            logger.error(f"Slack dispatch exception: {e}")
            self._log_dispatch(alert_id, "slack", "failed", 1, str(e))

    def _dispatch_email(self, alert_id: str, recipient: str, payload: Dict[str, Any]):
        """Send Email notification using smtplib."""
        severity = payload["severity"]
        subject = f"[Drishti Alert - {severity['tier']}] Dark Web threat found for watchlist {payload['watchlist_name']}"
        
        email_body = f"""
=== DRISHTI DARK WEB MONITORED ALERT ===
Alert ID: {alert_id}
Timestamp: {payload['timestamp']}
Watchlist: {payload['watchlist_name']}
Triggered Keyword: {payload['triggered_keyword']}
Severity Score: {severity['score']} / 100 ({severity['tier']})

Source Onion URL: {payload['source_url']}

Summary Findings:
----------------------------------------
{payload['summary']}

Recommended Security Action:
----------------------------------------
{payload['recommended_action']}

----------------------------------------
Security Advisory: Generated automatically by Drishti OSINT Platform.
        """

        msg = MIMEText(email_body)
        msg["Subject"] = subject
        msg["From"] = ALERT_SMTP_FROM or "drishti-alerts@lea.gov.in"
        msg["To"] = recipient

        try:
            # Connect via smtplib
            port = int(ALERT_SMTP_PORT) if ALERT_SMTP_PORT else 587
            with smtplib.SMTP(ALERT_SMTP_HOST, port, timeout=15) as server:
                server.ehlo()
                if port == 587:
                    server.starttls()
                    server.ehlo()
                if ALERT_SMTP_USER and ALERT_SMTP_PASSWORD:
                    server.login(ALERT_SMTP_USER, ALERT_SMTP_PASSWORD)
                server.sendmail(msg["From"], [recipient], msg.as_string())
            
            logger.info(f"Email alert dispatched successfully to {recipient}.")
            self._log_dispatch(alert_id, f"email:{recipient}", "delivered", 1)
        except Exception as e:
            logger.error(f"Email dispatch failed: {e}")
            self._log_dispatch(alert_id, f"email:{recipient}", "failed", 1, str(e))
