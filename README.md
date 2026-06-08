# Drishti - Dark Web Intelligence Platform

> **Drishti** (दृष्टि) means *vision* or *insight* in Hindi — a platform built to illuminate the hidden corners of the internet and empower investigators with actionable intelligence.

[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-passing-brightgreen)](backend/tests/)

Drishti is an AI-powered dark web OSINT (Open Source Intelligence) platform designed for cybersecurity professionals, law enforcement, and threat intelligence analysts. It combines multi-engine dark web search, AI-powered query refinement, automated artifact extraction, and real-time IOC enrichment into a single cohesive platform.

## 🚀 Features

### 🔍 AI-Powered Query Refinement
- Intelligently refines and expands search queries using LLMs before searching
- Supports multiple LLM backends: GPT-4.1, Claude Sonnet, Gemini 2.5, DeepSeek R1, and local models via Ollama (Llama 3.1, Llama 3.2, Gemma 3)
- Reduces noise and irrelevant results from the start

### 🌐 Multi-Engine Dark Web Search
- Queries **15 dark web search engines simultaneously** over Tor network
- Resilient failover with health tracking and automatic recovery
- Circuit breaker pattern prevents wasted time on dead endpoints
- Includes: Ahmia, OnionLand, Tor66, Excavator, Torgle, and more

### 📊 Clearnet OSINT Integration
- Automatically supplements results with open-web intelligence from **Pastebin** and **GitHub**
- Catches leaked credentials, API keys, and malware samples
- Deduplication ensures clean, non-redundant result sets

### 🛡️ Comprehensive IOC Artifact Extraction
- Extracts **19 types of Indicators of Compromise (IOCs)** from every page:
  - **Identity**: Email addresses, Phone numbers, Telegram handles
  - **Network**: IPv4 addresses (with reserved range filtering), Domains, Onion URLs
  - **Cryptocurrency**: Bitcoin (BTC), Ethereum (ETH), Monero (XMR), Litecoin (LTC)
  - **File Intelligence**: MD5, SHA1, SHA256 hashes
  - **Vulnerability**: CVE identifiers
  - **Credentials & Secrets**: JWT tokens, AWS access keys, API keys

### 📈 IOC Reputation Enrichment
- Real-time reputation data from **VirusTotal** and **AbuseIPDB**
- Malicious detection counts, abuse confidence scores, country attribution
- Saves hours of manual lookups during time-sensitive investigations

### 🖥️ Dual Interface
- **CLI Mode**: Command-line interface for automated workflows and scripting
- **Web UI**: Modern React-based interface with real-time progress tracking

## 📋 Prerequisites

- **Python 3.9+** (3.14.3 tested)
- **Node.js 18+** (for frontend)
- **Tor Proxy** (running locally or via Docker)
- **API Keys** (optional, for enhanced features):
  - OpenAI, Google, Anthropic, DeepSeek, HuggingFace, Groq (for LLMs)
  - VirusTotal, AbuseIPDB (for IOC enrichment)

## 🛠️ Installation

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/drishti-darkweb.git
cd drishti-darkweb
```

### 2. Backend Setup
```bash
cd backend
pip install -r requirements.txt
```

### 3. Frontend Setup
```bash
cd ../frontend
npm install
```

### 4. Environment Configuration
Copy the example environment file and configure your settings:
```bash
cp .env.example .env
# Edit .env with your API keys and preferences
```

### 5. Start Tor Proxy (Docker)
```bash
docker-compose up -d tor
```

## 🚀 Quick Start

### CLI Mode
```bash
# Basic search
python run.py -q "ransomware payments" -m llama3.2

# With more threads and verbose output
python run.py -q "data breach" -m gemma3 -t 12 -v

# Save output to specific file
python run.py -q "zero days" -o investigation_report
```

### Web UI Mode
```bash
# Start backend server
cd backend
python -m app

# In another terminal, start frontend dev server
cd frontend
npm run dev
```

Access the web interface at `http://localhost:5173`

### Docker Deployment
```bash
# Start full stack (Tor + Backend + Frontend)
docker-compose up -d
```

## 📁 Project Structure

```
drishti-darkweb/
├── backend/                 # Python Flask backend
│   ├── app.py              # Flask API server
│   ├── main.py             # CLI entry point
│   ├── search.py           # Multi-engine search
│   ├── scrape.py           # Web scraping utilities
│   ├── llm.py              # LLM integration
│   ├── artifact_extractor.py # IOC extraction
│   ├── enrichment.py       # IOC reputation enrichment
│   ├── config.py           # Configuration management
│   └── tests/              # Test suite
├── frontend/               # React frontend
│   ├── src/
│   │   ├── components/     # React components
│   │   ├── hooks/         # Custom React hooks
│   │   └── styles/        # CSS modules
│   └── vite.config.js     # Vite configuration
├── outputs/               # Generated intelligence reports
├── logs/                  # Application logs
├── docker-compose.yml     # Docker orchestration
├── .env.example          # Environment template
└── README.md             # This file
```

## 🔧 Configuration

Key environment variables (see `.env.example` for complete list):

```bash
# LLM API Keys (at least one required)
OPENAI_API_KEY=your_key
GOOGLE_API_KEY=your_key
ANTHROPIC_API_KEY=your_key
OLLAMA_BASE_URL=http://localhost:11434

# Enrichment API Keys
VIRUSTOTAL_API_KEY=your_key
ABUSEIPDB_API_KEY=your_key

# Search Configuration
SEARCH_ENGINE_COOLDOWN_MINUTES=5
SEARCH_REQUEST_TIMEOUT=30
SEARCH_RESULT_LIMIT=50

# Scraping Configuration
SCRAPE_MAX_WORKERS=5
SCRAPE_REQUEST_TIMEOUT=30

# Flask Configuration
FLASK_PORT=5000
FLASK_HOST=0.0.0.0
```

## 🧪 Testing

Run the test suite to verify installation:

```bash
cd backend
python -m pytest tests/ -v
```

All tests should pass. You may see warnings about thread cleanup during test teardown - these are harmless in test environment.

## 📊 Output Formats

Drishti generates comprehensive intelligence reports in multiple formats:

- **Markdown** (default): Human-readable summary with extracted artifacts
- **JSON**: Structured data for programmatic processing
- **CSV**: Tabular data for spreadsheet analysis
- **STIX 2.1**: Standardized threat intelligence format
- **HTML**: Interactive web report

## ⚖️ Legal & Compliance

Drishti is designed with legal frameworks in mind:

- **India**: Supports Section 69B of the Information Technology Act, 2000
- **International**: Aligns with Budapest Convention on Cybercrime
- **Law Enforcement**: Compatible with INTERPOL Cybercrime Directorate guidelines
- **Privacy**: Respects data protection regulations with configurable data retention

**Important**: Use Drishti only for authorized investigations and in compliance with applicable laws.

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines
- Write tests for new functionality
- Update documentation accordingly
- Follow existing code style
- Ensure all tests pass before submitting PR

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Tor Project** for providing anonymous communication
- **Search engine operators** for maintaining dark web search services
- **LLM providers** for AI capabilities
- **Threat intelligence platforms** (VirusTotal, AbuseIPDB) for enrichment data

## 📞 Support

For issues, questions, or feature requests:
- Open an issue on GitHub
- Check the [documentation](docs/DRISHTI_FEATURES.md)
- Review [implementation status](docs/IMPLEMENTATION_STATUS.md)

---

**Made with ❤️ by Paras Jangid**

*Drishti - Bringing light to the darkest corners of the web*