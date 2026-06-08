"""
Drishti Database Layer.
SQLAlchemy ORM models and session management.
Supports SQLite (default/dev) and PostgreSQL (production) via DATABASE_URL.
"""
import os
import logging
from datetime import datetime, timezone
from contextlib import contextmanager

from sqlalchemy import (
    create_engine, Column, Integer, String, Text, Float, Boolean,
    DateTime, ForeignKey, JSON, Index, Enum as SAEnum, UniqueConstraint
)
from sqlalchemy.orm import (
    declarative_base, relationship, sessionmaker, Session
)

try:
    from backend.config import DATABASE_URL
except (ModuleNotFoundError, ImportError):
    try:
        from config import DATABASE_URL
    except (ModuleNotFoundError, ImportError):
        DATABASE_URL = None

logger = logging.getLogger(__name__)

# Resolve database URL — default to SQLite in project root
_DB_URL = DATABASE_URL or os.getenv(
    "DATABASE_URL",
    f"sqlite:///{os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'drishti.db')}"
)

# Create engine
_engine_kwargs = {}
if _DB_URL.startswith("sqlite"):
    _engine_kwargs["connect_args"] = {"check_same_thread": False}
    # Ensure data directory exists
    db_path = _DB_URL.replace("sqlite:///", "")
    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)

engine = create_engine(_DB_URL, echo=False, pool_pre_ping=True, **_engine_kwargs)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()


def _utcnow():
    return datetime.now(timezone.utc)


# ── Models ────────────────────────────────────────────────────────────────────


class User(Base):
    """Platform user with role-based access."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(64), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default="analyst")  # admin, analyst, viewer
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=_utcnow, nullable=False)
    last_login = Column(DateTime, nullable=True)

    # Relationships
    investigations = relationship("Investigation", back_populates="user", lazy="dynamic")
    audit_logs = relationship("AuditLog", back_populates="user", lazy="dynamic")

    def __repr__(self):
        return f"<User {self.username} ({self.role})>"


class Investigation(Base):
    """A single investigation run (search + scrape + summarize)."""
    __tablename__ = "investigations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    query = Column(Text, nullable=False)
    refined_query = Column(Text, nullable=True)
    model = Column(String(64), nullable=True)
    status = Column(String(20), nullable=False, default="running")  # running, complete, failed
    report_path = Column(String(512), nullable=True)
    result_count = Column(Integer, default=0)
    scraped_count = Column(Integer, default=0)
    ioc_count = Column(Integer, default=0)
    threat_category = Column(String(64), nullable=True)
    tags = Column(JSON, default=list)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=_utcnow, nullable=False, index=True)
    completed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Float, nullable=True)

    # Foreign keys
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=True)
    watch_job_id = Column(Integer, ForeignKey("watch_jobs.id"), nullable=True)

    # Relationships
    user = relationship("User", back_populates="investigations")
    case = relationship("Case", back_populates="investigations")
    watch_job = relationship("WatchJob", back_populates="investigations")
    iocs = relationship("IOC", back_populates="investigation", cascade="all, delete-orphan", lazy="dynamic")

    __table_args__ = (
        Index("ix_investigations_query", "query", mysql_length=255),
        Index("ix_investigations_status", "status"),
    )

    def __repr__(self):
        return f"<Investigation #{self.id} q={self.query[:40]!r}>"


class IOC(Base):
    """Individual Indicator of Compromise extracted from an investigation."""
    __tablename__ = "iocs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ioc_type = Column(String(32), nullable=False, index=True)  # email, btc, ipv4, domain, etc.
    value = Column(String(512), nullable=False, index=True)
    source_url = Column(Text, nullable=True)
    context = Column(Text, nullable=True)  # surrounding text for context
    confidence = Column(String(16), default="medium")  # low, medium, high
    first_seen = Column(DateTime, default=_utcnow, nullable=False)
    last_seen = Column(DateTime, default=_utcnow, nullable=False)

    # Foreign keys
    investigation_id = Column(Integer, ForeignKey("investigations.id"), nullable=False)
    threat_actor_id = Column(Integer, ForeignKey("threat_actors.id"), nullable=True)

    # Relationships
    investigation = relationship("Investigation", back_populates="iocs")
    threat_actor = relationship("ThreatActor", back_populates="iocs")
    enrichments = relationship("Enrichment", back_populates="ioc", cascade="all, delete-orphan", lazy="joined")

    __table_args__ = (
        Index("ix_iocs_type_value", "ioc_type", "value"),
        UniqueConstraint("ioc_type", "value", "source_url", "investigation_id", name="uq_ioc_per_investigation"),
    )

    def __repr__(self):
        return f"<IOC {self.ioc_type}={self.value[:30]}>"


class Enrichment(Base):
    """Reputation / enrichment data for an IOC."""
    __tablename__ = "enrichments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source = Column(String(64), nullable=False)  # virustotal, abuseipdb, shodan, etc.
    data = Column(JSON, nullable=False, default=dict)
    malicious_count = Column(Integer, default=0)
    suspicious_count = Column(Integer, default=0)
    abuse_score = Column(Float, nullable=True)
    country = Column(String(8), nullable=True)
    queried_at = Column(DateTime, default=_utcnow, nullable=False)

    # Foreign key
    ioc_id = Column(Integer, ForeignKey("iocs.id"), nullable=False)

    # Relationship
    ioc = relationship("IOC", back_populates="enrichments")

    def __repr__(self):
        return f"<Enrichment {self.source} for IOC#{self.ioc_id}>"


class ThreatActor(Base):
    """A tracked threat actor / persona."""
    __tablename__ = "threat_actors"

    id = Column(Integer, primary_key=True, autoincrement=True)
    primary_handle = Column(String(128), nullable=False, unique=True, index=True)
    aliases = Column(JSON, default=list)  # list of known aliases
    pgp_fingerprint = Column(String(64), nullable=True)
    description = Column(Text, nullable=True)
    threat_level = Column(String(16), default="unknown")  # unknown, low, medium, high, critical
    first_seen = Column(DateTime, default=_utcnow, nullable=False)
    last_seen = Column(DateTime, default=_utcnow, nullable=False)
    notes = Column(Text, nullable=True)
    tags = Column(JSON, default=list)
    metadata_ = Column("metadata", JSON, default=dict)

    # Relationships
    iocs = relationship("IOC", back_populates="threat_actor", lazy="dynamic")

    def __repr__(self):
        return f"<ThreatActor {self.primary_handle}>"


class WatchJob(Base):
    """A scheduled monitoring job that runs periodically."""
    __tablename__ = "watch_jobs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    query = Column(Text, nullable=False)
    model = Column(String(64), default="gpt-5-mini")
    schedule_cron = Column(String(64), nullable=False)  # cron expression
    is_active = Column(Boolean, default=True, nullable=False)
    notify_email = Column(String(255), nullable=True)
    notify_webhook = Column(String(512), nullable=True)
    notify_ui = Column(Boolean, default=True)
    last_run_at = Column(DateTime, nullable=True)
    next_run_at = Column(DateTime, nullable=True)
    run_count = Column(Integer, default=0)
    last_ioc_hash = Column(String(64), nullable=True)  # SHA256 of last IOC set for delta detection
    created_at = Column(DateTime, default=_utcnow, nullable=False)

    # Foreign keys
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Relationships
    investigations = relationship("Investigation", back_populates="watch_job", lazy="dynamic")
    alerts = relationship("Alert", back_populates="watch_job", cascade="all, delete-orphan", lazy="dynamic")

    def __repr__(self):
        return f"<WatchJob #{self.id} q={self.query[:30]!r}>"


class Alert(Base):
    """An alert generated by a watch job when new IOCs are detected."""
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    severity = Column(String(16), nullable=False, default="info")  # info, warning, critical
    title = Column(String(255), nullable=False)
    summary = Column(Text, nullable=True)
    delta_data = Column(JSON, default=dict)  # new IOCs, new URLs, etc.
    is_read = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=_utcnow, nullable=False, index=True)

    # Foreign keys
    watch_job_id = Column(Integer, ForeignKey("watch_jobs.id"), nullable=False)

    # Relationship
    watch_job = relationship("WatchJob", back_populates="alerts")

    def __repr__(self):
        return f"<Alert [{self.severity}] {self.title[:40]}>"


class Case(Base):
    """A case groups multiple investigations into a single operation."""
    __tablename__ = "cases"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="open")  # open, closed, escalated
    priority = Column(String(16), default="medium")  # low, medium, high, critical
    tags = Column(JSON, default=list)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=_utcnow, nullable=False)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)
    closed_at = Column(DateTime, nullable=True)

    # Foreign keys
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Relationships
    investigations = relationship("Investigation", back_populates="case", lazy="dynamic")

    def __repr__(self):
        return f"<Case {self.name!r} ({self.status})>"


class AuditLog(Base):
    """Immutable audit trail for all significant actions."""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    action = Column(String(64), nullable=False, index=True)
    # Actions: login, logout, investigate, crawl, export, batch, watch.create,
    #          watch.delete, enrich, user.create, user.update, config.change
    target = Column(String(512), nullable=True)  # what was acted upon
    detail = Column(JSON, default=dict)  # additional context
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(512), nullable=True)
    created_at = Column(DateTime, default=_utcnow, nullable=False, index=True)

    # Foreign key
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Relationship
    user = relationship("User", back_populates="audit_logs")

    __table_args__ = (
        Index("ix_audit_user_action", "user_id", "action"),
    )

    def __repr__(self):
        return f"<AuditLog {self.action} by user#{self.user_id} at {self.created_at}>"


# ── Session Helpers ───────────────────────────────────────────────────────────

@contextmanager
def get_session():
    """Context manager yielding a database session with auto-commit/rollback."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db() -> Session:
    """Generator for FastAPI/Flask dependency injection."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db():
    """Create all tables. Safe to call multiple times."""
    Base.metadata.create_all(bind=engine)
    logger.info(f"Database initialized: {_DB_URL.split('?')[0]}")


def drop_all():
    """Drop all tables — for testing only."""
    Base.metadata.drop_all(bind=engine)
    logger.warning("All database tables dropped!")
