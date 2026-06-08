"""
Comprehensive Integration Tests for Upgraded Drishti Capabilities.
Verifies all 8 functional priority modules.
"""
import sys
import os
import pytest
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from analysis.severity_scorer import SeverityScorer
from nlp.language_pipeline import LanguagePipeline
from monitoring.watchlist import WatchlistManager
from monitoring.scheduler import MonitoringScheduler
from alerts.alert_dispatcher import AlertDispatcher
from analysis.actor_profiler import ActorProfiler
from analysis.trends import TrendAnalyzer
from forensics.evidence_sealer import EvidenceSealer
from reports.escalation_generator import EscalationGenerator

# ── 1. Severity Scorer Tests ───────────────────────────────────────────────

def test_severity_scorer_calculation():
    scorer = SeverityScorer()
    
    artifacts = {
        "http://market.onion": {
            "btc": ["1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"],
            "email": ["vendor@torbox.onion"]
        }
    }
    source_meta = {
        "url": "http://leakmarket.onion/post/1",
        "credibility_score": 85,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    summary = "Premium RedLine Password Stealer source code leak and credential dumps available."
    watchlist_keywords = ["stealer", "leak", "ransomware"]
    mitre_techniques = [
        {"id": "T1588", "name": "Obtain Capabilities", "tactic": "Resource Development"},
        {"id": "T1567", "name": "Exfiltration Over Web Service", "tactic": "Exfiltration"}
    ]
    enrichment_data = {
        "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa": {
            "malicious": 4,
            "suspicious": 1,
            "abuse_score": 80,
            "source": "virustotal"
        }
    }

    res = scorer.calculate(
        artifacts=artifacts,
        source_metadata=source_meta,
        summary=summary,
        watchlist_keywords=watchlist_keywords,
        mitre_techniques=mitre_techniques,
        enrichment_data=enrichment_data
    )

    assert isinstance(res["score"], int)
    assert res["score"] >= 60  # Should be classified as High or Critical threat level
    assert res["tier"] in ("HIGH", "CRITICAL")
    assert "ioc_reputation_score" in res["breakdown"]
    assert len(res["triggered_keywords"]) > 0
    assert "recommended_action" in res


# ── 2. Multi-Language NLP Pipeline Tests ───────────────────────────────────

def test_language_pipeline_hindi():
    pipeline = LanguagePipeline()
    hindi_text = "हैकर्स ने बैंक डेटा लीक कर दिया है। क्रेडिट कार्ड विवरण बिक्री पर हैं।"
    
    res = pipeline.process(hindi_text)
    
    # Validation
    assert res["original_lang"] == "hi"
    assert "credit card" in res["translated_text"].lower() or "hack" in res["translated_text"].lower()
    assert res["intent"] in ("selling", "buying", "information_sharing", "planning_attack", "unknown")
    assert res["sentiment"] in ("neutral", "transactional", "hostile")


def test_language_pipeline_russian():
    pipeline = LanguagePipeline()
    russian_text = "Продам новые эксплойты и исходный код вымогателя LockBit."
    
    res = pipeline.process(russian_text)
    
    # Validation
    assert res["original_lang"] == "ru"
    assert "exploit" in res["translated_text"].lower() or "lockbit" in res["translated_text"].lower()
    assert len(res["threat_keywords"]) > 0


# ── 3. Watchlist & Alerts Storage Tests ────────────────────────────────────

def test_watchlist_manager_crud(tmp_path):
    db_file = str(tmp_path / "test_watchlist.db")
    mgr = WatchlistManager(db_path=db_file)
    
    # Create
    wl_id = mgr.create_watchlist(
        name="Credit Card Watchlist",
        keywords=["credit card dump", "cvv", "carding"],
        alert_email="analyst@lea.gov.in",
        severity_threshold=40
    )
    assert wl_id > 0

    # Read all
    lists = mgr.get_all_watchlists()
    assert len(lists) == 1
    assert lists[0]["name"] == "Credit Card Watchlist"
    assert "cvv" in lists[0]["keywords"]

    # Add keyword
    assert mgr.add_keyword(wl_id, "cloned card")
    wl = mgr.get_watchlist(wl_id)
    assert "cloned card" in wl["keywords"]

    # Remove keyword
    assert mgr.remove_keyword(wl_id, "cvv")
    wl = mgr.get_watchlist(wl_id)
    assert "cvv" not in wl["keywords"]

    # Record Alert
    assert mgr.record_alert(
        watchlist_id=wl_id,
        finding_summary="Stolen credit cards database dump leaked.",
        severity_score=75,
        source_url="http://cardersleak.onion"
    )

    alerts = mgr.get_alerts(wl_id)
    assert len(alerts) == 1
    assert alerts[0]["severity_score"] == 75
    assert alerts[0]["source_url"] == "http://cardersleak.onion"


# ── 4. Real-Time Alert Webhooks Tests ──────────────────────────────────────

def test_alert_dispatcher_logging(tmp_path):
    db_file = str(tmp_path / "test_dispatcher.db")
    dispatcher = AlertDispatcher(db_path=db_file)
    
    payload = {
        "alert_id": "test-uuid-12345",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "watchlist_name": "Ransomware Alert",
        "severity": {"score": 85, "tier": "CRITICAL"},
        "triggered_keyword": "ransomware",
        "source_url": "http://lockbitsite.onion",
        "summary": "LockBit leaked internal database records of corporate target.",
        "artifacts": {"email": ["lockbit@onionmail.org"]},
        "recommended_action": "Raise threat warning"
    }

    # Dispatch to local dummy destinations to verify logging does not raise exception
    dispatcher.dispatch(payload, destination_overrides={"email": "test@lea.gov.in"})
    
    with dispatcher._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM alert_dispatch_logs")
        logs = cursor.fetchall()
        assert len(logs) > 0


# ── 5. Threat Actor Profiling Tests ────────────────────────────────────────

def test_actor_profiler_ingest(tmp_path):
    db_file = str(tmp_path / "test_profiler.db")
    profiler = ActorProfiler(db_path=db_file)
    
    artifacts = {
        "telegram": ["@cyberking_2026"],
        "xmpp": ["cyberking@jabber.calyxinstitute.org"],
        "btc": ["1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"]
    }
    raw_text = "I am @cyberking_2026. PM me for selling credential leaks. Escrow accepted."

    actor_id = profiler.ingest_finding(
        source_url="http://hackingforum.onion/actor/cyberking",
        artifacts=artifacts,
        raw_text=raw_text
    )
    assert actor_id > 0

    profile = profiler.build_profile(actor_id)
    assert profile["primary_handle"] == "@cyberking_2026"
    assert "@cyberking_2026" in profile["linked_pseudonyms"]
    assert "btc" in profile["linked_iocs"]
    assert "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa" in profile["linked_iocs"]["btc"]
    assert len(profile["platform_presence"]) == 1

    # Correlate
    corrs = profiler.correlate_across_sources("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa")
    assert len(corrs) == 1
    assert corrs[0]["primary_handle"] == "@cyberking_2026"

    # Export STIX2
    stix_str = profiler.export_profile(actor_id, export_format="stix2")
    assert "threat-actor" in stix_str
    assert "@cyberking_2026" in stix_str


# ── 6. Dashboard Trending & Timeline Tests ─────────────────────────────────

def test_trend_analyzer_ingest(tmp_path):
    db_file = str(tmp_path / "test_trends.db")
    analyzer = TrendAnalyzer(db_path=db_file)
    
    assert analyzer.ingest_metadata(
        url="http://leakpage.onion/file1",
        raw_text="Fentanyl and MDMA available on drug shop. High quality cocaine.",
        ioc_count=2,
        severity_score=45,
        language="en"
    )
    
    assert analyzer.ingest_metadata(
        url="http://leakpage.onion/file2",
        raw_text="Explosives and firearms ammunition listing.",
        ioc_count=1,
        severity_score=90,
        language="en"
    )

    # Trending
    trends = analyzer.get_trending_topics()
    assert trends["categories"]["drugs"] >= 2
    assert trends["categories"]["weapons"] >= 2

    # Rankings
    rankings = analyzer.get_source_rankings()
    assert len(rankings) == 1
    assert rankings[0]["domain"] == "leakpage.onion"
    assert rankings[0]["finding_frequency"] == 2

    # Timeline
    timeline = analyzer.get_activity_timeline()
    assert len(timeline) == 1
    assert timeline[0]["total_scans"] == 2


# ── 7. Evidence Sealing Tests ──────────────────────────────────────────────

def test_evidence_sealer_seals(tmp_path):
    db_file = str(tmp_path / "test_sealer.db")
    sealer = EvidenceSealer(db_path=db_file)
    
    report_dict = {
        "query": "exploit buy sale",
        "summary": "Threat actor selling zero-day exploit.",
        "artifacts": {"cve": ["CVE-2026-1234"]}
    }

    seal = sealer.seal_report("report_101", report_dict)
    assert seal["report_id"] == "report_101"
    assert "sha256_hash" in seal
    assert seal["seal_method"] == "local"

    # Verify
    db_seal = sealer.get_seal("report_101")
    assert db_seal["sha256_hash"] == seal["sha256_hash"]
    
    assert sealer.verify_report(report_dict, db_seal)

    # Export PDF / Markdown certificate
    cert_path = str(tmp_path / "cert_65B_101.pdf")
    assert sealer.export_certificate("report_101", cert_path)


# ── 8. Escalation Template Generator Tests ─────────────────────────────────

def test_escalation_generator(tmp_path):
    generator = EscalationGenerator(output_dir=str(tmp_path))
    
    investigation_report = {
        "query": "leak government credentials pan card",
        "summary": "Threat actor has leaked a database of PAN cards and Aadhaar credentials online.",
        "artifacts": {
            "http://leakeddata.onion": {
                "email": ["admin@torbox.onion"]
            }
        }
    }

    res = generator.generate_fir_complaint(investigation_report)
    assert os.path.exists(res["markdown_path"])
