"""
Clearnet OSINT search adapters.
Supplements dark web results with open-web intelligence sources.
Each adapter returns a list of {"title": str, "link": str} dicts.
"""
import requests
import logging
import random
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

_TIMEOUT = 15
_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/135.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/135.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:137.0) Gecko/20100101 Firefox/137.0",
]


def _headers():
    return {"User-Agent": random.choice(_USER_AGENTS)}


def search_pastebin(query: str, max_results: int = 10) -> list:
    """
    Search Pastebin via Google dork: site:pastebin.com <query>
    Returns list of {title, link} dicts.
    """
    results = []
    try:
        search_url = f"https://www.google.com/search?q=site:pastebin.com+{requests.utils.quote(query)}&num={max_results}"
        resp = requests.get(search_url, headers=_headers(), timeout=_TIMEOUT)
        soup = BeautifulSoup(resp.text, 'html.parser')
        for a in soup.select('a[href]'):
            href = a['href']
            if 'pastebin.com/' in href and '/search' not in href:
                # Google wraps links — extract actual URL
                if href.startswith('/url?q='):
                    href = href.split('/url?q=')[1].split('&')[0]
                title = a.get_text(strip=True) or href
                if href not in [r['link'] for r in results]:
                    results.append({"title": f"[Pastebin] {title}", "link": href})
                if len(results) >= max_results:
                    break
    except Exception as e:
        logger.debug(f"Pastebin search failed: {e}")
    return results


def search_github(query: str, max_results: int = 10) -> list:
    """
    Search GitHub code via Google dork: site:github.com <query>
    Useful for leaked credentials, API keys, and malware samples.
    """
    results = []
    try:
        search_url = f"https://www.google.com/search?q=site:github.com+{requests.utils.quote(query)}&num={max_results}"
        resp = requests.get(search_url, headers=_headers(), timeout=_TIMEOUT)
        soup = BeautifulSoup(resp.text, 'html.parser')
        for a in soup.select('a[href]'):
            href = a['href']
            if 'github.com/' in href and 'google.com' not in href:
                if href.startswith('/url?q='):
                    href = href.split('/url?q=')[1].split('&')[0]
                if not href.startswith('http'):
                    continue
                title = a.get_text(strip=True) or href
                if href not in [r['link'] for r in results]:
                    results.append({"title": f"[GitHub] {title}", "link": href})
                if len(results) >= max_results:
                    break
    except Exception as e:
        logger.debug(f"GitHub search failed: {e}")
    return results


def search_clearnet_osint(query: str, max_results: int = 10) -> list:
    """
    Aggregate results from all clearnet OSINT adapters.
    Returns combined deduplicated list.
    """
    combined = []
    seen = set()

    for adapter in (search_pastebin, search_github):
        try:
            for item in adapter(query, max_results=max_results // 2):
                if item['link'] not in seen:
                    seen.add(item['link'])
                    combined.append(item)
        except Exception as e:
            logger.debug(f"Adapter {adapter.__name__} failed: {e}")

    return combined[:max_results]
