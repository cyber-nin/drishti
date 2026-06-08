"""
Drishti Audit Logging System.
Provides immutable, append-only audit trail for all significant platform actions.
"""
import logging
from datetime import datetime, timezone
from typing import Optional

from flask import request, g

try:
    from backend.database import get_session, AuditLog
except (ModuleNotFoundError, ImportError):
    from database import get_session, AuditLog

logger = logging.getLogger(__name__)


# ── Audit Actions ─────────────────────────────────────────────────────────────

class AuditAction:
    """Constants for audit action types."""
    # Authentication
    LOGIN = "auth.login"
    LOGOUT = "auth.logout"
    LOGIN_FAILED = "auth.login_failed"
    USER_CREATED = "user.created"
    USER_UPDATED = "user.updated"
    PASSWORD_CHANGED = "user.password_changed"

    # Investigation
    INVESTIGATE = "investigate"
    INVESTIGATE_COMPLETE = "investigate.complete"
    INVESTIGATE_FAILED = "investigate.failed"

    # Deep Crawl
    CRAWL = "crawl"
    CRAWL_COMPLETE = "crawl.complete"

    # Batch
    BATCH_START = "batch.start"
    BATCH_COMPLETE = "batch.complete"

    # Export
    EXPORT = "export"
    DOWNLOAD = "download"

    # Watch Jobs
    WATCH_CREATE = "watch.create"
    WATCH_DELETE = "watch.delete"
    WATCH_UPDATE = "watch.update"
    WATCH_TRIGGER = "watch.trigger"

    # Alerts
    ALERT_TRIGGERED = "alert.triggered"
    ALERT_ACKNOWLEDGED = "alert.acknowledged"

    # Enrichment
    ENRICH = "enrich"

    # Graph
    GRAPH_BUILD = "graph.build"

    # Tor
    TOR_CONNECT = "tor.connect"
    TOR_DISCONNECT = "tor.disconnect"
    TOR_ROTATE = "tor.rotate"

    # Case Management
    CASE_CREATE = "case.create"
    CASE_UPDATE = "case.update"
    CASE_CLOSE = "case.close"

    # System
    CONFIG_CHANGE = "config.change"
    SYSTEM_START = "system.start"


# ── Core Logging Function ────────────────────────────────────────────────────

def log_audit(
    action: str,
    target: Optional[str] = None,
    detail: Optional[dict] = None,
    user_id: Optional[int] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
):
    """
    Write an immutable audit log entry.

    If called inside a Flask request context, user/IP/UA are auto-detected
    from g.current_user and request headers. These can be overridden via args.

    Args:
        action:     Action constant from AuditAction
        target:     What was acted upon (e.g., query text, filename, user id)
        detail:     Additional context dict
        user_id:    Override auto-detected user ID
        ip_address: Override auto-detected IP
        user_agent: Override auto-detected User-Agent
    """
    try:
        # Auto-detect from Flask context (safe outside request context)
        if user_id is None:
            try:
                current_user = getattr(g, 'current_user', None)
                if current_user:
                    user_id = current_user.get("id")
            except RuntimeError:
                pass  # outside Flask request context

        if ip_address is None:
            try:
                ip_address = request.headers.get("X-Forwarded-For", request.remote_addr)
            except RuntimeError:
                ip_address = None

        if user_agent is None:
            try:
                user_agent = request.headers.get("User-Agent", "")[:512]
            except RuntimeError:
                user_agent = None

        # Sanitize target
        if target and len(target) > 512:
            target = target[:509] + "..."

        with get_session() as session:
            entry = AuditLog(
                action=action,
                target=target,
                detail=detail or {},
                user_id=user_id,
                ip_address=ip_address,
                user_agent=user_agent,
            )
            session.add(entry)

        logger.debug(f"Audit: {action} target={target!r} user={user_id}")

    except Exception as e:
        # Audit logging must NEVER crash the application
        logger.error(f"Audit log failed: {e}", exc_info=True)


# ── Query Functions ───────────────────────────────────────────────────────────

def query_audit_logs(
    user_id: Optional[int] = None,
    action: Optional[str] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    limit: int = 100,
    offset: int = 0,
) -> dict:
    """
    Query audit logs with optional filters.

    Returns:
        {"total": int, "logs": [dict]}
    """
    with get_session() as session:
        query = session.query(AuditLog)

        if user_id is not None:
            query = query.filter(AuditLog.user_id == user_id)
        if action:
            query = query.filter(AuditLog.action == action)
        if from_date:
            query = query.filter(AuditLog.created_at >= from_date)
        if to_date:
            query = query.filter(AuditLog.created_at <= to_date)

        total = query.count()
        logs = query.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit).all()

        return {
            "total": total,
            "offset": offset,
            "limit": limit,
            "logs": [
                {
                    "id": log.id,
                    "action": log.action,
                    "target": log.target,
                    "detail": log.detail,
                    "user_id": log.user_id,
                    "ip_address": log.ip_address,
                    "created_at": log.created_at.isoformat() if log.created_at else None,
                }
                for log in logs
            ],
        }


def get_user_activity(user_id: int, days: int = 30) -> dict:
    """Get activity summary for a user over the last N days."""
    from_date = datetime.now(timezone.utc) - __import__('datetime').timedelta(days=days)

    with get_session() as session:
        from sqlalchemy import func

        actions = (
            session.query(AuditLog.action, func.count(AuditLog.id))
            .filter(AuditLog.user_id == user_id, AuditLog.created_at >= from_date)
            .group_by(AuditLog.action)
            .all()
        )

        return {
            "user_id": user_id,
            "period_days": days,
            "actions": {action: count for action, count in actions},
            "total": sum(count for _, count in actions),
        }
