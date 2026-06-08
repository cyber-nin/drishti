"""
Drishti Authentication & Authorization.
JWT-based auth with bcrypt password hashing and role-based access control.
"""
import os
import logging
import hashlib
import secrets
from datetime import datetime, timezone, timedelta
from functools import wraps
from typing import Optional

import jwt
from flask import request, jsonify, g

try:
    from backend.database import get_session, User
    from backend.config import (
        AUTH_SECRET_KEY, AUTH_TOKEN_EXPIRY_MINUTES,
        AUTH_REFRESH_TOKEN_EXPIRY_DAYS, AUTH_ENABLED
    )
except (ModuleNotFoundError, ImportError):
    from database import get_session, User
    try:
        from config import (
            AUTH_SECRET_KEY, AUTH_TOKEN_EXPIRY_MINUTES,
            AUTH_REFRESH_TOKEN_EXPIRY_DAYS, AUTH_ENABLED
        )
    except ImportError:
        AUTH_SECRET_KEY = "drishti-dev-secret-change-in-production"
        AUTH_TOKEN_EXPIRY_MINUTES = 60
        AUTH_REFRESH_TOKEN_EXPIRY_DAYS = 7
        AUTH_ENABLED = False

logger = logging.getLogger(__name__)

# ── Password Hashing ─────────────────────────────────────────────────────────
# Using hashlib (PBKDF2) to avoid external bcrypt dependency issues on Windows


def hash_password(password: str) -> str:
    """Hash a password with PBKDF2-SHA256 and a random salt."""
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100_000)
    return f"{salt}:{key.hex()}"


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against its PBKDF2-SHA256 hash."""
    try:
        salt, key_hex = password_hash.split(':')
        key = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100_000)
        return key.hex() == key_hex
    except (ValueError, AttributeError):
        return False


# ── Token Management ──────────────────────────────────────────────────────────

def create_access_token(user_id: int, username: str, role: str) -> str:
    """Create a JWT access token."""
    payload = {
        "sub": user_id,
        "username": username,
        "role": role,
        "type": "access",
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=AUTH_TOKEN_EXPIRY_MINUTES),
    }
    return jwt.encode(payload, AUTH_SECRET_KEY, algorithm="HS256")


def create_refresh_token(user_id: int) -> str:
    """Create a JWT refresh token with longer expiry."""
    payload = {
        "sub": user_id,
        "type": "refresh",
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(days=AUTH_REFRESH_TOKEN_EXPIRY_DAYS),
    }
    return jwt.encode(payload, AUTH_SECRET_KEY, algorithm="HS256")


def decode_token(token: str) -> Optional[dict]:
    """Decode and validate a JWT token. Returns payload or None."""
    try:
        payload = jwt.decode(token, AUTH_SECRET_KEY, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        logger.debug("Token expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.debug(f"Invalid token: {e}")
        return None


# ── User Management ───────────────────────────────────────────────────────────

def create_user(username: str, password: str, role: str = "analyst", email: str = None) -> dict:
    """
    Create a new user. Returns user dict on success, error dict on failure.
    """
    if role not in ("admin", "analyst", "viewer"):
        return {"error": f"Invalid role: {role}. Must be admin, analyst, or viewer."}

    if len(username) < 3 or len(username) > 64:
        return {"error": "Username must be 3-64 characters."}

    if len(password) < 8:
        return {"error": "Password must be at least 8 characters."}

    with get_session() as session:
        existing = session.query(User).filter(
            (User.username == username) | (User.email == email if email else False)
        ).first()

        if existing:
            return {"error": "Username or email already exists."}

        user = User(
            username=username,
            email=email,
            password_hash=hash_password(password),
            role=role,
        )
        session.add(user)
        session.flush()

        return {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "created_at": user.created_at.isoformat(),
        }


def authenticate_user(username: str, password: str) -> Optional[dict]:
    """
    Authenticate a user by username and password.
    Returns user dict with tokens on success, None on failure.
    """
    with get_session() as session:
        user = session.query(User).filter_by(username=username, is_active=True).first()
        if not user or not verify_password(password, user.password_hash):
            return None

        user.last_login = datetime.now(timezone.utc)
        session.flush()

        access_token = create_access_token(user.id, user.username, user.role)
        refresh_token = create_refresh_token(user.id)

        return {
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role": user.role,
            },
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
        }


def refresh_access_token(refresh_token_str: str) -> Optional[dict]:
    """
    Issue a new access token using a valid refresh token.
    """
    payload = decode_token(refresh_token_str)
    if not payload or payload.get("type") != "refresh":
        return None

    user_id = payload.get("sub")
    with get_session() as session:
        user = session.query(User).filter_by(id=user_id, is_active=True).first()
        if not user:
            return None

        access_token = create_access_token(user.id, user.username, user.role)
        return {
            "access_token": access_token,
            "token_type": "bearer",
        }


# ── Flask Middleware ──────────────────────────────────────────────────────────

def get_current_user() -> Optional[dict]:
    """Extract the current user from the request's Authorization header."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None

    token = auth_header[7:]
    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        return None

    return {
        "id": payload.get("sub"),
        "username": payload.get("username"),
        "role": payload.get("role"),
    }


def require_auth(f):
    """
    Flask decorator: requires a valid JWT access token.
    Sets g.current_user for downstream use.
    When AUTH_ENABLED is False, sets a default anonymous user.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        if not AUTH_ENABLED:
            # Auth disabled — set anonymous user context
            g.current_user = {"id": None, "username": "anonymous", "role": "admin"}
            return f(*args, **kwargs)

        user = get_current_user()
        if not user:
            return jsonify({"error": "Authentication required"}), 401

        g.current_user = user
        return f(*args, **kwargs)

    return decorated


def require_role(*roles):
    """
    Flask decorator: requires user to have one of the specified roles.
    Must be used AFTER @require_auth.

    Usage:
        @app.route('/admin-only')
        @require_auth
        @require_role('admin')
        def admin_endpoint():
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            user = getattr(g, 'current_user', None)
            if not user:
                return jsonify({"error": "Authentication required"}), 401

            if user.get("role") not in roles:
                return jsonify({
                    "error": "Insufficient permissions",
                    "required_roles": list(roles),
                    "your_role": user.get("role"),
                }), 403

            return f(*args, **kwargs)
        return decorated
    return decorator


def init_default_admin():
    """
    Create a default admin user if no users exist.
    Password is read from ADMIN_DEFAULT_PASSWORD env var, or defaults to 'admin123'.
    """
    with get_session() as session:
        if session.query(User).count() > 0:
            return  # users already exist

    default_password = os.getenv("ADMIN_DEFAULT_PASSWORD", "admin123")
    result = create_user(
        username="admin",
        password=default_password,
        role="admin",
        email="admin@drishti.local",
    )
    if "error" not in result:
        logger.info("Default admin user created (username: admin)")
    else:
        logger.warning(f"Failed to create default admin: {result['error']}")
