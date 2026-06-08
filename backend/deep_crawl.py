import random
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
try:
    from backend.config import CRAWL_REQUEST_TIMEOUT
    from backend.artifact_extractor import ArtifactExtractor
except ModuleNotFoundError:
    from config import CRAWL_REQUEST_TIMEOUT
    from artifact_extractor import ArtifactExtractor

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/135.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/135.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:137.0) Gecko/20100101 Firefox/137.0",
]

def deep_crawl(url, max_depth=2, max_pages=20):
    """Deep crawl a website and extract all artifacts. Yields progress updates."""

    if not url or not url.startswith('http'):
        yield {"type": "log", "message": f"Invalid URL: {url}"}
        yield {"type": "result", "data": {}}
        return

    use_tor = '.onion' in url
    session = requests.Session()
    if use_tor:
        session.proxies = {
            'http': 'socks5h://127.0.0.1:9050',
            'https': 'socks5h://127.0.0.1:9050'
        }

    extractor = ArtifactExtractor()
    combined_artifacts = {}
    links = set()

    visited = set()
    queued = set()  # track what's already in to_visit to avoid duplicates
    to_visit = [(url, 0)]
    queued.add(url)
    pages_crawled = 0

    yield {"type": "progress", "message": f"Starting crawl of {url} (Depth: {max_depth})"}

    while to_visit and pages_crawled < max_pages:
        current_url, depth = to_visit.pop(0)

        if current_url in visited or depth > max_depth:
            continue

        visited.add(current_url)
        pages_crawled += 1

        yield {"type": "progress", "message": f"Crawling {current_url} ({pages_crawled}/{max_pages})..."}

        try:
            headers = {"User-Agent": random.choice(USER_AGENTS)}
            response = session.get(current_url, headers=headers, timeout=CRAWL_REQUEST_TIMEOUT)
            soup = BeautifulSoup(response.text, 'html.parser')

            # Use ArtifactExtractor for accurate, consistent extraction
            page_artifacts = extractor.extract(response.text)
            for artifact_type, values in page_artifacts.items():
                combined_artifacts.setdefault(artifact_type, set()).update(values)

            # Extract JS files
            for script in soup.find_all('script', src=True):
                js_url = urljoin(current_url, script['src'])
                combined_artifacts.setdefault('js_files', set()).add(js_url)

            # Extract forms
            combined_artifacts.setdefault('forms', [])
            for form in soup.find_all('form'):
                combined_artifacts['forms'].append({
                    'action': form.get('action', ''),
                    'method': form.get('method', 'get'),
                    'inputs': [inp.get('name', '') for inp in form.find_all('input')]
                })

            # Collect internal links and queue unvisited ones
            if depth < max_depth:
                base_netloc = urlparse(url).netloc
                for link in soup.find_all('a', href=True):
                    next_url = urljoin(current_url, link['href'])
                    if urlparse(next_url).netloc == base_netloc:
                        links.add(next_url)
                        if next_url not in visited and next_url not in queued:
                            queued.add(next_url)
                            to_visit.append((next_url, depth + 1))

        except Exception as e:
            yield {"type": "log", "message": f"Error crawling {current_url}: {str(e)}"}
            continue

    # Serialize: convert sets to lists, keep forms as-is
    final_artifacts = {}
    for k, v in combined_artifacts.items():
        if isinstance(v, set):
            final_artifacts[k] = list(v)
        else:
            final_artifacts[k] = v
    final_artifacts['links'] = list(links)

    yield {"type": "result", "data": final_artifacts}
