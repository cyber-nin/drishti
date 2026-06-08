"""
Dark Web Marketplace Parser Module for DRISHTI.
Provides structured extraction of marketplace listings (products, prices, vendors, shipping rules, PGP keys) 
using heuristic analysis and LLM-assisted Pydantic schema parsing fallbacks.
"""
import re
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Structured Pydantic model for marketplace listings
class MarketplaceListing(BaseModel):
    vendor: Optional[str] = Field(None, description="The name of the vendor or seller")
    product_title: Optional[str] = Field(None, description="The title or name of the product/listing")
    price_btc: Optional[float] = Field(None, description="The price of the listing in Bitcoin (BTC)")
    price_xmr: Optional[float] = Field(None, description="The price of the listing in Monero (XMR)")
    price_usd: Optional[float] = Field(None, description="The price of the listing in US Dollars (USD)")
    category: Optional[str] = Field(None, description="The product category (e.g. Drugs, Hacking, Credentials, Weapons)")
    shipping_from: Optional[str] = Field(None, description="Country or region the product is shipped from")
    ships_to: Optional[List[str]] = Field(None, description="Countries or regions the product can be shipped to")
    pgp_key: Optional[str] = Field(None, description="The vendor's PGP public key block if found on the page")
    rating: Optional[float] = Field(None, description="Vendor or product rating/feedback score (typically 0.0 to 5.0)")
    listing_url: str = Field(..., description="The original URL of the listing")
    extracted_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat(), description="Extraction timestamp")


def extract_heuristically(html_content: str, url: str) -> MarketplaceListing:
    """
    Run fast, high-performance regex and BeautifulSoup heuristics to extract structured listing elements.
    
    Args:
        html_content: Raw HTML text of the page.
        url: Original target URL.
        
    Returns:
        MarketplaceListing object.
    """
    if not html_content:
        return MarketplaceListing(listing_url=url)
        
    # Standard text stripping from HTML to avoid tags
    text_content = re.sub(r'<[^>]+>', ' ', html_content)
    
    # 1. PGP Public Key Block
    pgp_match = re.search(r'-----BEGIN PGP PUBLIC KEY BLOCK-----[\s\S]+?-----END PGP PUBLIC KEY BLOCK-----', html_content)
    pgp_key = pgp_match.group(0).strip() if pgp_match else None
    
    # 2. Price BTC
    btc_match = re.search(r'\b(\d+(?:\.\d+)?)\s*(?:btc|bitcoin|฿)\b', text_content, re.IGNORECASE)
    price_btc = float(btc_match.group(1)) if btc_match else None
    if not price_btc:
        # Alt check: ฿0.0056
        btc_match_alt = re.search(r'฿\s*(\d+(?:\.\d+)?)\b', text_content)
        price_btc = float(btc_match_alt.group(1)) if btc_match_alt else None
        
    # 3. Price XMR
    xmr_match = re.search(r'\b(\d+(?:\.\d+)?)\s*(?:xmr|monero)\b', text_content, re.IGNORECASE)
    price_xmr = float(xmr_match.group(1)) if xmr_match else None
    
    # 4. Price USD
    usd_match = re.search(r'\$\s*(\d+(?:\.\d{1,2})?)\b|\b(\d+(?:\.\d{1,2})?)\s*(?:usd|dollars)\b', text_content, re.IGNORECASE)
    price_usd = None
    if usd_match:
        val = usd_match.group(1) or usd_match.group(2)
        price_usd = float(val) if val else None
        
    # 5. Vendor heuristics
    vendor = None
    vendor_patterns = [
        r'(?:vendor|seller|sold\s+by|merchant)\s*:\s*([a-zA-Z0-9_\-]+)\b',
        r'\bclass=["\'][^"\']*(?:vendor|seller)[^"\']*["\'][^>]*>\s*([a-zA-Z0-9_\-]+)\s*<',
    ]
    for pattern in vendor_patterns:
        v_match = re.search(pattern, html_content, re.IGNORECASE)
        if v_match:
            vendor = v_match.group(1).strip()
            break
            
    # 6. Title heuristics
    title = None
    # Look for H1 or standard listing titles
    title_match = re.search(r'<h1[^>]*>\s*(.*?)\s*</h1>', html_content, re.IGNORECASE)
    if title_match:
        title = re.sub(r'<[^>]+>', '', title_match.group(1)).strip()
        # Clean potential long headers
        if len(title) > 150:
            title = None
            
    if not title:
        # Fallback to Title tag
        page_title = re.search(r'<title[^>]*>\s*(.*?)\s*</title>', html_content, re.IGNORECASE)
        if page_title:
            title = page_title.group(1).strip()
            # Clean common suffixes
            title = re.sub(r'\s*[\-|\|]\s*.*$', '', title).strip()
            
    # 7. Rating heuristics
    rating = None
    rating_match = re.search(r'\b(?:rating|score|feedback)\s*:\s*(\d+(?:\.\d+)?)\b', text_content, re.IGNORECASE)
    if rating_match:
        rating = float(rating_match.group(1))
        if rating > 5.0 and rating <= 100.0:  # Percentage rating → convert to 5.0 scale
            rating = round((rating / 100.0) * 5.0, 2)
            
    # 8. Shipping from / Ships to
    shipping_from = None
    ship_from_match = re.search(
        r'(?:ships?\s+from|origin|location)\s*:\s*(?:ships?\s+from\s+)?([a-zA-Z0-9\s\-]+?)(?=\s*(?:\n|\r|\t|$|<|Destination|Ships?\s+to))',
        text_content,
        re.IGNORECASE
    )
    if ship_from_match:
        shipping_from = ship_from_match.group(1).strip()
        
    ships_to = None
    ship_to_match = re.search(
        r'(?:ships?\s+to|destination)\s*:\s*(?:ships?\s+to\s+)?([a-zA-Z0-9\s\-,\+]+?)(?=\s*(?:\n|\r|\t|$|<|Origin|Location|Ships?\s+from))',
        text_content,
        re.IGNORECASE
    )
    if ship_to_match:
        raw_to = ship_to_match.group(1).strip()
        ships_to = [c.strip() for c in raw_to.split(",") if c.strip()]

    return MarketplaceListing(
        vendor=vendor,
        product_title=title,
        price_btc=price_btc,
        price_xmr=price_xmr,
        price_usd=price_usd,
        shipping_from=shipping_from,
        ships_to=ships_to,
        pgp_key=pgp_key,
        rating=rating,
        listing_url=url
    )


def extract_with_llm(llm: Any, text_content: str, url: str) -> Optional[MarketplaceListing]:
    """
    Query the LLM to extract structured dark web marketplace listing using strict schema formatting.
    
    Args:
        llm: A loaded Large Language Model instance.
        text_content: Text parsed from the page.
        url: Original target URL.
        
    Returns:
        MarketplaceListing object or None if failed.
    """
    if not llm or not text_content:
        return None
        
    prompt = f"""You are a dark web threat analyst extracting structured marketplace listing data from raw page content.
    
Listing URL: {url}
Raw Page Text Content:
\"\"\"{text_content[:4000]}\"\"\"

Analyze the page content and extract the listing details.
Return ONLY a valid JSON object matching the schema below. Do NOT include markdown fences, introductory words, or note sections.

JSON Schema:
{{
  "vendor": "Vendor Name or Username (null if not found)",
  "product_title": "Product Title or Listing Heading (null if not found)",
  "price_btc": 0.005, // Float price in BTC (null if not found)
  "price_xmr": 1.25,  // Float price in XMR (null if not found)
  "price_usd": 150.0, // Float price in USD (null if not found)
  "category": "Drugs" | "Hacking" | "Credentials" | "Weapons" | "Fraud" | "Other" (null if not found),
  "shipping_from": "Origin country/region (null if not found)",
  "ships_to": ["Country1", "Country2"] (null if not found),
  "pgp_key": "Vendor PGP public key block starting with -----BEGIN PGP PUBLIC KEY BLOCK----- (null if not found)",
  "rating": 4.8 // Float rating (null if not found)
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
            data["listing_url"] = url
            return MarketplaceListing(**data)
    except Exception as e:
        logger.warning(f"Error extracting marketplace listing with LLM: {e}")
        
    return None


def extract_marketplace_data(html_content: str, url: str, llm: Optional[Any] = None) -> MarketplaceListing:
    """
    Main extraction interface. Attempts heuristic extraction first.
    If key fields (product_title or vendor) are missing and an LLM is provided, falls back to LLM-assisted extraction.
    """
    heuristic_listing = extract_heuristically(html_content, url)
    
    # If heuristic mapping is already highly populated, return it directly
    if heuristic_listing.product_title and (heuristic_listing.vendor or heuristic_listing.price_usd or heuristic_listing.price_btc):
        return heuristic_listing
        
    if not llm:
        return heuristic_listing
        
    # Fallback to LLM
    text_content = re.sub(r'<[^>]+>', ' ', html_content)
    # Strip excessive whitespace
    text_content = " ".join(text_content.split())
    
    llm_listing = extract_with_llm(llm, text_content, url)
    if not llm_listing:
        return heuristic_listing
        
    # Merge findings: prefer LLM for titles and vendor but merge PGP keys/prices if heuristic found them
    merged = MarketplaceListing(
        vendor=llm_listing.vendor or heuristic_listing.vendor,
        product_title=llm_listing.product_title or heuristic_listing.product_title,
        price_btc=llm_listing.price_btc or heuristic_listing.price_btc,
        price_xmr=llm_listing.price_xmr or heuristic_listing.price_xmr,
        price_usd=llm_listing.price_usd or heuristic_listing.price_usd,
        category=llm_listing.category or heuristic_listing.category,
        shipping_from=llm_listing.shipping_from or heuristic_listing.shipping_from,
        ships_to=llm_listing.ships_to or heuristic_listing.ships_to,
        pgp_key=llm_listing.pgp_key or heuristic_listing.pgp_key,
        rating=llm_listing.rating or heuristic_listing.rating,
        listing_url=url,
        extracted_at=llm_listing.extracted_at or heuristic_listing.extracted_at
    )
    
    return merged
