# Drishti Dark Web OSINT Platform - Architecture Analysis

## Overview
Drishti is an AI-powered dark web OSINT (Open Source Intelligence) platform designed for cybersecurity investigators and law enforcement agencies. The platform combines dark web search, artifact extraction, LLM-powered analysis, and visualization into a cohesive tool.

## System Architecture

### High-Level Components

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend (React)                         │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │ Search   │ │ Crawl    │ │ History  │ │ Batch    │       │
│  │ Mode     │ │ Mode     │ │ Mode     │ │ Mode     │       │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Graph Visualization                    │   │
│  └─────────────────────────────────────────────────────┘   │
└───────────────────────────┬─────────────────────────────────┘
                            │ HTTP/WebSocket
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                     Backend (Flask)                          │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │ API      │ │ Search   │ │ Scrape   │ │ LLM      │       │
│  │ Layer    │ │ Engine   │ │ Engine   │ │ Layer    │       │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │ Artifact │ │ Graph    │ │ Export   │ │ Tor      │       │
│  │ Extractor│ │ Builder  │ │ Engine   │ │ Manager  │       │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
└───────────────────────────┬─────────────────────────────────┘
                            │ Tor Network / HTTP
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                     External Services                        │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │ Tor      │ │ Dark Web │ │ Pastebin │ │ GitHub   │       │
│  │ Network  │ │ Search   │ │          │ │          │       │
│  │          │ │ Engines  │ │          │ │          │       │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
│  ┌──────────┐ ┌──────────┐                                 │
│  │ Virus-   │ │ Abuse-   │                                 │
│  │ Total    │ │ IPDB     │                                 │
│  └──────────┘ └──────────┘                                 │
└─────────────────────────────────────────────────────────────┘
```

## Data Flow Pipeline

### Standard Investigation Pipeline
1. **User Query** → HTTP GET `/investigate`
2. **Query Refinement** → `llm.refine_query()` (LLM rewrites/expands query)
3. **Search Execution** → `search.get_search_results()` (15+ Tor search engines)
4. **Result Filtering** → `llm.filter_results()` (LLM selects top 20 results)
5. **Content Scraping** → `scrape.scrape_multiple()` (fetch pages via Tor)
6. **Artifact Extraction** → `artifact_extractor.extract()` (19 IOC types)
7. **Report Generation** → `llm.generate_summary()` (LLM creates intelligence report)
8. **Output Writing** → Markdown/HTML/CSV/JSON/STIX 2.1 formats

### Alternative Flows
- **Deep Crawl Mode**: Recursive crawling of target URLs (up to depth 2, 20 pages)
- **Batch Mode**: Process up to 50 queries asynchronously
- **History Mode**: Retrieve and re-analyze previous investigations

## Backend Module Architecture

### Core Modules
1. **`app.py`** - Flask application with REST API endpoints
2. **`search.py`** - Multi-engine dark web search with failover
3. **`scrape.py`** / **`async_scraper.py`** - Page fetching and HTML extraction
4. **`llm.py`** - LLM integration (OpenAI, Anthropic, Google, Ollama, etc.)
5. **`artifact_extractor.py`** - Regex-based IOC extraction (19 artifact types)
6. **`enrichment.py`** - IOC reputation enrichment (VirusTotal, AbuseIPDB)
7. **`graph_builder.py`** - Entity relationship graph construction
8. **`exporter.py`** - Multi-format report export
9. **`tor_manager.py`** - Tor circuit management and rotation
10. **`deep_crawl.py`** - Recursive URL crawling
11. **`config.py`** - Configuration management

### Supporting Modules
- **`llm_utils.py`** - LLM utility functions
- **`output_schemas.py`** - Pydantic schemas for output validation
- **`output_validators.py`** - Output validation logic
- **`prompt_manager.py`** - LLM prompt management
- **`clearnet_search.py`** - Pastebin/GitHub OSINT integration

## Frontend Architecture

### Component Structure
- **`App.jsx`** - Main application container with tab management
- **`Sidebar.jsx`** - Navigation sidebar with mode selection
- **`SearchMode.jsx`** - Primary search interface
- **`CrawlMode.jsx`** - Deep crawl interface
- **`HistoryMode.jsx`** - Investigation history viewer
- **`BatchMode.jsx`** - Batch query processing interface
- **`GraphView.jsx`** - Interactive entity relationship visualization
- **`ArtifactsViewer.jsx`** - Extracted IOC display
- **`ReportView.jsx`** - LLM-generated report viewer
- **`TorStatus.jsx`** - Tor connection status indicator
- **`ConnectionStatus.jsx`** - Backend connectivity status
- **`ExportControls.jsx`** - Report export controls
- **`Terminal.jsx`** - Real-time progress terminal
- **`Toast.jsx`** - Notification system
- **`ErrorBoundary.jsx`** - React error boundary
- **`LoadingSkeleton.jsx`** - Loading state components

### Styling
- CSS modules organized in `src/styles/`
- Modern gradient-based design with dark theme
- Responsive layout for investigative workflows

## Deployment Architecture

### Docker Compose Setup
```
drishti-tor (dperson/torproxy)  - Tor SOCKS5 proxy (9050/9051)
backend (custom Flask app)      - Python backend API
frontend (Vite build)           - React frontend (served by Flask)
```

### Key Configuration
- **Tor Proxy**: SOCKS5 on 127.0.0.1:9050 for all .onion requests
- **API Endpoints**: Flask runs on 0.0.0.0:5000 by default
- **Output Storage**: `outputs/` directory for investigation reports
- **Logging**: Structured logging to `logs/drishti.log`

## Dependencies

### Backend Dependencies
- **Web Framework**: Flask >=2.0.0
- **LLM Integration**: LangChain (OpenAI, Anthropic, Google, HuggingFace, Ollama)
- **Web Scraping**: BeautifulSoup4, requests, aiohttp, aiohttp-socks
- **Tor Integration**: stem, pysocks
- **Data Processing**: pydantic >=2.0.0, cachetools >=5.0.0
- **Graph Processing**: networkx >=3.0
- **Environment**: python-dotenv

### Frontend Dependencies
- **UI Framework**: React 19.2.0
- **Styling**: CSS Modules
- **Animations**: framer-motion
- **Icons**: lucide-react
- **Markdown**: react-markdown
- **Syntax Highlighting**: react-syntax-highlighter
- **Build Tool**: Vite 7.2.4

## Key Features Implementation Status

Based on `IMPLEMENTATION_STATUS.md`:
- ✅ Enhanced Search Resilience & Failover
- ✅ Expanded Artifact Extraction & Validation  
- ✅ IOC Reputation Enrichment (VirusTotal, AbuseIPDB)
- ✅ Deep Crawl Mode
- ✅ Entity Relationship Graph
- ✅ Batch Investigation Mode
- ✅ Multi-Format Report Export
- ✅ Tor Circuit Management
- ✅ LLM-Generated Intelligence Summaries

## Security & Compliance Considerations

### Legal Framework Alignment
- **India**: IT Act 2000 (Sections 43A, 65B, 69B, 70B, 79A)
- **International**: Budapest Convention, INTERPOL guidelines, Europol SIENA
- **Standards**: NIST SP 800-61, MITRE ATT&CK, ISO/IEC 27037
- **Financial**: FATF Recommendation 15, FinCEN guidance

### Operational Security
- Tor circuit rotation for anonymity
- Configurable request timeouts and retries
- Health monitoring for search engines
- Secure API key management via environment variables

## Scalability Considerations

### Current Limitations
- In-memory job tracking for batch mode
- File-based output storage
- Single-instance Flask application

### Potential Enhancements
- Redis for job queue and caching
- PostgreSQL for investigation history
- Horizontal scaling with load balancer
- Cloud storage for investigation reports
- Message queue for async processing

## Development & Testing

### Testing Structure
- `backend/tests/` - Comprehensive test suite
- Unit tests for all major modules
- Integration tests for API endpoints
- Mock external services for reliable testing

### Build & Deployment
- Docker Compose for local development
- Vite for frontend bundling
- Environment-based configuration
- Health checks for Tor proxy