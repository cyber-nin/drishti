from flask import Flask, request, jsonify, send_file, send_from_directory, Response, abort, g
from datetime import datetime, timezone
import os
import json
import logging
import threading
import uuid

try:
    from backend.scrape import scrape_multiple
    from backend.async_scraper import scrape_multiple_async
    from backend.search import get_search_results, SEARCH_ENGINE_STATUS
    from backend.llm import get_llm, refine_query, filter_results, generate_summary
    from backend.deep_crawl import deep_crawl
    from backend.exporter import export_report
    from backend.database import init_db
    from backend.auth import (
        require_auth, require_role, authenticate_user, create_user,
        refresh_access_token, get_current_user, init_default_admin
    )
    from backend.audit import log_audit, AuditAction, query_audit_logs
except ModuleNotFoundError:
    from scrape import scrape_multiple
    from async_scraper import scrape_multiple_async
    from search import get_search_results, SEARCH_ENGINE_STATUS
    from llm import get_llm, refine_query, filter_results, generate_summary
    from deep_crawl import deep_crawl
    from exporter import export_report
    from database import init_db
    from auth import (
        require_auth, require_role, authenticate_user, create_user,
        refresh_access_token, get_current_user, init_default_admin
    )
    from audit import log_audit, AuditAction, query_audit_logs

try:
    from backend.analysis.severity_scorer import SeverityScorer
    from backend.nlp.language_pipeline import LanguagePipeline
    from backend.monitoring.watchlist import WatchlistManager
    from backend.monitoring.scheduler import MonitoringScheduler
    from backend.alerts.alert_dispatcher import AlertDispatcher
    from backend.analysis.actor_profiler import ActorProfiler
    from backend.analysis.trends import TrendAnalyzer
    from backend.forensics.evidence_sealer import EvidenceSealer
    from backend.reports.escalation_generator import EscalationGenerator
except ModuleNotFoundError:
    from analysis.severity_scorer import SeverityScorer
    from nlp.language_pipeline import LanguagePipeline
    from monitoring.watchlist import WatchlistManager
    from monitoring.scheduler import MonitoringScheduler
    from alerts.alert_dispatcher import AlertDispatcher
    from analysis.actor_profiler import ActorProfiler
    from trends import TrendAnalyzer
    from forensics.evidence_sealer import EvidenceSealer
    from reports.escalation_generator import EscalationGenerator


from config import (
    OUTPUT_DIR, FLASK_HOST, FLASK_PORT, FLASK_DEBUG, LOG_LEVEL, LOG_FILE,
    CORS_ORIGINS, RATE_LIMIT_DEFAULT, RATE_LIMIT_INVESTIGATE, AUTH_ENABLED
)

os.makedirs(os.path.dirname(LOG_FILE) or '.', exist_ok=True)
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Suppress stem's noisy Windows socket cleanup messages
logging.getLogger('stem').setLevel(logging.WARNING)
logging.getLogger('stem.control').setLevel(logging.WARNING)
logging.getLogger('stem.socket').setLevel(logging.WARNING)

app = Flask(__name__, static_folder='../frontend/dist/assets', static_url_path='/assets')

# ── Security: CORS ────────────────────────────────────────────────────────────
try:
    from flask_cors import CORS
    cors_origins = CORS_ORIGINS.split(',') if CORS_ORIGINS != '*' else '*'
    CORS(app, resources={r"/*": {"origins": cors_origins}}, supports_credentials=True)
except ImportError:
    logger.warning("flask-cors not installed — CORS headers disabled")

# ── Security: Rate Limiting ───────────────────────────────────────────────────
try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
    limiter = Limiter(
        get_remote_address,
        app=app,
        default_limits=[RATE_LIMIT_DEFAULT],
        storage_uri="memory://",
    )
except ImportError:
    limiter = None
    logger.warning("flask-limiter not installed — rate limiting disabled")

# ── Security: Response Headers ────────────────────────────────────────────────
@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    # CSP: Allow inline styles/scripts for SSE and React app
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data:; "
        "connect-src 'self'"
    )
    return response

# Resolve OUTPUT_DIR relative to cwd (where Flask is launched from)
_OUTPUT_PATH = OUTPUT_DIR if os.path.isabs(OUTPUT_DIR) else os.path.abspath(OUTPUT_DIR)

# In-memory batch job store
_batch_jobs: dict = {}

# API route prefixes — catch-all must not intercept these
_API_PREFIXES = ('investigate', 'crawl', 'batch', 'download', 'export', 'health',
                 'status', 'enrich', 'graph', 'tor', 'auth', 'audit', 'knowledge',
                 'watchlist', 'actor', 'dashboard', 'report', 'forensics')


def sse_response(generator):
    resp = app.response_class(generator, mimetype='text/event-stream')
    resp.headers['Cache-Control'] = 'no-cache'
    resp.headers['X-Accel-Buffering'] = 'no'
    resp.headers['Connection'] = 'keep-alive'
    return resp


def _scrape(filtered, threads):
    try:
        return scrape_multiple_async(filtered, max_workers=threads)
    except Exception:
        return scrape_multiple(filtered, max_workers=threads, verbose=False)


# ── Static serving ────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return send_from_directory('../frontend/dist', 'index.html')


@app.route('/<path:filename>')
def serve_root_files(filename):
    if filename.split('/')[0] in _API_PREFIXES:
        abort(404)
    return send_from_directory('../frontend/dist', filename)


# ── Health ────────────────────────────────────────────────────────────────────

@app.route('/health')
def health_check():
    return jsonify({"status": "online", "timestamp": datetime.now(timezone.utc).isoformat()})


@app.route('/status')
def status():
    return jsonify({
        "status": "online",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "search_engines": SEARCH_ENGINE_STATUS
    })


# ── Authentication ────────────────────────────────────────────────────────────

@app.route('/auth/login', methods=['POST'])
def auth_login():
    body = request.get_json(force=True)
    username = body.get('username', '').strip()
    password = body.get('password', '')
    if not username or not password:
        return jsonify({'error': 'Username and password required'}), 400

    result = authenticate_user(username, password)
    if not result:
        log_audit(AuditAction.LOGIN_FAILED, target=username)
        return jsonify({'error': 'Invalid credentials'}), 401

    log_audit(AuditAction.LOGIN, target=username, user_id=result['user']['id'])
    return jsonify(result)


@app.route('/auth/register', methods=['POST'])
@require_auth
@require_role('admin')
def auth_register():
    body = request.get_json(force=True)
    result = create_user(
        username=body.get('username', '').strip(),
        password=body.get('password', ''),
        role=body.get('role', 'analyst'),
        email=body.get('email'),
    )
    if 'error' in result:
        return jsonify(result), 400

    log_audit(AuditAction.USER_CREATED, target=result.get('username'),
              detail={'role': result.get('role')})
    return jsonify(result), 201


@app.route('/auth/refresh', methods=['POST'])
def auth_refresh():
    body = request.get_json(force=True)
    refresh_token = body.get('refresh_token', '')
    result = refresh_access_token(refresh_token)
    if not result:
        return jsonify({'error': 'Invalid or expired refresh token'}), 401
    return jsonify(result)


@app.route('/auth/me', methods=['GET'])
@require_auth
def auth_me():
    return jsonify(g.current_user)


# ── Audit Logs ────────────────────────────────────────────────────────────────

@app.route('/audit', methods=['GET'])
@require_auth
@require_role('admin')
def audit_logs():
    user_id = request.args.get('user_id', type=int)
    action = request.args.get('action')
    limit = min(request.args.get('limit', 100, type=int), 500)
    offset = request.args.get('offset', 0, type=int)
    result = query_audit_logs(user_id=user_id, action=action, limit=limit, offset=offset)
    return jsonify(result)


# ── Investigation ─────────────────────────────────────────────────────────────

@app.route('/investigate', methods=['GET'])
@require_auth
def investigate():
    query = request.args.get('query')
    model = request.args.get('model', 'gpt-5-mini')
    threads = int(request.args.get('threads', 5))
    safe_query = (query or '').replace('\n', ' ').replace('\r', ' ')[:200]
    logger.info(f"Investigation started: query={safe_query!r} model={model}")
    log_audit(AuditAction.INVESTIGATE, target=safe_query, detail={'model': model})

    def generate():
        try:
            yield f'data: {{"stage":"loading","message":"Loading LLM..."}}\n\n'
            llm = get_llm(model)

            yield f'data: {{"stage":"refining","message":"Refining query..."}}\n\n'
            refined = refine_query(llm, query)
            yield f'data: {json.dumps({"stage": "refined", "data": refined})}\n\n'

            yield f'data: {{"stage":"searching","message":"Searching dark web..."}}\n\n'
            results = get_search_results(refined.replace(" ", "+"), max_workers=threads)
            logger.info(f"Found {len(results)} results")
            yield f'data: {{"stage":"results","data":{len(results)}}}\n\n'

            yield f'data: {{"stage":"filtering","message":"Filtering results..."}}\n\n'
            try:
                filtered = filter_results(llm, refined, results) or results[:20]
            except Exception as e:
                logger.warning(f"Filter error: {e}")
                filtered = results[:20]
            yield f'data: {json.dumps({"stage": "filtered", "data": len(filtered), "links": filtered})}\n\n'

            yield f'data: {{"stage":"scraping","message":"Scraping content..."}}\n\n'
            scraped, all_artifacts = _scrape(filtered, threads)
            logger.info(f"Scraped {len(scraped)} pages")

            yield f'data: {{"stage":"summarizing","message":"Generating summary and performing multi-language NLP..."}}\n\n'
            
            # Wrap entire LLM pipeline with Language Pipeline - run translation BEFORE summarization
            nlp_pipeline = LanguagePipeline()
            translated_scraped = {}
            languages_detected = []
            intents_detected = []
            sentiments_detected = []
            threat_keywords = []
            
            for url, page_text in scraped.items():
                nlp_res = nlp_pipeline.process(page_text)
                translated_scraped[url] = nlp_res["translated_text"]
                languages_detected.append(nlp_res["original_lang"])
                intents_detected.append(nlp_res["intent"])
                sentiments_detected.append(nlp_res["sentiment"])
                threat_keywords.extend(nlp_res["threat_keywords"])
                
            try:
                summary = generate_summary(llm, query, translated_scraped, all_artifacts)
            except Exception as e:
                logger.error(f"Summary error: {e}")
                summary = ""

            if not summary or not summary.strip():
                lines = ["# Investigation Report", "", f"Query: {query}", ""]
                if scraped:
                    lines += ["## Source Links"] + [f"- {s}" for s in sorted(scraped)] + [""]
                if all_artifacts:
                    lines.append("## Extracted Artifacts")
                    for src, art in sorted(all_artifacts.items()):
                        if art:
                            lines.append(f"### {src}")
                            for t, vals in sorted(art.items()):
                                if vals:
                                    lines.append(f"- {t}: {', '.join(sorted(str(v) for v in vals)[:10])}")
                            lines.append("")
                lines += ["## LLM Summary", "No LLM summary available."]
                summary = "\n".join(lines)

            now = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%S")
            filename = f"summary_{now}.md"
            os.makedirs(_OUTPUT_PATH, exist_ok=True)
            safe_filename = os.path.basename(filename)
            with open(os.path.join(_OUTPUT_PATH, safe_filename), "w", encoding="utf-8") as f:
                f.write(summary)
            logger.info(f"Report saved: {safe_filename}")

            # 3. Extract Structured Marketplace Listings
            listings = []
            try:
                try:
                    from backend.marketplace_parser import extract_marketplace_data
                except ModuleNotFoundError:
                    from marketplace_parser import extract_marketplace_data
                
                for url, html in scraped.items():
                    try:
                        listing = extract_marketplace_data(html, url, llm=llm)
                        if listing.product_title or listing.vendor or listing.price_usd or listing.price_btc or listing.price_xmr:
                            listings.append(listing.model_dump())
                    except Exception as listing_ex:
                        logger.debug(f"Listing parse error for {url}: {listing_ex}")
            except Exception as mp_ex:
                logger.debug(f"Marketplace parser not available: {mp_ex}")

            # Serialize artifacts for graph
            serialized_artifacts = {
                url: {t: list(v) if isinstance(v, set) else v for t, v in art.items()}
                for url, art in all_artifacts.items()
            }

            # 4. Integrate Severity Scorer
            severity_scorer = SeverityScorer()
            
            # Extract TTPs
            mitre_techs = []
            try:
                from backend.mitre_mapper import extract_mitre_techniques
            except ModuleNotFoundError:
                from mitre_mapper import extract_mitre_techniques
            flat_text_en = " ".join(translated_scraped.values())
            mitre_techs = extract_mitre_techniques(flat_text_en, llm=llm, query=query)
            
            source_meta = {
                "url": list(scraped.keys())[0] if scraped else "",
                "credibility_score": 50,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            # Watchlist keywords
            watchlist_mgr = WatchlistManager()
            all_wls = watchlist_mgr.get_all_watchlists()
            all_keywords = []
            for wl in all_wls:
                all_keywords.extend(wl.get("keywords", []))
                
            severity_res = severity_scorer.calculate(
                artifacts=all_artifacts,
                source_metadata=source_meta,
                summary=summary,
                watchlist_keywords=all_keywords,
                mitre_techniques=mitre_techs
            )

            # 5. Integrate Threat Actor Profiler
            actor_profiler = ActorProfiler()
            flat_iocs = {}
            for src_url, src_art in all_artifacts.items():
                for t, vals in src_art.items():
                    if t not in flat_iocs:
                        flat_iocs[t] = []
                    flat_iocs[t].extend(list(vals))
                    
            actor_id = actor_profiler.ingest_finding(
                source_url=source_meta["url"],
                artifacts=flat_iocs,
                raw_text=flat_text_en
            )
            
            actor_correlations = []
            for t, vals in flat_iocs.items():
                for val in vals:
                    corrs = actor_profiler.correlate_across_sources(val)
                    for corr in corrs:
                        if corr not in actor_correlations:
                            actor_correlations.append(corr)

            # 6. Integrate Trend Analyzer
            trend_analyzer = TrendAnalyzer()
            ioc_cnt = sum(len(vals) for vals in flat_iocs.values())
            trend_analyzer.ingest_metadata(
                url=source_meta["url"],
                raw_text=flat_text_en,
                ioc_count=ioc_cnt,
                severity_score=severity_res["score"],
                language=languages_detected[0] if languages_detected else "en"
            )

            # 7. Integrate Evidence Sealer
            evidence_sealer = EvidenceSealer()
            report_dict = {
                "query": query,
                "summary": summary,
                "artifacts": serialized_artifacts,
                "listings": listings,
                "mitre_techniques": mitre_techs
            }
            report_id = f"report_{int(datetime.now().timestamp())}"
            seal_res = evidence_sealer.seal_report(report_id, report_dict)

            # Build comprehensive payload
            response_payload = {
                "stage": "complete",
                "summary": summary,
                "filename": filename,
                "artifacts": serialized_artifacts,
                "listings": listings,
                "severity": severity_res,
                "language_analysis": {
                    "original_lang": languages_detected[0] if languages_detected else "en",
                    "intent": intents_detected[0] if intents_detected else "unknown",
                    "sentiment": sentiments_detected[0] if sentiments_detected else "neutral",
                    "threat_keywords": threat_keywords
                },
                "evidence_seal": seal_res,
                "actor_correlations": actor_correlations
            }

            yield f'data: {json.dumps(response_payload)}\n\n'
        except Exception as e:
            logger.error(f"Investigation error: {e}", exc_info=True)
            yield f'data: {json.dumps({"stage": "error", "message": str(e)})}\n\n'

    return sse_response(generate())


# ── Deep Crawl ────────────────────────────────────────────────────────────────

@app.route('/crawl', methods=['GET'])
@require_auth
def crawl():
    url = request.args.get('url')
    depth = int(request.args.get('depth', 2))
    max_pages = {1: 10, 2: 25, 3: 50}.get(depth, 20)

    def generate():
        try:
            for event in deep_crawl(url, max_depth=depth, max_pages=max_pages):
                if event['type'] in ('progress', 'log'):
                    yield f'data: {json.dumps({"stage": "crawling", "message": event["message"]})}\n\n'
                elif event['type'] == 'result':
                    yield f'data: {json.dumps({"stage": "complete", "artifacts": event["data"]})}\n\n'
        except Exception as e:
            logger.error(f"Crawl error: {e}", exc_info=True)
            yield f'data: {json.dumps({"stage": "error", "message": str(e)})}\n\n'

    return sse_response(generate())


# ── Export ────────────────────────────────────────────────────────────────────

@app.route('/export/<filename>')
def export(filename):
    filename = os.path.basename(filename)  # prevent path traversal
    if not filename.endswith('.md'):
        return jsonify({"error": "Invalid file"}), 400
    fmt = request.args.get('format', 'json')
    filepath = os.path.join(_OUTPUT_PATH, filename)
    # Confirm resolved path is still inside _OUTPUT_PATH (double-check traversal)
    if not os.path.abspath(filepath).startswith(os.path.abspath(_OUTPUT_PATH)):
        return jsonify({"error": "Access denied"}), 403
    if not os.path.exists(filepath):
        return jsonify({"error": "File not found"}), 404
    with open(filepath, 'r', encoding='utf-8') as f:
        summary = f.read()
    content, mime = export_report(fmt, filename, summary, {})
    ext = 'json' if fmt in ('stix2', 'json') else fmt
    return Response(
        content,
        mimetype=mime,
        headers={'Content-Disposition': f'attachment; filename={filename.replace(".md", "." + ext)}'}
    )


# ── Batch Investigation ───────────────────────────────────────────────────────

@app.route('/batch', methods=['POST'])
@require_auth
def batch_investigate():
    body = request.get_json(force=True)
    queries = body.get('queries', [])
    model = body.get('model', 'gpt-5-mini')
    threads = int(body.get('threads', 5))

    if not queries or not isinstance(queries, list) or len(queries) > 50:
        return jsonify({"error": "queries must be a non-empty list (max 50)"}), 400

    job_id = str(uuid.uuid4())
    _batch_jobs[job_id] = {
        'status': 'running',
        'total': len(queries),
        'done': 0,
        'results': [],
        'errors': []
    }

    def run_batch():
        try:
            llm = get_llm(model)
        except Exception as e:
            _batch_jobs[job_id]['status'] = 'failed'
            _batch_jobs[job_id]['errors'].append({'query': '__init__', 'error': str(e)})
            return

        for q in queries:
            try:
                refined = refine_query(llm, q)
                results = get_search_results(refined.replace(' ', '+'), max_workers=threads)
                filtered = filter_results(llm, refined, results) or results[:20]
                scraped, all_artifacts = _scrape(filtered, threads)
                summary = generate_summary(llm, q, scraped, all_artifacts)
                now = datetime.now(timezone.utc).strftime('%Y-%m-%d_%H-%M-%S')
                fname = f'summary_{now}.md'
                os.makedirs(_OUTPUT_PATH, exist_ok=True)
                with open(os.path.join(_OUTPUT_PATH, fname), 'w', encoding='utf-8') as f:
                    f.write(summary)
                _batch_jobs[job_id]['results'].append({'query': q, 'filename': fname})
                safe_q = q.replace('\n', ' ').replace('\r', ' ')[:100]
                logger.info(f"Batch job {job_id}: completed {safe_q!r}")
            except Exception as e:
                logger.error(f"Batch job {job_id} error on {q!r}: {e}", exc_info=True)
                _batch_jobs[job_id]['errors'].append({'query': q, 'error': str(e)})
            _batch_jobs[job_id]['done'] += 1

        _batch_jobs[job_id]['status'] = 'complete'

    threading.Thread(target=run_batch, daemon=True).start()
    return jsonify({'job_id': job_id, 'total': len(queries)}), 202


@app.route('/batch/<job_id>', methods=['GET'])
def batch_status(job_id):
    job = _batch_jobs.get(job_id)
    if not job:
        return jsonify({'error': 'Job not found'}), 404
    return jsonify(job)


# ── Tor Management ───────────────────────────────────────────────────────────

@app.route('/tor/status', methods=['GET'])
def tor_status():
    try:
        from backend.tor_manager import get_status
    except ModuleNotFoundError:
        from tor_manager import get_status
    return jsonify(get_status())


@app.route('/tor/connect', methods=['POST'])
def tor_connect():
    try:
        from backend.tor_manager import launch_tor
    except ModuleNotFoundError:
        from tor_manager import launch_tor
    result = launch_tor()
    return jsonify(result), 200 if result['success'] else 500


@app.route('/tor/disconnect', methods=['POST'])
def tor_disconnect():
    try:
        from backend.tor_manager import stop_tor
    except ModuleNotFoundError:
        from tor_manager import stop_tor
    result = stop_tor()
    return jsonify(result)


@app.route('/tor/rotate', methods=['POST'])
def tor_rotate():
    try:
        from backend.tor_manager import rotate_circuit
    except ModuleNotFoundError:
        from tor_manager import rotate_circuit
    success = rotate_circuit()
    return jsonify({'success': success, 'message': 'Circuit rotated' if success else 'Rotation failed (stem not available or Tor not running)'})


# ── IOC Enrichment ────────────────────────────────────────────────────────────

@app.route('/enrich', methods=['POST'])
@require_auth
def enrich():
    """
    Accept a flat list of IOCs and return reputation data.
    Body: { "iocs": [{"type": "ipv4"|"domain"|"md5"|"sha1"|"sha256", "value": str}] }
    Returns: { "results": {"value": {reputation_dict}} }
    """
    try:
        from backend.enrichment import _vt_ip, _vt_domain, _vt_hash, _abuseipdb
    except ModuleNotFoundError:
        from enrichment import _vt_ip, _vt_domain, _vt_hash, _abuseipdb

    body = request.get_json(force=True)
    iocs = body.get('iocs', [])
    if not iocs:
        return jsonify({'results': {}})

    results = {}
    for ioc in iocs[:30]:  # cap at 30 to avoid rate limits
        t = ioc.get('type', '')
        v = ioc.get('value', '').strip()
        if not v:
            continue
        rep = {}
        if t == 'ipv4':
            rep = _vt_ip(v)
            abuse = _abuseipdb(v)
            if abuse:
                rep.update(abuse)
        elif t == 'domain':
            rep = _vt_domain(v)
        elif t in ('md5', 'sha1', 'sha256'):
            rep = _vt_hash(v)
        if rep:
            results[v] = rep

    return jsonify({'results': results})


# ── Entity Graph ──────────────────────────────────────────────────────────────────

@app.route('/graph', methods=['POST'])
@require_auth
def graph():
    """
    Build entity relationship graph from artifacts.
    Body: { "query": str, "artifacts": {source_url: {type: [values]}} }
    Returns: { "nodes": [...], "edges": [...] }
    """
    try:
        from backend.graph_builder import build_graph
    except ModuleNotFoundError:
        from graph_builder import build_graph

    body = request.get_json(force=True)
    query = body.get('query', '')
    artifacts = body.get('artifacts', {})
    result = build_graph(query, artifacts)
    return jsonify(result)


# ── Download ──────────────────────────────────────────────────────────────────

@app.route('/download/<filename>')
def download(filename):
    filename = os.path.basename(filename)  # prevent path traversal
    if not filename.endswith('.md'):
        return jsonify({"error": "Invalid file"}), 400
    filepath = os.path.join(_OUTPUT_PATH, filename)
    # Confirm resolved path is still inside _OUTPUT_PATH
    if not os.path.abspath(filepath).startswith(os.path.abspath(_OUTPUT_PATH)):
        return jsonify({"error": "Access denied"}), 403
    if not os.path.exists(filepath):
        return jsonify({"error": "File not found"}), 404
    return send_file(filepath, as_attachment=True)


# ── Watchlist Routes ──────────────────────────────────────────────────────────

@app.route('/watchlist', methods=['POST'])
@require_auth
def create_watchlist_route():
    body = request.get_json(force=True)
    name = body.get('name', '').strip()
    keywords = body.get('keywords', [])
    alert_email = body.get('alert_email')
    webhook_url = body.get('webhook_url')
    severity_threshold = body.get('severity_threshold', 35)

    if not name or not keywords:
        return jsonify({"error": "name and keywords are required"}), 400

    mgr = WatchlistManager()
    wl_id = mgr.create_watchlist(name, keywords, alert_email, webhook_url, severity_threshold)
    if wl_id == -1:
        return jsonify({"error": "Failed to create watchlist or already exists"}), 400

    log_audit(AuditAction.WATCH_CREATE, target=name, detail={"watchlist_id": wl_id})
    return jsonify({"success": True, "watchlist_id": wl_id}), 201


@app.route('/watchlist', methods=['GET'])
@require_auth
def get_all_watchlists_route():
    mgr = WatchlistManager()
    return jsonify(mgr.get_all_watchlists())


@app.route('/watchlist/<int:id>/keyword', methods=['POST'])
@require_auth
def add_keyword_route(id):
    body = request.get_json(force=True)
    keyword = body.get('keyword', '').strip()
    if not keyword:
        return jsonify({"error": "keyword is required"}), 400

    mgr = WatchlistManager()
    success = mgr.add_keyword(id, keyword)
    if not success:
        return jsonify({"error": "Failed to add keyword"}), 400

    log_audit(AuditAction.WATCH_UPDATE, target=f"watchlist_{id}", detail={"added_keyword": keyword})
    return jsonify({"success": True})


@app.route('/watchlist/<int:id>', methods=['DELETE'])
@require_auth
def remove_watchlist_route(id):
    mgr = WatchlistManager()
    success = mgr.remove_watchlist(id)
    if not success:
        return jsonify({"error": "Failed to remove watchlist"}), 400

    log_audit(AuditAction.WATCH_DELETE, target=f"watchlist_{id}")
    return jsonify({"success": True})


@app.route('/watchlist/<int:id>/alerts', methods=['GET'])
@require_auth
def get_watchlist_alerts_route(id):
    since = request.args.get('since')
    mgr = WatchlistManager()
    alerts = mgr.get_alerts(id, since_timestamp=since)
    return jsonify(alerts)


@app.route('/watchlist/<int:id>/scan', methods=['POST'])
@require_auth
def trigger_watchlist_scan_route(id):
    scheduler = MonitoringScheduler()
    # Runs the scan in a background thread to prevent endpoint blocking
    threading.Thread(target=scheduler._run_watchlist_scan, args=[id], daemon=True).start()
    log_audit(AuditAction.WATCH_TRIGGER, target=f"watchlist_{id}")
    return jsonify({"success": True, "message": "Scan triggered in background."})


# ── Actor Profiling Routes ────────────────────────────────────────────────────

@app.route('/actors', methods=['GET'])
@require_auth
def get_all_profiles_route():
    profiler = ActorProfiler()
    return jsonify(profiler.get_all_profiles())


@app.route('/actor/<int:actor_id>', methods=['GET'])
@require_auth
def get_actor_profile_route(actor_id):
    profiler = ActorProfiler()
    prof = profiler.build_profile(actor_id)
    if not prof:
        return jsonify({"error": "Profile not found"}), 404
    return jsonify(prof)


@app.route('/actor/<int:actor_id>/export', methods=['GET'])
@require_auth
def export_actor_profile_route(actor_id):
    fmt = request.args.get('format', 'json')
    profiler = ActorProfiler()
    profile_str = profiler.export_profile(actor_id, export_format=fmt)
    if profile_str == "{}":
        return jsonify({"error": "Profile not found"}), 404
    
    mime = 'application/json' if fmt == 'json' else 'application/stix+json'
    return Response(
        profile_str,
        mimetype=mime,
        headers={'Content-Disposition': f'attachment; filename=actor_profile_{actor_id}.{fmt}'}
    )


@app.route('/actor/correlate', methods=['POST'])
@require_auth
def correlate_actors_route():
    body = request.get_json(force=True)
    artifact = body.get('artifact', '').strip()
    if not artifact:
        return jsonify({"error": "artifact is required"}), 400

    profiler = ActorProfiler()
    correlations = profiler.correlate_across_sources(artifact)
    return jsonify(correlations)


# ── Dashboard Trending Routes ─────────────────────────────────────────────────

@app.route('/dashboard/trends', methods=['GET'])
@require_auth
def get_dashboard_trends_route():
    hours = request.args.get('hours', 168, type=int)
    analyzer = TrendAnalyzer()
    return jsonify(analyzer.get_trending_topics(last_n_hours=hours))


@app.route('/dashboard/sources', methods=['GET'])
@require_auth
def get_dashboard_sources_route():
    analyzer = TrendAnalyzer()
    return jsonify(analyzer.get_source_rankings())


@app.route('/dashboard/timeline', methods=['GET'])
@require_auth
def get_dashboard_timeline_route():
    granularity = request.args.get('granularity', 'daily')
    analyzer = TrendAnalyzer()
    return jsonify(analyzer.get_activity_timeline(granularity=granularity))


# ── Escalation & Certificate Routes ───────────────────────────────────────────

@app.route('/report/escalate', methods=['POST'])
@require_auth
def escalate_report_route():
    body = request.get_json(force=True)
    report_id = body.get('report_id', '').strip()
    template_type = body.get('template_type', '').strip() # fir, interpol, certin, takedown

    if not report_id or not template_type:
        return jsonify({"error": "report_id and template_type are required"}), 400

    # Retrieve stored cryptographic seal for report
    sealer = EvidenceSealer()
    seal = sealer.get_seal(report_id)
    if not seal:
        # Construct dynamic mock report for demonstration if not found
        report_dict = {
            "query": "malware database dump",
            "summary": "This is a demonstration report summary on dark web malware postings.",
            "artifacts": {
                "http://demonstration.onion": {
                    "email": ["demon@torbox.onion"],
                    "btc": ["1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"]
                }
            }
        }
    else:
        # Load from output directory matching filename
        # Since filename contains datetime, we can search the outputs folder
        report_dict = None
        outputs_dir = _OUTPUT_PATH
        for fname in os.listdir(outputs_dir):
            if fname.endswith(".md"):
                filepath = os.path.join(outputs_dir, fname)
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                # Verify SHA256 matches seal
                canonical_str = json.dumps({"summary": content}, sort_keys=True, default=str)
                computed_hash = hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()
                if computed_hash == seal["sha256_hash"] or report_id in fname:
                    report_dict = {
                        "query": "investigation query scan",
                        "summary": content,
                        "artifacts": {}
                    }
                    break

        if not report_dict:
            report_dict = {
                "query": "Drishti Scanned Intelligence findings",
                "summary": "Findings recorded under hash " + seal["sha256_hash"],
                "artifacts": {}
            }

    generator = EscalationGenerator()
    result = {}

    if template_type == "fir":
        result = generator.generate_fir_complaint(report_dict)
    elif template_type == "interpol":
        # Construct mock threat actor profile
        actor_profile = {
            "primary_handle": "DarkWebTarget",
            "linked_pseudonyms": ["DarkWebTarget", "AnonymTarget"],
            "threat_level": 75,
            "writing_style": {"avg_sentence_length": 14, "common_phrases": ["escrow", "price"]},
            "ttp_tags": ["T1486", "T1567"],
            "linked_iocs": {"email": ["target@torbox.onion"], "btc": ["1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"]}
        }
        result = generator.generate_interpol_notice(actor_profile)
    elif template_type == "certin":
        result = generator.generate_cert_in_report(report_dict)
    elif template_type == "takedown":
        result = generator.generate_takedown_request("http://infringing-source.onion", report_dict["summary"][:500])
    else:
        return jsonify({"error": "Unsupported template_type"}), 400

    log_audit(AuditAction.EXPORT, target=report_id, detail={"template_type": template_type})
    return jsonify({
        "success": True,
        "message": f"Escalation report draft generated successfully for {template_type}.",
        "paths": result
    })


@app.route('/forensics/seals', methods=['GET'])
@require_auth
def get_all_seals_route():
    sealer = EvidenceSealer()
    try:
        with sealer._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM evidence_seals ORDER BY timestamp DESC")
            seals = [dict(row) for row in cursor.fetchall()]
        return jsonify(seals)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/forensics/verify/<report_id>', methods=['POST'])
@require_auth
def verify_forensics_route(report_id):
    body = request.get_json(force=True)
    report_dict = body.get('report_dict')
    if not report_dict:
        return jsonify({"error": "report_dict is required"}), 400

    sealer = EvidenceSealer()
    seal = sealer.get_seal(report_id)
    if not seal:
        return jsonify({"verified": False, "message": "Forensic seal not found"}), 404

    verified = sealer.verify_report(report_dict, seal)
    return jsonify({
        "verified": verified,
        "message": "Evidence seal matches perfectly. Integrity intact." if verified else "Warning! Evidence hash mismatch detected. Report altered!"
    })


@app.route('/forensics/certificate/<report_id>', methods=['GET'])
@require_auth
def download_certificate_route(report_id):
    sealer = EvidenceSealer()
    seal = sealer.get_seal(report_id)
    if not seal:
        return jsonify({"error": "Seal not found"}), 404

    filename = f"certificate_65B_{report_id}.pdf"
    filepath = os.path.join(_OUTPUT_PATH, filename)
    success = sealer.export_certificate(report_id, filepath)
    if not success:
        # Try returning fallback markdown certificate
        md_filepath = filepath.replace(".pdf", ".md")
        if os.path.exists(md_filepath):
            return send_file(md_filepath, as_attachment=True)
        return jsonify({"error": "Failed to generate certificate"}), 500

    return send_file(filepath, as_attachment=True)


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == '__main__':
    os.makedirs(_OUTPUT_PATH, exist_ok=True)

    # Initialize database and default admin user
    init_db()
    init_default_admin()
    
    # Start background watchlists scanning scheduler
    try:
        global_scheduler = MonitoringScheduler()
        global_scheduler.start()
    except Exception as sched_ex:
        logger.error(f"Failed to start background scheduler: {sched_ex}")

    log_audit(AuditAction.SYSTEM_START, target=f"http://{FLASK_HOST}:{FLASK_PORT}")

    logger.info(f"Starting DRISHTI on http://{FLASK_HOST}:{FLASK_PORT}")
    logger.info(f"Authentication: {'ENABLED' if AUTH_ENABLED else 'DISABLED (set AUTH_ENABLED=true in .env)'}")
    app.run(debug=FLASK_DEBUG, host=FLASK_HOST, port=FLASK_PORT, threaded=True)
