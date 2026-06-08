import os
from dotenv import load_dotenv

load_dotenv()

# ===== API Keys =====
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
NVIDIA_NIM_API_KEY = os.getenv("NVIDIA_NIM_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
VIRUSTOTAL_API_KEY = os.getenv("VIRUSTOTAL_API_KEY")
ABUSEIPDB_API_KEY = os.getenv("ABUSEIPDB_API_KEY")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# ===== Search Configuration =====
SEARCH_ENGINE_COOLDOWN_MINUTES = int(os.getenv("SEARCH_ENGINE_COOLDOWN_MINUTES", 5))
SEARCH_ENGINE_MAX_FAILURES = int(os.getenv("SEARCH_ENGINE_MAX_FAILURES", 3))
SEARCH_REQUEST_TIMEOUT = int(os.getenv("SEARCH_REQUEST_TIMEOUT", 30))
SEARCH_RESULT_LIMIT = int(os.getenv("SEARCH_RESULT_LIMIT", 50))
# Use stub results when no search engines are available (for local testing/demo)
SEARCH_STUB_RESULTS_ENABLED = os.getenv("SEARCH_STUB_RESULTS_ENABLED", "false").lower() == "true"

# ===== Scraping Configuration =====
SCRAPE_REQUEST_TIMEOUT = int(os.getenv("SCRAPE_REQUEST_TIMEOUT", 30))
SCRAPE_MAX_WORKERS = int(os.getenv("SCRAPE_MAX_WORKERS", 5))
SCRAPE_MAX_CHARS = int(os.getenv("SCRAPE_MAX_CHARS", 50000))

# ===== Deep Crawl Configuration =====
CRAWL_MAX_DEPTH = int(os.getenv("CRAWL_MAX_DEPTH", 2))
CRAWL_MAX_PAGES = int(os.getenv("CRAWL_MAX_PAGES", 20))
CRAWL_REQUEST_TIMEOUT = int(os.getenv("CRAWL_REQUEST_TIMEOUT", 60))

# ===== Artifact Extraction Configuration =====
ARTIFACT_CONTEXT_WINDOW = int(os.getenv("ARTIFACT_CONTEXT_WINDOW", 50))
ARTIFACT_DEDUP_ENABLED = os.getenv("ARTIFACT_DEDUP_ENABLED", "true").lower() == "true"

# ===== LLM Configuration =====
LLM_CACHE_ENABLED = os.getenv("LLM_CACHE_ENABLED", "true").lower() == "true"
LLM_CACHE_MAX_SIZE = int(os.getenv("LLM_CACHE_MAX_SIZE", 1000))
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", 0.0))
LLM_STREAMING_ENABLED = os.getenv("LLM_STREAMING_ENABLED", "true").lower() == "true"

# ===== Flask Configuration =====
FLASK_DEBUG = os.getenv("FLASK_DEBUG", "false").lower() == "true"
FLASK_PORT = int(os.getenv("FLASK_PORT", 5000))
FLASK_HOST = os.getenv("FLASK_HOST", "0.0.0.0")

# ===== Logging Configuration =====
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", "logs/drishti.log")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# ===== Proxy Configuration =====
TOR_PROXY_HOST = os.getenv("TOR_PROXY_HOST", "127.0.0.1")
TOR_PROXY_PORT = int(os.getenv("TOR_PROXY_PORT", 9050))
TOR_CONTROL_PORT = int(os.getenv("TOR_CONTROL_PORT", 9051))
TOR_CONTROL_PASSWORD = os.getenv("TOR_CONTROL_PASSWORD")

# ===== Output Configuration =====
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "outputs")
REPORT_FORMAT = os.getenv("REPORT_FORMAT", "markdown")  # markdown, json, csv

# ===== Database Configuration =====
DATABASE_URL = os.getenv("DATABASE_URL")  # None → SQLite default; set to postgres:// for production

# ===== Authentication Configuration =====
AUTH_ENABLED = os.getenv("AUTH_ENABLED", "false").lower() == "true"
AUTH_SECRET_KEY = os.getenv("AUTH_SECRET_KEY", "drishti-dev-secret-change-in-production")
AUTH_TOKEN_EXPIRY_MINUTES = int(os.getenv("AUTH_TOKEN_EXPIRY_MINUTES", 60))
AUTH_REFRESH_TOKEN_EXPIRY_DAYS = int(os.getenv("AUTH_REFRESH_TOKEN_EXPIRY_DAYS", 7))

# ===== Security Configuration =====
RATE_LIMIT_DEFAULT = os.getenv("RATE_LIMIT_DEFAULT", "60/minute")
RATE_LIMIT_INVESTIGATE = os.getenv("RATE_LIMIT_INVESTIGATE", "10/minute")
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*")  # comma-separated; use specific origins in production

# ===== Feature Flags =====
ENABLE_DEEP_CRAWL = os.getenv("ENABLE_DEEP_CRAWL", "true").lower() == "true"
ENABLE_ARTIFACT_EXTRACTION = os.getenv("ENABLE_ARTIFACT_EXTRACTION", "true").lower() == "true"
ENABLE_CACHING = os.getenv("ENABLE_CACHING", "true").lower() == "true"

# ===== Future Feature Keys (Phase 3+) =====
TELEGRAM_API_ID = os.getenv("TELEGRAM_API_ID")
TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH")
SHODAN_API_KEY = os.getenv("SHODAN_API_KEY")
CENSYS_API_ID = os.getenv("CENSYS_API_ID")
CENSYS_API_SECRET = os.getenv("CENSYS_API_SECRET")

# ===== Drishti Upgraded Configs =====
SEVERITY_WEIGHTS = {
    "ioc_reputation": float(os.getenv("SEVERITY_WEIGHT_IOC", 0.35)),
    "keyword_match": float(os.getenv("SEVERITY_WEIGHT_KEYWORD", 0.25)),
    "mitre_ttp": float(os.getenv("SEVERITY_WEIGHT_MITRE", 0.20)),
    "source_credibility": float(os.getenv("SEVERITY_WEIGHT_CREDIBILITY", 0.10)),
    "recency": float(os.getenv("SEVERITY_WEIGHT_RECENCY", 0.10))
}

WATCHLIST_DB_PATH = os.getenv("WATCHLIST_DB_PATH")

ALERT_WEBHOOK_URL = os.getenv("ALERT_WEBHOOK_URL")
ALERT_SLACK_URL = os.getenv("ALERT_SLACK_URL")

ALERT_SMTP_HOST = os.getenv("ALERT_SMTP_HOST")
ALERT_SMTP_PORT = os.getenv("ALERT_SMTP_PORT")
ALERT_SMTP_USER = os.getenv("ALERT_SMTP_USER")
ALERT_SMTP_PASSWORD = os.getenv("ALERT_SMTP_PASSWORD")
ALERT_SMTP_FROM = os.getenv("ALERT_SMTP_FROM")

BLOCKCHAIN_ENABLED = os.getenv("BLOCKCHAIN_ENABLED", "false").lower() == "true"
POLYGON_RPC_URL = os.getenv("POLYGON_RPC_URL")
WALLET_PRIVATE_KEY = os.getenv("WALLET_PRIVATE_KEY")

SUPPORTED_LANGUAGES = ["en", "hi", "ru", "ar"]

