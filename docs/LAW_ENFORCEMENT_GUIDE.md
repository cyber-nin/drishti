# Law Enforcement Quick Reference Guide

## Overview
Drishti is designed to assist law enforcement agencies in conducting dark web OSINT investigations. This guide provides practical workflows for common investigation scenarios.

## Investigation Artifacts

### Automatically Extracted Indicators

| Artifact Type | Examples | Investigation Use |
|--------------|----------|-------------------|
| **Email Addresses** | user@protonmail.com | Identity linking, account tracking |
| **Bitcoin (BTC)** | 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa | Financial tracking, money laundering |
| **Ethereum (ETH)** | 0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb | Smart contract analysis, NFT tracking |
| **Monero (XMR)** | 4AdUndXHHZ6cfufTMvppY6JwXNouMBzSkbLYfpAV5Usx... | Privacy coin transactions |
| **Litecoin (LTC)** | LM3AdUndXHHZ6cfufTMvppY6JwXNouMBzSkbLYfpAV5U | Alternative cryptocurrency tracking |
| **Telegram** | @username, t.me/channel | Communication channels |
| **Phone Numbers** | +1-555-123-4567 | Contact networks, suspect identification |
| **IP Addresses** | 192.168.1.100 | Infrastructure mapping, server location |
| **Onion Domains** | marketplace.onion | Dark web infrastructure |
| **Domains** | suspicious-site.com | Surface web connections |

## Common Investigation Scenarios

### 1. Ransomware Investigation
```bash
# Initial investigation
python run.py cli -m gpt-4.1 -q "ransomware group payment bitcoin" -v -t 12 -o ransomware_case_001

# Follow-up on specific group
python run.py cli -m gpt-4.1 -q "LockBit ransomware negotiation" -v -t 10 -o lockbit_investigation
```

**Artifacts to Focus On:**
- Bitcoin/Monero addresses for payment tracking
- Telegram handles for negotiation channels
- Email addresses for contact
- Onion domains for leak sites

### 2. Marketplace Investigation
```bash
# Identify active marketplaces
python run.py cli -m claude-sonnet-4-5 -q "darknet marketplace drugs weapons" -v -t 15 -o marketplace_scan

# Vendor investigation
python run.py cli -m gpt-4.1 -q "vendor username marketplace reviews" -v -t 10 -o vendor_profile
```

**Artifacts to Focus On:**
- Cryptocurrency addresses for transactions
- Vendor usernames and handles
- Onion marketplace URLs
- Email contacts

### 3. Credential Leak Investigation
```bash
# Search for leaked credentials
python run.py cli -m gpt-4.1 -q "database leak credentials 2024" -v -t 12 -o credential_leak

# Specific organization
python run.py cli -m gpt-4.1 -q "company_name employee credentials breach" -v -t 10 -o company_breach
```

**Artifacts to Focus On:**
- Email addresses from organization
- Domains associated with breach
- Paste sites and forums
- Threat actor handles

### 4. Threat Actor Profiling
```bash
# Profile specific actor
python run.py cli -m claude-sonnet-4-5 -q "threat_actor_name posts activity" -v -t 12 -o actor_profile

# Track actor across platforms
python run.py cli -m gpt-4.1 -q "threat_actor_handle forum marketplace" -v -t 15 -o actor_tracking
```

**Artifacts to Focus On:**
- All handles and usernames
- Email addresses
- Cryptocurrency addresses
- Communication channels

### 5. Child Exploitation Investigation
```bash
# CAUTION: Use appropriate filters and follow agency protocols
python run.py cli -m gpt-4.1 -q "CSAM forum takedown operation" -v -t 10 -o csam_investigation
```

**Artifacts to Focus On:**
- Onion domains for reporting
- User handles for identification
- IP addresses if exposed
- Payment methods

## Best Practices

### 1. Documentation
- Always use the `-o` flag to name your investigation files
- Include case numbers in output filenames
- Save all generated reports for evidence
- Timestamp format is automatic: `summary_YYYY-MM-DD_HH-MM-SS.md`

### 2. Verbose Mode Usage
- Use `-v` flag for complex investigations
- Helps track which sources were successfully scraped
- Useful for court documentation of methodology
- Provides audit trail of investigation steps

### 3. Thread Optimization
- Use `-t 10-15` for time-sensitive investigations
- Lower threads (`-t 5`) for stable, thorough searches
- Higher threads may trigger rate limits on some engines

### 4. Model Selection
- **gpt-4.1**: Best for complex analysis and detailed reports
- **claude-sonnet-4-5**: Excellent for threat intelligence
- **gemini-2.5-flash**: Fast processing for quick scans
- **llama3.1**: Offline investigations (requires Ollama)

### 5. Artifact Validation
- Always manually verify extracted artifacts
- Cross-reference with other intelligence sources
- Use blockchain explorers for crypto addresses
- Verify email addresses through OSINT tools

## Investigation Workflow

### Phase 1: Initial Reconnaissance
```bash
python run.py cli -m gpt-4.1 -q "broad_search_term" -v -t 10 -o phase1_recon
```
- Review extracted artifacts
- Identify key indicators
- Plan follow-up searches

### Phase 2: Targeted Investigation
```bash
python run.py cli -m gpt-4.1 -q "specific_artifact_or_handle" -v -t 12 -o phase2_targeted
```
- Focus on specific artifacts from Phase 1
- Deep dive into suspect profiles
- Map relationships

### Phase 3: Evidence Collection
```bash
python run.py cli -m claude-sonnet-4-5 -q "final_comprehensive_query" -v -t 15 -o phase3_evidence
```
- Comprehensive artifact collection
- Document all sources
- Prepare for legal proceedings

## Legal Considerations

### Chain of Custody
1. All reports include source URLs
2. Timestamps are automatically generated
3. Artifacts are attributed to sources
4. Investigation methodology is documented in verbose mode

### Admissibility
- Tool uses public dark web search engines
- No illegal access or hacking involved
- Automated extraction with manual verification
- Reproducible investigations

### Privacy & Ethics
- Tool is for lawful investigations only
- Follow agency protocols and legal requirements
- Obtain necessary warrants/authorizations
- Protect sensitive information in reports

## Artifact Export & Integration

### Manual Export
All artifacts are in markdown format and can be:
- Copy/pasted into case management systems
- Converted to CSV/JSON with standard tools
- Imported into threat intelligence platforms
- Shared with partner agencies

### Recommended Tools for Further Analysis
- **Blockchain Explorers**: blockchain.com, etherscan.io
- **Email OSINT**: hunter.io, emailrep.io
- **Domain Analysis**: whois, virustotal.com
- **Telegram**: Telegram OSINT tools
- **IP Analysis**: shodan.io, censys.io

## Troubleshooting

### No Results Found
- Try broader search terms
- Increase thread count
- Check Tor connection: `curl --socks5-hostname 127.0.0.1:9050 https://check.torproject.org`

### Scraping Failures
- Some onion sites may be down (normal on dark web)
- Verbose mode shows which URLs failed
- Retry with different thread count

### Rate Limiting
- Reduce thread count
- Add delays between investigations
- Use different LLM models

## Support & Training

For agency training or technical support:
- Review the main README.md
- Check ARTIFACT_EXTRACTION.md for technical details
- Open issues on GitHub for bugs
- Follow operational security best practices

## Disclaimer

This tool is for lawful law enforcement investigations only. Users are responsible for:
- Complying with all applicable laws
- Following agency policies and procedures
- Obtaining necessary legal authorizations
- Protecting sensitive information
- Maintaining operational security

---

**Remember**: Always verify artifacts manually and follow your agency's standard operating procedures for dark web investigations.
