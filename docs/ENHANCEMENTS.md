# Drishti Dark Web OSINT Platform Enhancement Plan

## 1. Executive summary

This document describes a prioritized, in-depth roadmap to enhance the core capabilities of the Drishti dark web OSINT platform.

Goals:
- Increase data coverage, reliability, and relevance.
- Reduce hallucination and improve structured intelligence outputs.
- Harden safety, operators, and compliance.
- Improve maintainability and extensibility.

---

## 2. Current baseline architecture

### 2.1 Pipeline

1. User query (HTTP GET `/investigate`)
2. `llm.refine_query` (query rewriting)
3. `search.get_search_results` (multiple Tor onion search engines)
4. `llm.filter_results` (LLM-based top20 selection)
5. `scrape.scrape_multiple` (page fetch + HTML text extraction)
6. `artifact_extractor.extract` (regex IOCs)
7. `llm.generate_summary` (report generation)
8. Write markdown to `outputs/`.

### 2.2 Existing tooling

- Flask backend API (`app.py`)
- Tor-oriented scraping/search (`requests`, `BeautifulSoup`, system Tor proxy 127.0.0.1:9050)
- Langchain wrappers for LLMs (`langchain_openai`, `langchain_anthropic`, etc.)
- Deep crawl module with same regex intelligence extraction
- Minimal config in `config.py`

---

## 3. Priority enhancements (deep design and execution plan)

### 3.1 Search and sourcing core

#### 3.1.1. Soft-fail resilient search aggregator

- Problem: single-hop fail over chain; no endpoint health logic.
- Design changes:
  - Add per-engine health status tracking (up/down, latency, failure count) in `search.py`.
  - Query a “search pool” with dynamic weight based on reliability.
  - Add retries with exponential backoff for 5xx/timeouts.
- Implementation steps:
  1. Add in-memory `SEARCH_ENGINE_STATUS = {endpoint: {'ok': True, 'failures':0, 'last_seen': datetime}}`.
  2. Add util `select_endpoints(max_n)`.
  3. Update `fetch_search_results` to return exceptions with context.
  4. Add `get_search_results` logic to remove dead engines and recover after cooldown.
- Tech stack: Python `concurrent.futures`, `tenacity` (optional), `requests`, `logging`.
- Benefit:
  - Improved consistency and no single-point outages, better uptime.
  - More usable in production ops with ephemeral onion search sources.

#### 3.1.2. Multi-source, multi-protocol crawl (beyond Tor search engines)

- Problem: only onion indexers.
- Design:
  - Add plug-in adapter model in `search/` for source types (`onion_search`, `clearnet_osint`, `pastebin`, `social`) in a strategy pattern.
  - Include source of truth metadata for each result (source, indexing date, confidence).
- Implementation steps:
  1. Create class `BaseSearchAdapter` and adapters per source.
  2. Add configuration in YAML/JSON `sources.yaml` (enabled, weight, rate limit).
  3. Add `search.sources` module using `importlib` to load adapters.
  4. Create tests for each adapter.
- Tech stack: Python plugin architecture, `aiohttp` for async, existing `requests` for legacy.
- Benefit:
  - Larger and fresher coverage, cross-correlation with open web and dark web.

#### 3.1.3. TOR circuit rotation and proxy pool

- Problem: hard-coded single Tor endpoint; no IP rotation.
- Design:
  - Add library support for Tor control protocol (`stem`), ephemeral stream circuit rotation.
  - Manage multiple Tor processes using `stem.control.Controller` / optional docker containerized tor.
- Implementation steps:
  1. Add `tor_manager.py` with rate-limit and rotate API.
  2. In each request path, call `tor_manager.get_proxies()` and `tor_manager.rotate_if_needed()`.
  3. Add circuit health poller.
- Tech stack: `stem`, `requests[socks]`.
- Benefits:
  - reduced blocking, better reliability for crawling gated dark web sites.

---

### 3.2 LLM workflow, prompt engineering, and validation

#### 3.2.1. Structured LLM output using schema + parsing

- Problem: free-text LLM results are fragile, hallucination-prone.
- Design:
  - Use schema defined in JSON (Pydantic models) for all LLM outputs: `query_refinement`, `result_ranking`, `investigation_summary`.
  - Use `langchain_core.output_parsers` or custom parser to enforce schema and provide deterministic fields.
- Implementation steps:
  1. Create `models/llm_schema.py`: `QueryRefinement`, `FilterResult`, `Summary` Pydantic classes.
  2. Create prompt wrappers in `llm.py` to include explicit JSON output instructions, error checking, and fallback to retries.
  3. Parse output through `json.loads` + Pydantic validation; on failure re-prompt with “repair” mechanism.
  4. Test with mocked model output.
- Tech stack: `pydantic`, `langchain` parser, `jsonschema` optional.
- Benefits:
  - structured internal state, safer to chain, easier to triage bugs.
  - simplified downstream data consumers and UIs.

#### 3.2.2. Consistent prompt engineering + prompt versioning

- Problem: hard-coded prompt text in functions.
- Design:
  - Externalize prompts to `prompts/` folder with templates and metadata (purpose, last_updated, version).
  - Add `prompts/prompt_manager.py` to load and render with variables.
- Implementation steps:
  1. Create `prompts/refine_query.prompt.md`, `prompts/filter_results.prompt.md`, `prompts/summary.prompt.md` with sections.
  2. In `llm.py`, load via prompt manager and supply parameters.
  3. Add a prompt benchmark script for evaluating LLM output quality.
- Tech stack: YAML/Markdown-based prompts, pure Python.
- Benefit:
  - easier review by security teams, rapid tuning and A/B tests.

#### 3.2.3. Cost-efficient model fallback + caching

- Problem: always expensive, no caching, no fallback.
- Design:
  - Add in-memory LRU cache for query results and summary generation (with TTL), using `cachetools`.
  - Add `llm_utils` policy for model tiers (local/gpu vs commercial), auto-fallback.
- Implementation steps:
  1. Add `cache = TTLCache(maxsize=1000, ttl=86400)` in `llm.py`.
  2. Wrap `refine_query` + `filter_results` + `generate_summary` with cache key from inputs.
  3. Add `ModelPriority` ordering in config and fallback on failures.
- Tech stack: `cachetools`, `functools.lru_cache`, `Redis` optional for shared state.
- Benefit:
  - operational cost reduction and faster replays / reproducibility.

---

### 3.3 Extraction, correlation, and enrichment

#### 3.3.1 Expanded IOC extraction and false positive filtering

- Problem: limited to basic patterns (email, crypto, IP). prone to FP.
- Design:
  - Add extraction for: software hashes (MD5/SHA1/SHA256), UUIDs, CVE IDs, URLs with  phishing patterns, credit card token patterns, screenshots / JWTs.
  - Use normalization/validation for each IOC type (e.g., crypto checksum, domain heuristics, IP reserved range filtering).
- Implementation steps:
  1. Extend `ArtifactExtractor.patterns` and validation functions in `artifact_extractor.py`.
  2. Add enrichment with third-party breach DBs + IOC reputation sources.
  3. Add configurable context window (n words before/after artifact) for “artifact context” output.
- Tech stack: `validators`, `tldextract`, `pyasn1` etc.
- Benefit:
  - higher accuracy and actionable artifacts to feed to SOC pipelines.

#### 3.3.2 Graph-based entity clustering and relationship analysis

- Problem: each artifact siloed per source.
- Design:
  - Build a graph in memory (NetworkX / Neo4j / RedisGraph) linking queries, URLs, artifacts, threat actor labels.
  - Support scoring by frequency/time and threat relevance.
- Implementation steps:
  1. Add `analysis/graph_builder.py` to ingest artifacts and produce nodes/edges.
  2. Enrich with TTP mapping from MITRE ATT&CK.
  3. Hard-coded 