"""
Drishti Monitoring Scheduler.
Automates scheduled dark web keyword scans in the background using APScheduler.
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional

try:
    from apscheduler.schedulers.background import BackgroundScheduler
except ImportError:
    BackgroundScheduler = None

try:
    from backend.monitoring.watchlist import WatchlistManager
    from backend.analysis.severity_scorer import SeverityScorer
    from backend.nlp.language_pipeline import LanguagePipeline
    from backend.alerts.alert_dispatcher import AlertDispatcher
    from backend.search import get_search_results
    from backend.scrape import scrape_multiple
    from backend.async_scraper import scrape_multiple_async
    from backend.llm import get_llm, refine_query, filter_results, generate_summary
    from backend.artifact_extractor import ArtifactExtractor
    from backend.config import FLASK_DEBUG
except ModuleNotFoundError:
    from monitoring.watchlist import WatchlistManager
    from analysis.severity_scorer import SeverityScorer
    from nlp.language_pipeline import LanguagePipeline
    from alerts.alert_dispatcher import AlertDispatcher
    from search import get_search_results
    from scrape import scrape_multiple
    from async_scraper import scrape_multiple_async
    from llm import get_llm, refine_query, filter_results, generate_summary
    from artifact_extractor import ArtifactExtractor
    from config import FLASK_DEBUG


logger = logging.getLogger(__name__)

class MonitoringScheduler:
    """Schedules, triggers, and manages automated background dark web scans."""

    def __init__(self, manager: Optional[WatchlistManager] = None):
        self.manager = manager or WatchlistManager()
        self.scorer = SeverityScorer()
        self.nlp = LanguagePipeline()
        self.dispatcher = AlertDispatcher()
        
        if BackgroundScheduler:
            self.scheduler = BackgroundScheduler()
        else:
            self.scheduler = None
            logger.warning("APScheduler is not installed. Background scanning will not be functional.")

    def start(self):
        """Start the background scheduler."""
        if self.scheduler:
            if not self.scheduler.running:
                self.scheduler.start()
                logger.info("Monitoring background scheduler started.")
                # Load all active watchlists from DB and schedule jobs
                self._load_active_jobs()
        else:
            logger.warning("Scheduler not initialized. Cannot start background scans.")

    def shutdown(self):
        """Stop the background scheduler."""
        if self.scheduler and self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Monitoring background scheduler shutdown completed.")

    def _load_active_jobs(self):
        """Query and schedule jobs for all active watchlists from SQLite."""
        try:
            watchlists = self.manager.get_all_watchlists()
            for wl in watchlists:
                # Default interval is 6 hours for dark web refreshes unless configured otherwise
                self.add_watchlist_job(wl["id"], interval_hours=6)
        except Exception as e:
            logger.error(f"Error loading active watchlist jobs: {e}")

    def add_watchlist_job(self, watchlist_id: int, interval_hours: int = 6):
        """Schedule a recurring background scan job for a watchlist."""
        if not self.scheduler:
            return
        
        job_id = f"watchlist_{watchlist_id}"
        self.remove_job(watchlist_id)  # Remove if already exists to prevent duplication
        
        self.scheduler.add_job(
            func=self._run_watchlist_scan,
            trigger="interval",
            hours=interval_hours,
            id=job_id,
            args=[watchlist_id],
            next_run_time=datetime.now() + timedelta(seconds=10) # Run first scan shortly after scheduling
        )
        logger.info(f"Scheduled scan job '{job_id}' every {interval_hours} hours.")

    def remove_job(self, watchlist_id: int):
        """Cancel a scheduled background watchlist job."""
        if not self.scheduler:
            return
        job_id = f"watchlist_{watchlist_id}"
        try:
            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)
                logger.info(f"Canceled background watchlist scan job '{job_id}'.")
        except Exception as e:
            logger.error(f"Error removing watchlist job {job_id}: {e}")

    def _run_watchlist_scan(self, watchlist_id: int):
        """Execute the automated intelligence crawling pipeline for a watchlist's keywords."""
        logger.info(f"Starting scheduled monitoring scan for Watchlist ID: {watchlist_id}")
        
        # Retrieve watchlist parameters
        wl = self.manager.get_watchlist(watchlist_id)
        if not wl:
            logger.warning(f"Watchlist {watchlist_id} not found in database. Aborting scan.")
            return

        keywords = wl.get("keywords", [])
        if not keywords:
            logger.info(f"Watchlist {watchlist_id} '{wl.get('name')}' has no keywords. Skipping scan.")
            return

        severity_threshold = wl.get("severity_threshold", 35)

        # 24h Alert Deduplication logic
        # Get historical alerts triggered for this watchlist in the last 24h
        cutoff_time = (datetime.now(timezone.utc) - timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")
        past_alerts = self.manager.get_alerts(watchlist_id, since_timestamp=cutoff_time)
        recently_alerted_urls = {alert["source_url"] for alert in past_alerts if alert.get("source_url")}

        # Perform scan for each keyword
        for kw in keywords:
            try:
                logger.info(f"Scanning watchlist keyword: '{kw}'")
                llm = get_llm("gpt-5-mini")
                
                # 1. Pipeline: Refine
                refined = refine_query(llm, kw)
                
                # 2. Pipeline: Search Onion Domains
                results = get_search_results(refined.replace(" ", "+"), max_workers=3)
                if not results:
                    continue
                
                # 3. Pipeline: Filter Relevance
                filtered = filter_results(llm, refined, results) or results[:5]
                # Filter out recently alerted URLs
                unalerted_results = [r for r in filtered if r["link"] not in recently_alerted_urls]
                if not unalerted_results:
                    logger.debug(f"All relevant results for '{kw}' were already alerted in the last 24h. Skipping.")
                    continue
                
                # Limit watchlist crawling to the top 3 unalerted pages to save resources
                target_results = unalerted_results[:3]
                
                # 4. Pipeline: Scrape
                try:
                    scraped, all_artifacts = scrape_multiple_async(target_results, max_workers=3)
                except Exception:
                    scraped, all_artifacts = scrape_multiple(target_results, max_workers=3, verbose=False)
                
                # 5. Pipeline: Analyze & Score
                for url, html_content in scraped.items():
                    if not html_content or len(html_content) < 100:
                        continue
                        
                    # Extract artifacts for this specific page
                    extractor = ArtifactExtractor()
                    page_art = {url: extractor.extract(html_content)}
                    
                    # Language detection & Translation
                    nlp_res = self.nlp.process(html_content)
                    page_text_en = nlp_res["translated_text"]
                    
                    # Generate brief LLM summary of findings
                    summary = generate_summary(llm, kw, {url: page_text_en}, page_art)
                    
                    # MITRE ATT&CK mapping
                    try:
                        from backend.mitre_mapper import extract_mitre_techniques
                    except ModuleNotFoundError:
                        from mitre_mapper import extract_mitre_techniques
                    ttps = extract_mitre_techniques(page_text_en, llm=llm, query=kw)
                    
                    # Compute severity scoring
                    source_meta = {
                        "url": url,
                        "credibility_score": 50,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                    score_res = self.scorer.calculate(
                        artifacts=page_art,
                        source_metadata=source_meta,
                        summary=summary,
                        watchlist_keywords=[kw],
                        mitre_techniques=ttps
                    )
                    
                    score = score_res["score"]
                    
                    # Trigger alert if severity score meets threshold
                    if score >= severity_threshold:
                        logger.warning(f"Threat detected! Keyword: '{kw}', Score: {score}, Source: {url}")
                        
                        # Store in SQLite database
                        finding_summary = summary[:300] + "..." if len(summary) > 300 else summary
                        self.manager.record_alert(
                            watchlist_id=watchlist_id,
                            finding_summary=finding_summary,
                            severity_score=score,
                            source_url=url
                        )
                        
                        # Build full Alert Payload
                        import uuid
                        alert_payload = {
                            "alert_id": str(uuid.uuid4()),
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "watchlist_name": wl.get("name", "Watchlist Alert"),
                            "severity": {"score": score, "tier": score_res["tier"]},
                            "triggered_keyword": kw,
                            "source_url": url,
                            "summary": finding_summary,
                            "artifacts": {k: list(v) for k, v in page_art.get(url, {}).items()},
                            "recommended_action": score_res["recommended_action"]
                        }
                        
                        # Dispatch real-time alert to all channels (Webhook/Slack/Email)
                        dispatch_destinations = {
                            "email": wl.get("alert_email"),
                            "webhook": wl.get("webhook_url")
                        }
                        self.dispatcher.dispatch(alert_payload, dispatch_destinations)
                        
                        # Mark URL as alerted to prevent double alerting inside the current loop
                        recently_alerted_urls.add(url)
                        
            except Exception as kw_ex:
                logger.error(f"Error running scan on keyword '{kw}' for Watchlist {watchlist_id}: {kw_ex}", exc_info=True)
                
        logger.info(f"Finished scheduled monitoring scan for Watchlist ID: {watchlist_id}")
