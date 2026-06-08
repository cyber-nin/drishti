"""
Tor connection manager.
- Auto-detects if Tor is already running on 9050
- Auto-launches Tor process if not running (searches common install paths)
- Provides health check, circuit rotation, and status reporting
"""
import os
import time
import socket
import logging
import threading
import subprocess
from datetime import datetime, timezone

# Suppress stem's noisy Windows socket cleanup messages before anything imports stem
logging.getLogger('stem').setLevel(logging.WARNING)
logging.getLogger('stem.control').setLevel(logging.WARNING)
logging.getLogger('stem.socket').setLevel(logging.WARNING)

try:
    from backend.config import TOR_PROXY_HOST, TOR_PROXY_PORT, TOR_CONTROL_PORT, TOR_CONTROL_PASSWORD
except ModuleNotFoundError:
    from config import TOR_PROXY_HOST, TOR_PROXY_PORT, TOR_CONTROL_PORT, TOR_CONTROL_PASSWORD

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_launch_lock = threading.Lock()          # separate lock to prevent concurrent launches
_request_count = 0
_rotation_interval = 10
_tor_process = None  # subprocess.Popen handle if we launched Tor ourselves

# ── stem availability ─────────────────────────────────────────────────────────
_stem_available = False
try:
    from stem import Signal
    from stem.control import Controller
    _stem_available = True
except ImportError:
    pass

# ── Tor executable search paths (Windows + Linux) ────────────────────────────
_TOR_PATHS = [
    # Generic Expert Bundle pattern in Downloads — resolved at runtime via {user}
    r"C:\Users\{user}\Downloads\tor-expert-bundle-windows-x86_64-15.0.8\tor\tor.exe",
    r"C:\Users\{user}\Downloads\tor-expert-bundle-windows-x86_64-14.0\tor\tor.exe",
    r"C:\Users\{user}\Downloads\tor-expert-bundle-windows-x86_64-13.0\tor\tor.exe",
    r"C:\Users\{user}\Downloads\tor\tor.exe",
    r"C:\Users\{user}\Desktop\tor\tor.exe",
    # Common manual extraction paths
    r"C:\tor\tor.exe",
    r"C:\tor\Tor\tor.exe",
    r"C:\Tools\tor\tor.exe",
    # Tor Browser bundle
    r"C:\Users\{user}\Desktop\Tor Browser\Browser\TorBrowser\Tor\tor.exe",
    r"C:\Program Files\Tor Browser\Browser\TorBrowser\Tor\tor.exe",
    # Linux / macOS
    "/usr/bin/tor",
    "/usr/local/bin/tor",
    "/opt/homebrew/bin/tor",
]


def _resolve_paths():
    import glob
    user = os.environ.get("USERNAME") or os.environ.get("USER") or ""
    paths = [p.replace("{user}", user) for p in _TOR_PATHS]

    # Glob search for any Expert Bundle version in Downloads
    downloads = os.path.expanduser("~/Downloads")
    for match in glob.glob(os.path.join(downloads, "tor-expert-bundle-*", "tor", "tor.exe")):
        if match not in paths:
            paths.insert(0, match)  # highest priority

    return paths


def _find_tor_executable() -> str | None:
    """Find tor binary on this system."""
    for path in _resolve_paths():
        if os.path.isfile(path):
            return path
    # Also try PATH
    import shutil
    return shutil.which("tor")


# ── Core status functions ─────────────────────────────────────────────────────

def is_tor_running() -> bool:
    """Check if Tor SOCKS proxy is accepting connections on port 9050."""
    try:
        with socket.create_connection((TOR_PROXY_HOST, TOR_PROXY_PORT), timeout=3):
            return True
    except (ConnectionRefusedError, OSError, TimeoutError):
        return False


def get_tor_ip() -> str | None:
    """
    Get the current exit node IP via Tor.
    Returns IP string or None if Tor is not reachable.
    """
    try:
        import requests
        proxies = get_proxies()
        r = requests.get(
            "https://check.torproject.org/api/ip",
            proxies=proxies,
            timeout=15
        )
        if r.status_code == 200:
            data = r.json()
            if data.get("IsTor"):
                return data.get("IP")
    except Exception as e:
        logger.debug(f"Tor IP check failed: {e}")
    return None


def get_status() -> dict:
    """Return full Tor status dict for the /tor/status endpoint."""
    running = is_tor_running()
    return {
        "running": running,
        "host": TOR_PROXY_HOST,
        "port": TOR_PROXY_PORT,
        "stem_available": _stem_available,
        "auto_launched": _tor_process is not None,
        "executable": _find_tor_executable(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ── Launch Tor ────────────────────────────────────────────────────────────────

def launch_tor() -> dict:
    """
    Try to launch Tor automatically.
    Returns {"success": bool, "message": str}
    """
    global _tor_process

    with _launch_lock:
        return _launch_tor_locked()


def _launch_tor_locked() -> dict:
    """Inner launch logic — must be called with _launch_lock held."""
    global _tor_process

    if is_tor_running():
        return {"success": True, "message": "Tor is already running on port 9050."}

    exe = _find_tor_executable()
    if not exe:
        return {
            "success": False,
            "message": (
                "Tor executable not found. Please install Tor:\n"
                "• Windows: Download Tor Expert Bundle from https://www.torproject.org/download/tor/\n"
                "• Linux: sudo apt install tor\n"
                "• macOS: brew install tor"
            )
        }

    try:
        tor_dir = os.path.dirname(os.path.abspath(exe))

        # Place torrc inside the tor_dir itself to avoid permission issues
        # when tor.exe is at C:\tor\tor.exe, torrc goes to C:\tor\torrc
        torrc = os.path.join(tor_dir, 'torrc')

        # Write torrc if it doesn't exist or doesn't have ControlPort
        needs_write = True
        if os.path.exists(torrc):
            with open(torrc, 'r') as f:
                if 'ControlPort' in f.read():
                    needs_write = False

        if needs_write:
            data_dir = os.path.join(tor_dir, 'data')
            os.makedirs(data_dir, exist_ok=True)
            with open(torrc, 'w') as f:
                f.write(
                    f"SocksPort 9050\n"
                    f"ControlPort 9051\n"
                    f"CookieAuthentication 0\n"
                    f"DataDirectory {data_dir}\n"
                    f"Log notice stdout\n"
                )
            logger.info(f"Wrote torrc to {torrc}")

        cmd = [exe, '-f', torrc]
        logger.info(f"Launching Tor: {' '.join(cmd)}")
        _tor_process = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )

        # Wait up to 30 seconds for Tor to bootstrap
        for i in range(30):
            time.sleep(1)
            if is_tor_running():
                logger.info(f"Tor started successfully after {i+1}s")
                return {"success": True, "message": f"Tor started successfully (took {i+1}s to bootstrap)."}

        _tor_process.terminate()
        _tor_process = None
        return {"success": False, "message": "Tor process started but did not open port 9050 within 30 seconds."}

    except Exception as e:
        logger.error(f"Failed to launch Tor: {e}")
        return {"success": False, "message": f"Failed to launch Tor: {str(e)}"}


def stop_tor() -> dict:
    """Stop the Tor process if we launched it."""
    global _tor_process
    with _launch_lock:
        if _tor_process is None:
            return {
                "success": False,
                "message": "Tor was not launched by Drishti — stop it manually via Task Manager or 'taskkill /IM tor.exe'."
            }
        try:
            _tor_process.terminate()
            _tor_process = None
            return {"success": True, "message": "Tor process stopped."}
        except Exception as e:
            return {"success": False, "message": str(e)}


# ── Proxy helpers ────────────────────────────────────────────────────────────
def get_proxies() -> dict:
    return {
        "http":  f"socks5h://{TOR_PROXY_HOST}:{TOR_PROXY_PORT}",
        "https": f"socks5h://{TOR_PROXY_HOST}:{TOR_PROXY_PORT}",
    }


def rotate_circuit() -> bool:
    if not _stem_available:
        logger.debug("Circuit rotation skipped: stem library not installed. Run: pip install stem")
        return False
    try:
        password = TOR_CONTROL_PASSWORD or None
        with Controller.from_port(port=TOR_CONTROL_PORT) as controller:
            controller.authenticate(password=password)
            controller.signal(Signal.NEWNYM)
            time.sleep(1)
            logger.info("Tor circuit rotated")
            return True
    except Exception as e:
        # Ignore Windows socket cleanup error after NEWNYM — rotation succeeded
        if "10038" in str(e) or "SocketClosed" in str(e) or "closed file" in str(e):
            logger.info("Tor circuit rotated (socket cleanup noise ignored)")
            return True
        logger.warning(f"Circuit rotation failed: {e}")
        return False


def get_proxies_and_rotate_if_needed() -> dict:
    global _request_count
    with _lock:
        _request_count += 1
        if _request_count >= _rotation_interval:
            _request_count = 0
            rotate_circuit()
    return get_proxies()


def is_stem_available() -> bool:
    return _stem_available
