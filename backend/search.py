import requests
import random, re
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    from backend.config import (
        SEARCH_ENGINE_COOLDOWN_MINUTES,
        SEARCH_ENGINE_MAX_FAILURES,
        SEARCH_REQUEST_TIMEOUT,
        SEARCH_STUB_RESULTS_ENABLED
    )
    from backend.tor_manager import get_proxies_and_rotate_if_needed
except ModuleNotFoundError:
    from config import (
        SEARCH_ENGINE_COOLDOWN_MINUTES,
        SEARCH_ENGINE_MAX_FAILURES,
        SEARCH_REQUEST_TIMEOUT,
        SEARCH_STUB_RESULTS_ENABLED
    )
    from tor_manager import get_proxies_and_rotate_if_needed

import warnings
warnings.filterwarnings("ignore")

try:
    from clearnet_search import search_clearnet_osint
except ModuleNotFoundError:
    try:
        from backend.clearnet_search import search_clearnet_osint
    except ModuleNotFoundError:
        search_clearnet_osint = None

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

SEARCH_ENGINE_ENDPOINTS = [
    "http://juhanurmihxlp77nkq76byazcldy2hlmovfu2epvl5ankdibsot4csyd.onion/search/?q={query}", # Ahmia
    "http://3bbad7fauom4d6sgppalyqddsqbf5u5p56b5k5uk2zxsy3d6ey2jobad.onion/search?q={query}", # OnionLand
    "http://darkhuntyla64h75a3re5e2l3367lqn7ltmdzpgmr6b4nbz3q2iaxrid.onion/search?q={query}", # DarkRunt
    "http://iy3544gmoeclh5de6gez2256v6pjh4omhpqdh2wpeeppjtvqmjhkfwad.onion/torgle/?query={query}", # Torgle
    "http://amnesia7u5odx5xbwtpnqk3edybgud5bmiagu75bnqx2crntw5kry7ad.onion/search?query={query}", # Amnesia
    "http://kaizerwfvp5gxu6cppibp7jhcqptavq3iqef66wbxenh6a2fklibdvid.onion/search?q={query}", # Kaizer
    "http://anima4ffe27xmakwnseih3ic2y7y3l6e7fucwk4oerdn4odf7k74tbid.onion/search?q={query}", # Anima
    "http://tornadoxn3viscgz647shlysdy7ea5zqzwda7hierekeuokh5eh5b3qd.onion/search?q={query}", # Tornado
    "http://tornetupfu7gcgidt33ftnungxzyfq2pygui5qdoyss34xbgx2qruzid.onion/search?q={query}", # TorNet
    "http://torlbmqwtudkorme6prgfpmsnile7ug2zm4u3ejpcncxuhpu4k2j4kyd.onion/index.php?a=search&q={query}", # Torland
    "http://findtorroveq5wdnipkaojfpqulxnkhblymc7aramjzajcvpptd4rjqd.onion/search?q={query}", # Find Tor
    "http://2fd6cemt4gmccflhm6imvdfvli3nf7zn6rfrwpsy7uhxrgbypvwf5fad.onion/search?query={query}", # Excavator    
    "http://oniwayzz74cv2puhsgx4dpjwieww4wdphsydqvf5q7eyz4myjvyw26ad.onion/search.php?s={query}", # Onionway
    "http://tor66sewebgixwhcqfnp5inzp5x5uohhdy3kvtnyfxc2e5mxiuh34iid.onion/search?q={query}", # Tor66
    "http://3fzh7yuupdfyjhwt3ugzqqof6ulbcl27ecev33knxe3u7goi3vfn2qqd.onion/oss/index.php?search={query}", # OSS (Onion Search Server)
]

SEARCH_ENGINE_STATUS = {
    endpoint: {
        "ok": True,
        "failures": 0,
        "last_try": None
    }
    for endpoint in SEARCH_ENGINE_ENDPOINTS
}


def fetch_search_results(endpoint, query):
    url = endpoint.format(query=query)
    headers = {
        "User-Agent": random.choice(USER_AGENTS)
    }
    proxies = get_proxies_and_rotate_if_needed()
    try:
        response = requests.get(url, headers=headers, proxies=proxies, timeout=SEARCH_REQUEST_TIMEOUT)
        if response.status_code == 200:
            SEARCH_ENGINE_STATUS[endpoint].update({"ok": True, "failures": 0, "last_try": datetime.now()})
            soup = BeautifulSoup(response.text, "html.parser")
            links = []
            for a in soup.find_all('a'):
                try:
                    href = a['href']
                    title = a.get_text(strip=True)
                    link = re.findall(r'https?:\/\/[^\/]*\.onion.*', href)
                    if len(link) != 0:
                        links.append({"title": title, "link": link[0]})
                except Exception:
                    continue
            return links
        else:
            failure_data = SEARCH_ENGINE_STATUS[endpoint]
            failure_data['failures'] += 1
            failure_data['last_try'] = datetime.now()
            if failure_data['failures'] >= SEARCH_ENGINE_MAX_FAILURES:
                failure_data['ok'] = False
            return []
    except Exception:
        failure_data = SEARCH_ENGINE_STATUS[endpoint]
        failure_data['failures'] += 1
        failure_data['last_try'] = datetime.now()
        if failure_data['failures'] >= SEARCH_ENGINE_MAX_FAILURES:
            failure_data['ok'] = False
        return []

def _select_active_endpoints(max_count):
    now = datetime.now()
    active = []

    for endpoint, status in SEARCH_ENGINE_STATUS.items():
        if status.get("ok", False):
            active.append(endpoint)
        else:
            last_try = status.get("last_try")
            if last_try and now - last_try > timedelta(minutes=SEARCH_ENGINE_COOLDOWN_MINUTES):
                status.update({"ok": True, "failures": 0})
                active.append(endpoint)

    if not active:
        active = list(SEARCH_ENGINE_ENDPOINTS)

    return active[:max_count]


def get_search_results(refined_query, max_workers=5):
    results = []
    endpoints = _select_active_endpoints(max_workers)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(fetch_search_results, endpoint, refined_query)
                   for endpoint in endpoints]
        for future in as_completed(futures):
            result_urls = future.result() or []
            results.extend(result_urls)

    # If no results from active endpoints, try all endpoints once more
    if not results:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(fetch_search_results, endpoint, refined_query)
                       for endpoint in SEARCH_ENGINE_ENDPOINTS]
            for future in as_completed(futures):
                result_urls = future.result() or []
                results.extend(result_urls)

    # Supplement with clearnet OSINT sources
    if search_clearnet_osint:
        try:
            clearnet_results = search_clearnet_osint(refined_query, max_results=10)
            results.extend(clearnet_results)
        except Exception as e:
            import logging
            logging.getLogger(__name__).debug(f"Clearnet search failed: {e}")

    # Deduplicate results based on the link.
    seen_links = set()
    unique_results = []
    for res in results:
        link = res.get("link")
        if link and link not in seen_links:
            seen_links.add(link)
            unique_results.append(res)

    # Provide a stub for demo if no data at all and stub mode is enabled.
    if not unique_results and SEARCH_STUB_RESULTS_ENABLED:
        unique_results = [
            {"title": "Ransomware leak posting sample", "link": "http://example.onion/sample1"},
            {"title": "Ransomware negotiation data sample", "link": "http://example.onion/sample2"},
        ]

    return unique_results