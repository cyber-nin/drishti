import random
import requests
import threading
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
try:
    from backend.artifact_extractor import ArtifactExtractor
except ModuleNotFoundError:
    from artifact_extractor import ArtifactExtractor

try:
    from backend.config import SCRAPE_REQUEST_TIMEOUT, SCRAPE_MAX_CHARS
    from backend.tor_manager import get_proxies_and_rotate_if_needed
except ModuleNotFoundError:
    from config import SCRAPE_REQUEST_TIMEOUT, SCRAPE_MAX_CHARS
    from tor_manager import get_proxies_and_rotate_if_needed

import warnings
warnings.filterwarnings("ignore")

# Define a list of rotating user agents.
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:137.0) Gecko/20100101 Firefox/137.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.7; rv:137.0) Gecko/20100101 Firefox/137.0",
    "Mozilla/5.0 (X11; Linux i686; rv:137.0) Gecko/20100101 Firefox/137.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_7_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.3 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36 Edg/135.0.3179.54",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36 Edg/135.0.3179.54"
]

# Global counter and lock for thread-safe Tor rotation
request_counter = 0
counter_lock = threading.Lock()

def scrape_single(url_data, rotate=False, rotate_interval=5, control_port=9051, control_password=None, verbose=False):
    """
    Scrapes a single URL.
    If the URL is an onion site, routes the request through Tor.
    Returns a tuple (url, scraped_text, artifacts).
    """
    url = url_data['link']
    use_tor = ".onion" in url
    proxies = get_proxies_and_rotate_if_needed() if use_tor else None
    headers = {
        "User-Agent": random.choice(USER_AGENTS)
    }
    
    if verbose:
        print(f"[VERBOSE] Scraping: {url}")
    
    try:
        response = requests.get(url, headers=headers, proxies=proxies, timeout=SCRAPE_REQUEST_TIMEOUT)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            scraped_text = url_data['title'] + soup.get_text().replace('\n', ' ').replace('\r', '')
            if verbose:
                print(f"[VERBOSE] [+] Success: {url} ({len(scraped_text)} chars)")
        else:
            scraped_text = url_data['title']
            if verbose:
                print(f"[VERBOSE] [-] Failed: {url} (Status: {response.status_code})")
    except Exception as e:
        scraped_text = url_data['title']
        if verbose:
            print(f"[VERBOSE] [-] Error: {url} ({str(e)[:50]})")
    
    # Extract artifacts
    extractor = ArtifactExtractor()
    artifacts = extractor.extract(scraped_text)
    
    return url, scraped_text, artifacts

def scrape_multiple(urls_data, max_workers=5, verbose=False):
    """
    Scrapes multiple URLs concurrently using a thread pool.
    
    Parameters:
      - urls_data: list of URLs to scrape.
      - max_workers: number of concurrent threads for scraping.
      - verbose: enable verbose output.
    
    Returns:
      A tuple (results, all_artifacts) where results maps URLs to content
      and all_artifacts maps URLs to extracted artifacts.
    """
    results = {}
    all_artifacts = {}
    
    if verbose:
        print(f"\n[VERBOSE] Starting scrape of {len(urls_data)} URLs with {max_workers} workers...\n")
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_url = {
            executor.submit(scrape_single, url_data, verbose=verbose): url_data
            for url_data in urls_data
        }
        for future in as_completed(future_to_url):
            url, content, artifacts = future.result()
            if len(content) > SCRAPE_MAX_CHARS:
                content = content[:SCRAPE_MAX_CHARS]
            results[url] = content
            all_artifacts[url] = artifacts
    
    if verbose:
        print(f"\n[VERBOSE] Scraping complete. {len(results)} URLs processed.\n")
    
    return results, all_artifacts