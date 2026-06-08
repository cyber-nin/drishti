"""
MITRE ATT&CK Mapping Module for DRISHTI.
Provides heuristic and LLM-assisted mapping of dark web content to MITRE Enterprise techniques.
"""
import re
import logging
from typing import Dict, List, Set, Any, Optional

logger = logging.getLogger(__name__)

# Standard mapping of common techniques related to dark web, cybercrime, and OSINT
MITRE_TECHNIQUES = {
    "T1486": {
        "name": "Data Encrypted for Impact",
        "tactic": "Impact",
        "description": "Adversaries may encrypt data on non-system or system volumes on compromised systems or on shared network drives to interrupt the availability of system and network resources.",
        "keywords": [r"ransomware", r"encrypt", r"decrypt", r"pay(?:ment)?\s+demand", r"lockbit", r"alphv", r"blackcat", r"clop", r"negotiat", r"leak\s+site", r"extort"]
    },
    "T1566": {
        "name": "Phishing",
        "tactic": "Initial Access",
        "description": "Adversaries may send phishing messages to gain access to systems. All forms of phishing are targeted at individuals and rely on social engineering.",
        "keywords": [r"phish", r"credential\s+harvest", r"fake\s+page", r"spoof", r"clone", r"lure", r"spearphish", r"lookalike"]
    },
    "T1567": {
        "name": "Exfiltration Over Web Service",
        "tactic": "Exfiltration",
        "description": "Adversaries may exfiltrate data using a Web service, such as a cloud storage service, instead of a more conventional transfer protocol.",
        "keywords": [r"pastebin", r"github", r"exfiltrat", r"mega\.nz", r"dropbox", r"gdrive", r"leak", r"dump", r"database\s+breach", r"sensitive\s+data"]
    },
    "T1583": {
        "name": "Acquire Infrastructure",
        "tactic": "Resource Development",
        "description": "Adversaries may purchase, lease, or otherwise acquire infrastructure that can be used during targeting or operational execution.",
        "keywords": [r"buy\s+domain", r"register\s+domain", r"vps", r"hosting", r"acquire\s+server", r"purchase\s+proxy", r"rent\s+infrastructure"]
    },
    "T1584": {
        "name": "Compromise Infrastructure",
        "tactic": "Resource Development",
        "description": "Adversaries may compromise third-party infrastructure that can be used during targeting or operational execution.",
        "keywords": [r"botnet", r"c2\s+server", r"hijack", r"compromised\s+website", r"web\s+shell", r"backdoor\s+access"]
    },
    "T1588": {
        "name": "Obtain Capabilities",
        "tactic": "Resource Development",
        "description": "Adversaries may buy, steal, or otherwise obtain capabilities that can be used during targeting or operational execution.",
        "keywords": [r"buy\s+malware", r"exploit\s+kit", r"zero-day", r"purchase\s+stealer", r"crypter", r"access\s+broker", r"initial\s+access\s+sale", r"loader"]
    },
    "T1586": {
        "name": "Compromise Accounts",
        "tactic": "Resource Development",
        "description": "Adversaries may compromise social media, email, or other user accounts that can be used during targeting or operational execution.",
        "keywords": [r"compromised\s+account", r"hijacked\s+profile", r"session\s+hijack", r"cookie\s+steal", r"leaked\s+credential", r"combo\s+list"]
    },
    "T1105": {
        "name": "Ingress Tool Transfer",
        "tactic": "Command and Control",
        "description": "Adversaries may transfer tools or other files from an external system into a compromised environment.",
        "keywords": [r"download\s+payload", r"upload\s+tool", r"wget", r"curl\s+download", r"fetch\s+malware", r"payload\s+delivery"]
    },
    "T1204": {
        "name": "User Execution",
        "tactic": "Execution",
        "description": "Adversaries may rely on the actions of a user in order to gain execution. This may include opening a malicious document, clicking a link, or running a file.",
        "keywords": [r"open\s+attachment", r"click\s+link", r"enable\s+macros", r"lure\s+document", r"victim\s+click"]
    },
    "T1090": {
        "name": "Proxy",
        "tactic": "Command and Control",
        "description": "Adversaries may use a proxy to direct network traffic between systems or to act as an intermediary for network communications, especially to avoid security controls.",
        "keywords": [r"tor\s+circuit", r"socks5", r"onion\s+proxy", r"anonymous\s+route", r"proxy\s+chain", r"channelling"]
    },
    "T1587": {
        "name": "Develop Capabilities",
        "tactic": "Resource Development",
        "description": "Adversaries may develop capabilities that can be used during targeting or operational execution, such as custom malware, exploits, or infrastructure scripts.",
        "keywords": [r"malware\s+development", r"coding\s+exploit", r"source\s+code\s+leak", r"develop\s+backdoor", r"write\s+stealer"]
    },
    "T1213": {
        "name": "Data from Information Repositories",
        "tactic": "Collection",
        "description": "Adversaries may leverage information repositories (like SharePoint, Confluence, or source code systems) to extract sensitive operational data.",
        "keywords": [r"database\s+dump", r"sql\s+dump", r"extract\s+wiki", r"leak\s+repository", r"confluence\s+breach", r"steal\s+source\s+code"]
    },
    "T1190": {
        "name": "Exploit Public-Facing Application",
        "tactic": "Initial Access",
        "description": "Adversaries may attempt to exploit a weakness in an Internet-facing computer or program to gain initial access to a network.",
        "keywords": [r"cve-", r"exploit\s+vulnerability", r"sql\s+injection", r"rce\s+exploit", r"cross-site\s+scripting", r"zero\s+day"]
    },
    "T1078": {
        "name": "Valid Accounts",
        "tactic": "Defense Evasion",
        "description": "Adversaries may steal credentials of a specific user or service account to bypass access controls and evade active detection mechanisms.",
        "keywords": [r"admin\s+login", r"valid\s+credentials", r"active\s+session", r"access\s+token", r"corporate\s+login", r"rdp\s+credentials"]
    },
    "T1555": {
        "name": "Credentials from Password Stores",
        "tactic": "Credential Access",
        "description": "Adversaries may search password stores, web browsers, or credential managers to gain access to system, service, or database accounts.",
        "keywords": [r"password\s+stealer", r"browser\s+credentials", r"keychain", r"dump\s+passwords", r"credentials\.txt", r"redline\s+stealer", r"vidar"]
    },
    "T1490": {
        "name": "Inhibit System Recovery",
        "tactic": "Impact",
        "description": "Adversaries may delete or disrupt system backups, shadow copies, or boot settings to prevent recovery.",
        "keywords": [r"delete\s+backups", r"vssadmin", r"shadow\s+copy", r"disable\s+recovery", r"wipe\s+restore"]
    },
    "T1498": {
        "name": "Network Denial of Service",
        "tactic": "Impact",
        "description": "Adversaries may perform Network Denial of Service (DoS) attacks to disrupt or degrade system/network resource availability.",
        "keywords": [r"ddos\s+booter", r"ddos\s+service", r"stressor", r"syn\s+flood", r"denial\s+of\s+service", r"botnet\s+ddos"]
    },
    "T1595": {
        "name": "Active Scanning",
        "tactic": "Reconnaissance",
        "description": "Adversaries may execute active reconnaissance scans to gather information about target networks, systems, or service vulnerabilities.",
        "keywords": [r"port\s+scan", r"nmap", r"shodan\s+scan", r"vulnerability\s+scan", r"enumerate", r"network\s+sweep"]
    }
}


def map_text_heuristically(text: str) -> List[Dict[str, Any]]:
    """
    Run keyword-matching algorithms to determine associated MITRE ATT&CK techniques.
    
    Args:
        text: Raw scraped page content or analytical summary.
        
    Returns:
        List of technique dictionaries found in the text.
    """
    if not text:
        return []
        
    matched_techniques = []
    
    for tid, info in MITRE_TECHNIQUES.items():
        matches_count = 0
        for kw_pattern in info["keywords"]:
            if re.search(kw_pattern, text, re.IGNORECASE):
                matches_count += 1
                
        if matches_count > 0:
            confidence = "low"
            if matches_count >= 3:
                confidence = "high"
            elif matches_count >= 1:
                confidence = "medium"
                
            matched_techniques.append({
                "id": tid,
                "name": info["name"],
                "tactic": info["tactic"],
                "description": info["description"],
                "confidence": confidence,
                "matches": matches_count
            })
            
    # Sort by matches count descending
    return sorted(matched_techniques, key=lambda x: x["matches"], reverse=True)


def map_text_with_llm(llm: Any, text: str, query: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Query the LLM to extract sophisticated MITRE Enterprise TTP mappings.
    
    Args:
        llm: A loaded LangChain or custom LLM instance.
        text: Investigation summary or scraped pages.
        query: Original search query context.
        
    Returns:
        List of mapped techniques.
    """
    if not llm or not text:
        return []
        
    prompt = f"""You are a senior cyber threat intelligence analyst mapping dark web intelligence findings to the MITRE Enterprise ATT&CK framework.
    
Investigation Context:
Query: {query or "N/A"}
Scraped Content / Findings:
\"\"\"{text[:4000]}\"\"\"

Review the findings above and map them to the most relevant MITRE Enterprise ATT&CK Techniques.
Choose from these common dark web techniques or add other highly relevant ones:
- T1486 (Data Encrypted for Impact) - for ransomware / leak sites
- T1566 (Phishing) - credential harvest, fake pages
- T1567 (Exfiltration Over Web Service) - exfiltrated database leaks to pastebin / github
- T1588 (Obtain Capabilities) - buying/selling malware, stealer logs, exploits
- T1586 (Compromise Accounts) - leaked database records, combo lists
- T1090 (Proxy) - Tor network usage, anonymous SOCKS proxies
- T1595 (Active Scanning) - open port scanners, Shodan findings

Return ONLY a valid JSON array of objects. Do NOT include markdown blocks, introductory text, or explanatory headers.
Output Schema:
[
  {{
    "id": "TXXXX",
    "name": "Technique Name",
    "tactic": "Tactic Name",
    "confidence": "high" | "medium" | "low",
    "rationale": "Brief 1-sentence explanation of why this technique applies based on the findings"
  }}
]
"""
    try:
        response = llm.invoke(prompt)
        response_text = ""
        
        if isinstance(response, dict):
            response_text = response.get("output_text") or response.get("text") or response.get("response") or str(response)
        elif isinstance(response, str):
            response_text = response
        else:
            response_text = str(response)
            
        # Clean potential markdown fences
        response_text = response_text.replace("```json", "").replace("```", "").strip()
        
        import json
        mappings = json.loads(response_text)
        if isinstance(mappings, list):
            valid_mappings = []
            for mapping in mappings:
                tid = mapping.get("id", "").strip().upper()
                if not tid:
                    continue
                # Enrich with description if we have it in our offline registry
                local_info = MITRE_TECHNIQUES.get(tid)
                valid_mappings.append({
                    "id": tid,
                    "name": mapping.get("name") or (local_info["name"] if local_info else "Unknown"),
                    "tactic": mapping.get("tactic") or (local_info["tactic"] if local_info else "Unknown"),
                    "description": local_info["description"] if local_info else "",
                    "confidence": mapping.get("confidence", "medium"),
                    "rationale": mapping.get("rationale", "")
                })
            return valid_mappings
    except Exception as e:
        logger.warning(f"Error mapping MITRE TTPs with LLM: {e}")
        
    return []


def extract_mitre_techniques(text: str, llm: Optional[Any] = None, query: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Extract MITRE ATT&CK techniques from text using both heuristic and optional LLM mappings.
    Merges duplicate results, using LLM rationale where available.
    """
    heuristics = map_text_heuristically(text)
    
    if not llm:
        return heuristics
        
    llm_mappings = map_text_with_llm(llm, text, query)
    if not llm_mappings:
        return heuristics
        
    # Merge results
    merged = {m["id"]: m for m in heuristics}
    for l_map in llm_mappings:
        tid = l_map["id"]
        if tid in merged:
            # Upgrade confidence or add rationale
            merged[tid]["confidence"] = l_map["confidence"]
            merged[tid]["rationale"] = l_map["rationale"]
        else:
            merged[tid] = l_map
            
    return list(merged.values())
