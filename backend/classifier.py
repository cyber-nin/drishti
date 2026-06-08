"""
Threat Content Classifier Module for DRISHTI.
Provides automated classification of scraped dark web content into predefined threat risk taxonomies
using keyword heuristics and LLM-assisted Pydantic structured schemas.
"""
import re
import logging
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Predefined risk taxonomy categories
CATEGORIES = ["ransomware", "leak_site", "marketplace", "malware", "hacking_forum", "financial_fraud", "other"]

class ThreatClassificationResult(BaseModel):
    primary_category: str = Field(..., description="The dominant threat/risk category of the page")
    confidence: float = Field(..., description="Confidence score for the primary classification (0.0 to 1.0)")
    secondary_categories: List[str] = Field(default_factory=list, description="Any supporting threat categories identified")
    confidence_scores: Dict[str, float] = Field(..., description="Confidence scores mapping for all evaluated categories")
    rationale: str = Field(..., description="1-sentence analytical rationale for this threat classification")


def classify_heuristically(text: str) -> ThreatClassificationResult:
    """
    Run fast, high-performance keyword analysis to evaluate threat risk classification.
    
    Args:
        text: Raw text content from scraped page.
        
    Returns:
        ThreatClassificationResult object.
    """
    if not text:
        return ThreatClassificationResult(
            primary_category="other",
            confidence=1.0,
            secondary_categories=[],
            confidence_scores={cat: 0.0 for cat in CATEGORIES if cat != "other"} | {"other": 1.0},
            rationale="No content provided to analyze."
        )
        
    category_scores = {cat: 0.0 for cat in CATEGORIES}
    
    # Keyword weights mapping
    keywords = {
        "ransomware": [r"ransomware", r"encrypt", r"decrypt", r"pay(?:ment)?\s+demand", r"lockbit", r"alphv", r"blackcat", r"clop", r"negotiat", r"extort"],
        "leak_site": [r"leak\s+site", r"leak\s+blog", r"published\s+data", r"dumped\s+data", r"breached\s+files", r"download\s+leak", r"victim\s+list"],
        "marketplace": [r"vendor", r"product", r"add\s+to\s+cart", r"escrow", r"shipping", r"ships\s+from", r"ships\s+to", r"buy\s+now", r"price", r"monero", r"xmr", r"btc"],
        "malware": [r"stealer", r"loader", r"crypter", r"botnet", r"c2", r"backdoor", r"trojan", r"exploit\s+kit", r"keylogger", r"spyware"],
        "hacking_forum": [r"forum", r"post", r"thread", r"tutorials?", r"how\s+to\s+hack", r"source\s+code\s+leak", r"exploit\s+release", r"database\s+leak", r"leaked\s+combo"],
        "financial_fraud": [r"carding", r"cloned\s+cards?", r"cvv", r"fullz", r"dumps", r"bank\s+transfer", r"paypal\s+cashout", r"western\s+union", r"logs\s+sale", r"cc\s+shop"]
    }
    
    total_hits = 0
    for category, patterns in keywords.items():
        hits = 0
        for pattern in patterns:
            hits += len(re.findall(pattern, text, re.IGNORECASE))
            
        category_scores[category] = float(hits)
        total_hits += hits
        
    # Standardize confidence scores
    confidence_scores = {}
    if total_hits > 0:
        for cat in CATEGORIES:
            if cat == "other":
                continue
            confidence_scores[cat] = round(category_scores[cat] / total_hits, 2)
            
        # If the highest score is very small, classify as other
        max_score_cat = max(confidence_scores, key=confidence_scores.get)
        if confidence_scores[max_score_cat] < 0.15:
            primary = "other"
            confidence = 0.8
            confidence_scores["other"] = 0.8
        else:
            primary = max_score_cat
            confidence = confidence_scores[max_score_cat]
            confidence_scores["other"] = 0.0
    else:
        primary = "other"
        confidence = 1.0
        confidence_scores = {cat: 0.0 for cat in CATEGORIES if cat != "other"}
        confidence_scores["other"] = 1.0
        
    # Secondary categories (any with confidence >= 0.20 except primary)
    secondaries = [
        cat for cat, score in confidence_scores.items() 
        if cat != primary and cat != "other" and score >= 0.20
    ]
    
    rationales = {
        "ransomware": "Page matches highly specific ransomware payment, encryption, and extortion indicators.",
        "leak_site": "Page contains terms commonly associated with active corporate data breaches and leak publications.",
        "marketplace": "Page exhibits structured e-commerce, shopping, shipping, escrow, and cryptocurrency payment indicators.",
        "malware": "Page discusses exploit kits, stealers, load scripts, botnets, or automated trojans.",
        "hacking_forum": "Page is structured with standard forum threads, posts, sharing tutorials, or credentials combos.",
        "financial_fraud": "Page focuses on carding, bank drops, compromised transfers, cloned credit cards, and fullz.",
        "other": "No dominant indicators found; page classified as general dark web resource."
    }
    
    return ThreatClassificationResult(
        primary_category=primary,
        confidence=confidence,
        secondary_categories=secondaries,
        confidence_scores=confidence_scores,
        rationale=rationales.get(primary, "Classified heuristically.")
    )


def classify_content_with_llm(llm: Any, text: str) -> Optional[ThreatClassificationResult]:
    """
    Query the LLM to classify dark web text content into the risk taxonomy.
    
    Args:
        llm: A loaded Large Language Model instance.
        text: Page text content.
        
    Returns:
        ThreatClassificationResult object or None if failed.
    """
    if not llm or not text:
        return None
        
    prompt = f"""You are a cyber threat intelligence analyst classifying dark web web pages into standard threat categories.
    
Page Scraped Text:
\"\"\"{text[:4000]}\"\"\"

Classify this text content into one of these strict risk categories:
- ransomware (ransomware demands, lockbit negotiation, victim portals)
- leak_site (ransomware leak blogs, corporate data breach catalogs, file dumps)
- marketplace (drug, weapon, credentials, account stores with cart/escrow/shipping)
- malware (stealer, loader, RAT, crypter, exploit code development/sale)
- hacking_forum (structured discussion boards, user threads, tutorials, credential combo lists)
- financial_fraud (carding, credit cards shops, paypal cashout, compromised bank transfers)
- other (general darknet search engines, link hubs, personal blogs, or neutral pages)

Return ONLY a valid JSON object matching the schema below. Do NOT include markdown fences, note sections, or extra commentary.

JSON Schema:
{{
  "primary_category": "primary_category_name", // One of: ransomware, leak_site, marketplace, malware, hacking_forum, financial_fraud, other
  "confidence": 0.85, // Float between 0.0 and 1.0
  "secondary_categories": ["secondary_category_name"], // Array of other applicable categories (exclude other)
  "confidence_scores": {{
    "ransomware": 0.0,
    "leak_site": 0.0,
    "marketplace": 0.0,
    "malware": 0.0,
    "hacking_forum": 0.0,
    "financial_fraud": 0.0,
    "other": 0.0
  }}, // Complete float score mapping for all 7 categories (must sum to roughly 1.0)
  "rationale": "Brief 1-sentence explanation of why this page fits the primary category based on exact keywords or text indicators."
}}
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
        data = json.loads(response_text)
        if isinstance(data, dict):
            primary = data.get("primary_category", "other").lower().strip()
            if primary not in CATEGORIES:
                primary = "other"
            data["primary_category"] = primary
            
            # Clean secondary categories
            sec = [s.lower().strip() for s in data.get("secondary_categories", []) if s.lower().strip() in CATEGORIES and s.lower().strip() != "other"]
            data["secondary_categories"] = sec
            
            return ThreatClassificationResult(**data)
    except Exception as e:
        logger.warning(f"Error classifying threat content with LLM: {e}")
        
    return None


def classify_content(llm: Optional[Any], text: str) -> ThreatClassificationResult:
    """
    Main content classification interface.
    Attempts LLM classification if an LLM is provided, else falls back to heuristics.
    """
    if llm:
        llm_result = classify_content_with_llm(llm, text)
        if llm_result:
            return llm_result
            
    return classify_heuristically(text)
