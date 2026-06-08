"""
Unit and Integration Tests for Drishti Phase 2: Intelligence Core.
Tests artifact extraction, MITRE ATT&CK mapping, marketplace parsing, threat classification, graph building, and STIX2 exports.
"""
import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from artifact_extractor import ArtifactExtractor
from mitre_mapper import extract_mitre_techniques, map_text_heuristically
from marketplace_parser import extract_heuristically, MarketplaceListing
from classifier import classify_heuristically, ThreatClassificationResult
from graph_builder import build_graph
from exporter import to_stix2

# ── Sample Raw Text Constants ──────────────────────────────────────────────────
SAMPLE_PGP_KEY = """
-----BEGIN PGP PUBLIC KEY BLOCK-----
Version: GnuPG v2

mQENBFY5a5gBCADF3/S29u56V...
-----END PGP PUBLIC KEY BLOCK-----
"""

SAMPLE_TEXT = f"""
This is an OSINT investigation dump.
Contact us at support@jabber.calyxinstitute.org (XMPP) or contact@domain.com.
Add us on Tox messenger: 4A5FCF766C2E2A6A5506198C2EEF0F771A28A6D197E5B5D619A0A1B2C3D4E5F61234567890AB
Or Session ID: 05c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4
Here is our vendor PGP key:
{SAMPLE_PGP_KEY}
"""

SAMPLE_MARKPLACE_HTML = """
<html>
<head><title>Empire Market - Buy High Quality Stealer</title></head>
<body>
<div class="product-card">
  <h1>Premium RedLine Password Stealer</h1>
  <span class="price">Price: 0.0045 BTC</span>
  <span class="price-xmr">0.85 XMR</span>
  <span class="price-usd">$75.00</span>
  <span class="vendor">Sold by: CyberMerchant_2026</span>
  <span class="shipping">Origin: Ships from Germany</span>
  <span class="ships-to">Destination: Ships to Worldwide, USA, EU</span>
  <span class="rating">Rating: 4.8 / 5.0 (150 reviews)</span>
</div>
</body>
</html>
"""

SAMPLE_RANSOMWARE_TEXT = """
LockBit ransomware group has encrypted the internal volumes of corporate network.
We demand a payment of 5.5 BTC to decrypt files. If payment is not received within 48 hours,
sensitive database files will be published to our leak site blog.
"""


# ── 1. Enhanced Artifact Extraction Tests ──────────────────────────────────────

def test_enhanced_artifact_extraction():
    extractor = ArtifactExtractor()
    artifacts = extractor.extract(SAMPLE_TEXT)
    
    assert 'xmpp' in artifacts
    assert 'support@jabber.calyxinstitute.org' in artifacts['xmpp']
    
    assert 'tox_id' in artifacts
    assert '4A5FCF766C2E2A6A5506198C2EEF0F771A28A6D197E5B5D619A0A1B2C3D4E5F61234567890AB'.lower() in artifacts['tox_id']
    
    assert 'session_id' in artifacts
    assert '05c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4' in artifacts['session_id']
    
    assert 'pgp_key' in artifacts
    assert SAMPLE_PGP_KEY.strip() in artifacts['pgp_key']


def test_format_artifacts_with_pgp_key():
    extractor = ArtifactExtractor()
    artifacts = {
        "http://example.onion": {
            "pgp_key": {SAMPLE_PGP_KEY},
            "xmpp": {"support@jabber.calyxinstitute.org"}
        }
    }
    formatted = extractor.format_artifacts(artifacts)
    assert "PGP Public Keys" in formatted
    assert "PGP Public Key Block" in formatted
    assert "XMPP Handles" in formatted


# ── 2. MITRE ATT&CK Mapping Tests ──────────────────────────────────────────────

def test_mitre_mapping_heuristics():
    # Test ransomware keywords
    techniques = map_text_heuristically(SAMPLE_RANSOMWARE_TEXT)
    tech_ids = [t["id"] for t in techniques]
    
    assert "T1486" in tech_ids  # Data Encrypted for Impact
    assert "T1567" in tech_ids  # Exfiltration Over Web Service / Leak Site
    
    # Verify technique details
    t1486 = next(t for t in techniques if t["id"] == "T1486")
    assert t1486["name"] == "Data Encrypted for Impact"
    assert t1486["tactic"] == "Impact"
    assert t1486["confidence"] == "high"


# ── 3. Marketplace Parser Tests ────────────────────────────────────────────────

def test_marketplace_parser_heuristics():
    listing = extract_heuristically(SAMPLE_MARKPLACE_HTML, "http://empiremarket.onion/listing/123")
    
    assert isinstance(listing, MarketplaceListing)
    assert listing.vendor == "CyberMerchant_2026"
    assert listing.product_title == "Premium RedLine Password Stealer"
    assert listing.price_btc == 0.0045
    assert listing.price_xmr == 0.85
    assert listing.price_usd == 75.00
    assert listing.shipping_from == "Germany"
    assert "Worldwide" in listing.ships_to
    assert listing.rating == 4.8
    assert listing.listing_url == "http://empiremarket.onion/listing/123"


# ── 4. Threat Classification Tests ──────────────────────────────────────────────

def test_threat_classification_heuristics():
    res = classify_heuristically(SAMPLE_RANSOMWARE_TEXT)
    
    assert isinstance(res, ThreatClassificationResult)
    assert res.primary_category == "ransomware"
    assert res.confidence > 0.3
    assert "ransomware" in res.confidence_scores
    assert "leak_site" in res.secondary_categories or res.confidence_scores["leak_site"] > 0.0


# ── 5. Graph Builder Tests ──────────────────────────────────────────────────────

def test_graph_builder_with_techniques():
    artifacts = {
        "http://lockbit.onion": {
            "onion": {"lockbit.onion"},
            "btc": {"1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"},
            "pgp_key": {SAMPLE_PGP_KEY}
        }
    }
    
    # Should automatically extract MITRE techniques from query "ransomware lockbit"
    graph_res = build_graph("ransomware lockbit", artifacts)
    
    assert "nodes" in graph_res
    assert "edges" in graph_res
    
    nodes = graph_res["nodes"]
    node_types = [n["type"] for n in nodes]
    node_labels = [n["label"] for n in nodes]
    
    assert "technique" in node_types
    assert "pgp_key" in node_types
    assert any("T1486" in label for label in node_labels)
    
    # Verify edge relations
    edges = graph_res["edges"]
    relations = [e["relation"] for e in edges]
    assert "associated_ttp" in relations


# ── 6. STIX 2.1 Exporter Tests ──────────────────────────────────────────────────

def test_stix2_exporter_with_attack_patterns():
    artifacts = {
        "http://lockbit.onion": {
            "ipv4": {"198.51.100.1"},
            "btc": {"1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"},
            "xmpp": {"admin@jabber.calyxinstitute.org"}
        }
    }
    
    stix_json = to_stix2("ransomware decrypt payments", artifacts)
    
    import json
    bundle = json.loads(stix_json)
    
    assert bundle["type"] == "bundle"
    assert "objects" in bundle
    
    objects = bundle["objects"]
    types = [obj["type"] for obj in objects]
    
    assert "attack-pattern" in types
    assert "relationship" in types
    assert "user-account" in types
    
    # Check that relationship links an Indicator to an Attack Pattern
    relationships = [obj for obj in objects if obj["type"] == "relationship"]
    assert len(relationships) > 0
    assert relationships[0]["relationship_type"] == "indicates"
    assert relationships[0]["source_ref"].startswith("indicator--")
    assert relationships[0]["target_ref"].startswith("attack-pattern--")


# ── 7. Smart LLM Fallback Tests ──────────────────────────────────────────────────

def test_get_llm_automatic_fallback(monkeypatch):
    import llm
    
    # Mock Ollama base URL to be offline in both potential config imports
    try:
        import backend.config as backend_config
        monkeypatch.setattr(backend_config, "OLLAMA_BASE_URL", "http://localhost:9999")
    except ImportError:
        pass
        
    try:
        import config
        monkeypatch.setattr(config, "OLLAMA_BASE_URL", "http://localhost:9999")
    except ImportError:
        pass
    
    # Mock _get_fallback_llm to return a dummy model
    class DummyLLM:
        pass
    
    dummy_instance = DummyLLM()
    monkeypatch.setattr(llm, "_get_fallback_llm", lambda: (dummy_instance, "dummy-flash"))
    
    # get_llm("llama3.1") should fall back to the dummy cloud model!
    resolved_llm = llm.get_llm("llama3.1")
    assert resolved_llm is dummy_instance
