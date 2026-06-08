# Drishti — Feature Documentation

> **Drishti** (दृष्टि) means *vision* or *insight* in Hindi — a fitting name for a platform built to illuminate the hidden corners of the internet and empower investigators with actionable intelligence.

---

## Why Drishti Matters

Cybercrime, ransomware, data breaches, and dark web marketplaces pose a growing threat to individuals, organizations, and national security. Investigators need tools that are fast, intelligent, and legally sound. Drishti is purpose-built for exactly that — combining AI-powered analysis, automated artifact extraction, and resilient dark web search into a single, cohesive platform.

Whether you are a law enforcement officer, a cybersecurity analyst, or a threat intelligence professional, Drishti dramatically reduces the time from query to actionable intelligence.

---

## Core Features

### 1. AI-Powered Query Refinement

Drishti does not just take your search query and run it verbatim. It uses a Large Language Model (LLM) to intelligently refine and expand your query before searching, ensuring that the most relevant dark web content surfaces first.

**How it helps:**
- Investigators unfamiliar with dark web terminology get better results automatically.
- Reduces noise and irrelevant results from the start.
- Supports multiple LLM backends — GPT-4.1, Claude Sonnet, Gemini 2.5, DeepSeek R1, and local offline models via Ollama (Llama 3.1, Llama 3.2, Gemma 3).

**Relevant legal framework:**
- Supports the intelligence-gathering mandate under **Section 69B of the Information Technology Act, 2000 (India)**, which authorizes agencies to monitor and collect traffic data for cybersecurity purposes.
- Aligns with **INTERPOL's Cybercrime Directorate** guidelines on structured threat intelligence collection.

---

### 2. Multi-Engine Dark Web Search with Resilient Failover

Drishti queries **15 dark web search engines simultaneously** over the Tor network, including Ahmia, OnionLand, Tor66, Excavator, Torgle, and more. Its built-in health tracking system automatically detects when a search engine goes down and routes queries to healthy alternatives — with automatic recovery after a configurable cooldown period.

**How it helps:**
- No single point of failure — investigations continue even when individual Tor search engines are offline.
- Parallel querying across all engines dramatically increases coverage and speed.
- Circuit breaker pattern prevents wasted time on dead endpoints.

**Relevant legal framework:**
- Supports the **National Cyber Crime Reporting Portal (NCRP)** investigation workflows under the **Ministry of Home Affairs, India**.
- Consistent with **Budapest Convention on Cybercrime (Article 14–21)** provisions on expedited preservation and collection of computer data.

---

### 3. Clearnet OSINT Integration

Beyond the dark web, Drishti automatically supplements results with open-web intelligence from **Pastebin** and **GitHub** — two of the most common surfaces where leaked credentials, API keys, and malware samples are publicly exposed.

**How it helps:**
- A single investigation query covers both dark web and surface web simultaneously.
- Leaked credentials and source code exposures are caught alongside dark web chatter.
- Deduplication ensures clean, non-redundant result sets.

**Relevant legal framework:**
- Supports **CERT-In (Indian Computer Emergency Response Team)** incident response workflows under **Section 70B of the IT Act, 2000**.
- Aligns with **NIST SP 800-61** (Computer Security Incident Handling Guide) recommendations for comprehensive evidence collection.

---

### 4. Comprehensive IOC Artifact Extraction

Drishti automatically extracts **19 types of Indicators of Compromise (IOCs)** from every page it scrapes, with intelligent validation to minimize false positives:

| Category | Artifact Types |
|---|---|
| Identity | Email addresses, Phone numbers, Telegram handles |
| Network | IPv4 addresses (with reserved range filtering), Domains, Onion URLs, Full URLs |
| Cryptocurrency | Bitcoin (BTC), Ethereum (ETH), Monero (XMR), Litecoin (LTC) |
| File Intelligence | MD5, SHA1, SHA256 hashes |
| Vulnerability | CVE identifiers |
| Credentials & Secrets | JWT tokens, AWS access keys, API keys |

**How it helps:**
- Investigators get a structured, ready-to-use intelligence package from every search — no manual copy-pasting.
- Reserved IP ranges (127.x, 192.168.x, 10.x) are automatically filtered out, keeping results clean.
- Hash normalization ensures consistent cross-referencing with threat intelligence databases.

**Relevant legal framework:**
- Directly supports **Section 43A of the IT Act, 2000 (India)** investigations into data breaches involving sensitive personal data.
- Aligns with **MITRE ATT&CK Framework** IOC collection standards used globally by SOC teams.
- Supports **Financial Intelligence Unit-India (FIU-IND)** cryptocurrency transaction tracking requirements.

---

### 5. IOC Reputation Enrichment

Every extracted IP address, domain, and file hash can be automatically enriched with real-time reputation data from **VirusTotal** and **AbuseIPDB** — two of the world's most trusted threat intelligence platforms.

**How it helps:**
- Instantly know if an extracted IP has been flagged as malicious by dozens of security vendors.
- Abuse confidence scores and country attribution for IP addresses.
- Malicious and suspicious detection counts for domains and file hashes.
- Saves hours of manual lookups during time-sensitive investigations.

**Relevant legal framework:**
- Supports **CERT-In's Cyber Threat Intelligence (CTI) sharing** framework.
- Aligns with **EU NIS2 Directive** requirements for threat intelligence integration in incident response.
- Consistent with **FATF Recommendation 15** on virtual asset risk assessment, supporting AML investigations.

---

### 6. Deep Crawl Mode

When a specific dark web URL needs thorough investigation, Drishti's Deep Crawl mode goes beyond the surface. It recursively crawls a target site up to a configurable depth, visiting up to 50 pages, extracting all artifacts, discovering internal links, identifying JavaScript files, and mapping form structures.

**How it helps:**
- Uncovers hidden pages and subpages that a surface-level search would miss.
- Automatically handles both Tor (.onion) and clearnet URLs.
- Real-time progress streaming keeps investigators informed as the crawl proceeds.
- Discovers JS files and form structures useful for technical forensic analysis.

**Relevant legal framework:**
- Supports **Section 79A of the IT Act, 2000 (India)** — electronic evidence collection by authorized examiners.
- Aligns with **ACPO Good Practice Guide for Digital Evidence** (UK) principles of thoroughness and reproducibility.
- Consistent with **ISO/IEC 27037** guidelines for identification, collection, and preservation of digital evidence.

---

### 7. Entity Relationship Graph

Drishti builds an interactive visual graph that maps the relationships between your investigation query, source URLs, and all extracted artifacts. Shared artifacts across multiple sources are automatically correlated with cross-edges, revealing hidden connections between threat actors, infrastructure, and financial flows.

**How it helps:**
- Visually identify when the same Bitcoin address, email, or IP appears across multiple dark web sources — a strong indicator of a single threat actor.
- Color-coded nodes by artifact type make complex investigations immediately understandable.
- Exportable graph data for integration with external analysis tools.

**Relevant legal framework:**
- Supports **link analysis** methodologies recommended by **INTERPOL** and **Europol** for organized cybercrime investigations.
- Aligns with **FinCEN guidance** on cryptocurrency transaction graph analysis for money laundering investigations.
- Supports **NIA (National Investigation Agency, India)** structured analytical techniques for terrorism financing investigations.

---

### 8. Batch Investigation Mode

Investigators often need to run multiple queries simultaneously — tracking several threat actors, monitoring multiple keywords, or processing a list of suspects. Drishti's Batch Mode accepts up to **50 queries in a single API call**, processes them asynchronously in the background, and saves individual reports for each.

**How it helps:**
- Dramatically reduces investigation time for large-scale operations.
- Each query gets its own complete report with artifacts and LLM summary.
- Job status tracking lets investigators monitor progress in real time.
- Ideal for overnight bulk investigations or processing large intelligence backlogs.

**Relevant legal framework:**
- Supports **Operation-scale investigations** conducted by **CBI (Central Bureau of Investigation, India)** and **State Cyber Cells**.
- Aligns with **Europol's SIENA (Secure Information Exchange Network Application)** bulk intelligence processing workflows.

---

### 9. Multi-Format Report Export

Every investigation report can be exported in five formats, making Drishti's output compatible with virtually any downstream system:

| Format | Best For |
|---|---|
| **Markdown** | Internal documentation, GitHub, case notes |
| **HTML** | Standalone printable reports, court submissions |
| **CSV** | Spreadsheet analysis, case management system import |
| **JSON** | API integration, custom tooling, SIEM ingestion |
| **STIX 2.1** | Threat intelligence platform sharing (MISP, OpenCTI, ThreatConnect) |

**How it helps:**
- STIX 2.1 export enables direct sharing with partner agencies and threat intelligence platforms.
- HTML reports are self-contained, professionally styled, and print-ready for court documentation.
- CSV export integrates seamlessly with Excel, Google Sheets, and case management systems.
- All reports include timestamps, source URLs, and methodology — critical for chain of custody.

**Relevant legal framework:**
- HTML and Markdown reports support **admissibility requirements** under **Section 65B of the Indian Evidence Act, 1872** for electronic records.
- STIX 2.1 format aligns with **CERT-In's CTI sharing standards** and **TAXII 2.1 protocol** for inter-agency intelligence exchange.
- Supports **GDPR Article 30** record-keeping requirements for EU-based investigations.

---

### 10. Tor Circuit Management

Drishti includes built-in Tor lifecycle management — connect, disconnect, and rotate circuits directly from the platform without any manual configuration. Circuit rotation changes your Tor exit node, providing a fresh network identity for each investigation phase.

**How it helps:**
- Operational security is maintained automatically — no manual Tor management needed.
- Circuit rotation reduces the risk of target sites correlating multiple requests to a single investigator.
- Status monitoring shows real-time Tor connection health.

**Relevant legal framework:**
- Supports **operational security (OPSEC)** requirements for undercover digital investigations under **CrPC Section 91 (India)** and equivalent provisions.
- Aligns with **FBI/DOJ guidelines** on covert online investigations and digital undercover operations.

---

### 11. LLM-Generated Intelligence Summaries

After collecting and extracting all artifacts, Drishti uses an LLM to generate a structured, human-readable intelligence summary. The summary includes source links, extracted artifacts organized by source, and an analytical narrative — all in a single report.

**How it helps:**
- Transforms raw scraped data into a professional intelligence product in seconds.
- Summaries are structured with clear sections: Source Links, Extracted Artifacts, LLM Analysis.
- Supports multiple LLM providers so agencies can use their preferred or approved AI vendor.
- Intelligent caching means repeated queries return instantly without additional API costs.

**Relevant legal framework:**
- AI-assisted analysis supports **OSINT-based intelligence products** admissible under **Section 45A of the Indian Evidence Act** (expert opinion on electronic records).
- Aligns with **NATO OSINT Handbook** standards for structured intelligence reporting.

---

### 12. Real-Time Streaming Interface

Drishti's web UI and API use **Server-Sent Events (SSE)** to stream investigation progress in real time. Every stage — query refinement, searching, filtering, scraping, summarizing — is visible as it happens.

**How it helps:**
- Investigators know exactly what the platform is doing at every moment.
- Long-running investigations don't feel like a black box.
- Verbose mode provides a detailed audit trail of every step, useful for court documentation of methodology.

---

### 13. Health & Status Monitoring

A dedicated `/health` and `/status` endpoint provides real-time visibility into platform health and the availability of all 15 dark web search engines. This enables integration with monitoring dashboards and alerting systems.

**How it helps:**
- Operations teams can monitor platform availability 24/7.
- Search engine health data helps investigators understand result coverage.
- Supports SLA monitoring for agencies running Drishti as a shared service.

---

## Deployment Flexibility

Drishti is designed to run in any environment:

- **Docker** — Full containerized deployment with `docker-compose.yml` for rapid setup.
- **Local** — Direct Python installation for air-gapped or offline environments.
- **CLI Mode** — Scriptable command-line interface for automation and integration with existing workflows.
- **Web UI** — React-based frontend for interactive investigations.
- **API** — RESTful Flask API for integration with case management systems, SIEMs, and custom tooling.

---

## Summary

Drishti brings together AI intelligence, resilient dark web search, comprehensive artifact extraction, and professional reporting into a single platform — purpose-built for the investigators who need it most. Every feature is designed with legal admissibility, operational security, and investigative efficiency in mind.

> *"The best intelligence tool is the one that gets out of the way and lets investigators focus on what matters — finding the truth."*

---


