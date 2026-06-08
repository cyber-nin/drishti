"""
Async scraper using aiohttp for faster concurrent page fetching.
Drop-in replacement for scrape.scrape_multiple with better performance.
"""
import asyncio
import random
import logging
from typing import Dict, Tuple
from bs4 import BeautifulSoup

try:
    import aiohttp
    from aiohttp_socks import ProxyConnector
    _AIOHTTP_AVAILABLE = True
except ImportError:
    _AIOHTTP_AVAILABLE = False

try:
    from backend.config import SCRAPE_REQUEST_TIMEOUT, SCRAPE_MAX_CHARS
    from backend.artifact_extractor import ArtifactExtractor
except ModuleNotFoundError:
    from config import SCRAPE_REQUEST_TIMEOUT, SCRAPE_MAX_CHARS
    from artifact_extractor import ArtifactExtractor



logger = logging.getLogger(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/135.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/135.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:137.0) Gecko/20100101 Firefox/137.0",
]

TOR_PROXY = "socks5h://127.0.0.1:9050"


async def _fetch_one(session: "aiohttp.ClientSession", url_data: dict) -> Tuple[str, str, dict]:
    url = url_data["link"]
    title = url_data.get("title", "")
    use_tor = ".onion" in url
    proxy = TOR_PROXY if use_tor else None
    headers = {"User-Agent": random.choice(USER_AGENTS)}

    try:
        async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=SCRAPE_REQUEST_TIMEOUT)) as resp:
            if resp.status == 200:
                html = await resp.text(errors="replace")
                soup = BeautifulSoup(html, "html.parser")
                text = title + soup.get_text().replace("\n", " ").replace("\r", "")
            else:
                text = title
    except Exception as e:
        logger.debug(f"Async scrape failed for {url}: {e}")
        text = title

    if len(text) > SCRAPE_MAX_CHARS:
        text = text[:SCRAPE_MAX_CHARS]

    extractor = ArtifactExtractor()
    artifacts = extractor.extract(text)
    return url, text, artifacts


async def _scrape_all(urls_data: list) -> Tuple[Dict[str, str], Dict[str, dict]]:
    has_onion = any(".onion" in u["link"] for u in urls_data)
    if has_onion:
        connector = ProxyConnector.from_url(TOR_PROXY, ssl=False)
    else:
        connector = aiohttp.TCPConnector(ssl=False, limit=20)

    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [_fetch_one(session, u) for u in urls_data]
        results_raw = await asyncio.gather(*tasks, return_exceptions=True)

    scraped, all_artifacts = {}, {}
    for item in results_raw:
        if isinstance(item, Exception):
            logger.debug(f"Async scrape task error: {item}")
            continue
        url, text, artifacts = item
        scraped[url] = text
        all_artifacts[url] = artifacts

    return scraped, all_artifacts


def scrape_multiple_async(urls_data: list, **kwargs) -> Tuple[Dict[str, str], Dict[str, dict]]:
    """
    Async drop-in replacement for scrape.scrape_multiple.
    Falls back to sync scraper if aiohttp is not installed.
    """
    if not _AIOHTTP_AVAILABLE:
        logger.warning("aiohttp not installed, falling back to sync scraper. Run: pip install aiohttp")
        try:
            from backend.scrape import scrape_multiple
        except ModuleNotFoundError:
            from scrape import scrape_multiple
        return scrape_multiple(urls_data, **kwargs)

    try:
        try:
            # Check if there is an active running event loop
            asyncio.get_running_loop()
            # Loop is already running — run coroutine in a separate executor thread
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, _scrape_all(urls_data))
                return future.result()
        except RuntimeError:
            # No running event loop in this thread — safely spawn and manage one via asyncio.run
            return asyncio.run(_scrape_all(urls_data))
    except Exception as e:
        logger.warning(f"Async scraper failed, falling back to sync: {e}")
        try:
            from backend.scrape import scrape_multiple
        except ModuleNotFoundError:
            from scrape import scrape_multiple
        return scrape_multiple(urls_data, **kwargs)
