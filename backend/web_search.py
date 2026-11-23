import socket
import time
import urllib.request
import urllib.parse
import json
import re
from typing import List, Dict, Tuple, Optional, Any
from html.parser import HTMLParser

class HTMLTagStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
    def handle_data(self, data):
        self.parts.append(data)
    def get_text(self) -> str:
        return "".join(self.parts).strip()

def strip_html_tags(html_str: str) -> str:
    """Removes HTML tags and entities from string."""
    if not html_str:
        return ""
    try:
        stripper = HTMLTagStripper()
        stripper.feed(html_str)
        text = stripper.get_text()
        text = text.replace("&quot;", '"').replace("&amp;", "&").replace("&#39;", "'").replace("&lt;", "<").replace("&gt;", ">").replace("&nbsp;", " ")
        return re.sub(r'\s+', ' ', text).strip()
    except Exception:
        clean = re.sub(r'<[^>]+>', '', html_str)
        return re.sub(r'\s+', ' ', clean).strip()

_online_cache: Dict[str, Any] = {"status": None, "timestamp": 0.0, "latency": 0.0}

def check_internet_connectivity(timeout: float = 1.5, cache_seconds: float = 8.0) -> Tuple[bool, float]:
    """
    Checks if the system currently has live internet access.
    Caches the result for short intervals to prevent network lag on consecutive tokens.
    Returns (is_online, latency_ms).
    """
    now = time.time()
    if _online_cache["status"] is not None and (now - _online_cache["timestamp"]) < cache_seconds:
        return _online_cache["status"], _online_cache["latency"]

    start = time.time()
    # Try quick connection to Cloudflare DNS 1.1.1.1
    try:
        s = socket.create_connection(("1.1.1.1", 53), timeout=timeout)
        s.close()
        latency = round((time.time() - start) * 1000, 1)
        _online_cache.update({"status": True, "timestamp": now, "latency": latency})
        return True, latency
    except Exception:
        # Fallback to Google DNS 8.8.8.8
        try:
            s = socket.create_connection(("8.8.8.8", 53), timeout=timeout)
            s.close()
            latency = round((time.time() - start) * 1000, 1)
            _online_cache.update({"status": True, "timestamp": now, "latency": latency})
            return True, latency
        except Exception:
            _online_cache.update({"status": False, "timestamp": now, "latency": 0.0})
            return False, 0.0

def search_bing(query: str, max_results: int = 5) -> List[Dict[str, str]]:
    """
    Scrapes organic search results from Bing with zero API key required.
    Returns title, url, domain, and snippet.
    """
    encoded_query = urllib.parse.quote(query)
    url = f"https://www.bing.com/search?q={encoded_query}&setlang=en"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9"
    }
    req = urllib.request.Request(url, headers=headers)
    results = []

    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            html = resp.read().decode('utf-8', errors='ignore')

        # Each result in Bing is enclosed in a block with class b_algo
        blocks = re.findall(r'<li[^>]*class="[^"]*b_algo[^"]*"[^>]*>(.*?)(?:</li>|(?=<li[^>]*class="[^"]*b_algo))', html, re.DOTALL)
        
        for b in blocks:
            h2 = re.search(r'<h2[^>]*>\s*<a\s+[^>]*href="([^"]+)"[^>]*>(.*?)</a>', b, re.DOTALL)
            if not h2:
                continue
            
            raw_url = h2.group(1).replace("&amp;", "&")
            title = strip_html_tags(h2.group(2))
            
            # Find snippet
            p = re.search(r'<p[^>]*class="[^"]*b_lineclamp[^"]*"[^>]*>(.*?)</p>', b, re.DOTALL)
            if not p:
                p = re.search(r'<p[^>]*>(.*?)</p>', b, re.DOTALL)
            snippet = strip_html_tags(p.group(1)) if p else ""

            # Find clean display domain from cite
            cite = re.search(r'<cite[^>]*>(.*?)</cite>', b, re.DOTALL)
            source_domain = strip_html_tags(cite.group(1)) if cite else ""
            if not source_domain and "://" in raw_url:
                source_domain = raw_url.split("://")[1].split("/")[0]

            if title and (snippet or source_domain):
                results.append({
                    "title": title,
                    "url": raw_url,
                    "source": source_domain or "Web Source",
                    "snippet": snippet or title
                })
                if len(results) >= max_results:
                    break

    except Exception as e:
        # Bing scrape error, will fallback
        pass

    return results

def search_wikipedia(query: str, max_results: int = 3) -> List[Dict[str, str]]:
    """
    Queries Wikimedia REST API for direct encyclopedic information.
    Zero authentication needed.
    """
    clean_query = query.strip()
    url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote(clean_query)}&format=json&utf8=1"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "NooraAI-LAN-Server/1.0 (https://github.com/nadeemmhdm/Noora-LAN-AI-Server)"}
    )
    results = []
    try:
        with urllib.request.urlopen(req, timeout=4) as resp:
            data = json.loads(resp.read().decode())
            search_items = data.get("query", {}).get("search", [])
            for item in search_items[:max_results]:
                title = item.get("title", "")
                snippet = strip_html_tags(item.get("snippet", ""))
                article_url = f"https://en.wikipedia.org/wiki/{urllib.parse.quote(title.replace(' ', '_'))}"
                results.append({
                    "title": title,
                    "url": article_url,
                    "source": "Wikipedia",
                    "snippet": snippet
                })
    except Exception:
        pass
    return results

def search_duckduckgo_api(query: str) -> List[Dict[str, str]]:
    """
    Queries DuckDuckGo Instant Answer API for quick definitions and topics.
    """
    url = f"https://api.duckduckgo.com/?q={urllib.parse.quote(query)}&format=json&no_html=1"
    req = urllib.request.Request(url, headers={"User-Agent": "NooraAI/1.0"})
    results = []
    try:
        with urllib.request.urlopen(req, timeout=4) as resp:
            data = json.loads(resp.read().decode())
            if data.get("AbstractText"):
                results.append({
                    "title": data.get("Heading", "Overview"),
                    "url": data.get("AbstractURL", ""),
                    "source": "DuckDuckGo Instant Answer",
                    "snippet": data.get("AbstractText")
                })
            for topic in data.get("RelatedTopics", [])[:3]:
                if isinstance(topic, dict) and topic.get("Text") and topic.get("FirstURL"):
                    title = topic.get("FirstURL", "").split("/")[-1].replace("_", " ") or "Topic"
                    results.append({
                        "title": title,
                        "url": topic.get("FirstURL", ""),
                        "source": "DuckDuckGo",
                        "snippet": topic.get("Text")
                    })
    except Exception:
        pass
    return results

def clean_search_query(prompt: str) -> str:
    """Strips conversational prefixes so the search query is focused and effective."""
    if not prompt:
        return ""
    p = prompt.strip()
    prefixes = [
        r"^(please\s+)?search\s+(the\s+web\s+|online\s+)?(for|about)?\s*",
        r"^(can\s+you\s+)?(please\s+)?find\s+(online|on\s+the\s+web)?\s*(for|about)?\s*",
        r"^(can\s+you\s+)?tell\s+me\s+(about\s+)?",
        r"^what\s+is\s+the\s+latest\s+(news\s+|updates?\s+)?(on|about)?\s*",
        r"^what\s+are\s+the\s+latest\s+news\s+(on|about)?\s*",
        r"^look\s+up\s*",
        r"^browse\s+for\s*"
    ]
    for pattern in prefixes:
        p = re.sub(pattern, "", p, flags=re.IGNORECASE).strip()
    return p if len(p) > 2 else prompt

def perform_web_search(query: str, max_results: int = 4) -> Dict[str, Any]:
    """
    Master web search function.
    Validates online status, executes primary and fallback searches, and returns unified results.
    """
    online, latency = check_internet_connectivity()
    if not online:
        return {
            "online": False,
            "query": query,
            "results": [],
            "source": "offline",
            "message": "No internet connection detected. Server running in offline mode."
        }

    search_term = clean_search_query(query)
    # 1. Primary search: Bing
    results = search_bing(search_term, max_results=max_results)

    # 2. If 0 results, fallback to Wikipedia or DuckDuckGo API
    if not results:
        results = search_wikipedia(search_term, max_results=max_results)
    if not results:
        results = search_duckduckgo_api(search_term)

    return {
        "online": True,
        "latency_ms": latency,
        "query": search_term,
        "original_prompt": query,
        "results": results,
        "count": len(results),
        "source": "online_search" if results else "no_results_found"
    }

SEARCH_TRIGGER_KEYWORDS = [
    "latest", "current", "news", "today", "yesterday", "recently", "recent",
    "2024", "2025", "2026", "weather", "score", "winner", "stock", "price",
    "who won", "who is the current", "what happened", "search", "browse",
    "find online", "update", "release date", "schedule", "election", "championship",
    "market cap", "top headlines", "what is new", "newest"
]

def should_trigger_web_search(prompt: str) -> bool:
    """Detects whether a user prompt likely requires real-time / current web information."""
    if not prompt:
        return False
    p = prompt.lower()
    return any(kw in p for kw in SEARCH_TRIGGER_KEYWORDS)

def format_search_context(search_data: Dict[str, Any]) -> str:
    """Formats retrieved web results into a clean system instruction context."""
    results = search_data.get("results", [])
    if not results:
        return ""

    query = search_data.get("query", "")
    lines = [
        f"[ONLINE LIVE WEB SEARCH CONTEXT FOR '{query}']",
        "The following real-time web search results were retrieved online. Use them to provide accurate, up-to-date facts:",
        ""
    ]

    for idx, r in enumerate(results, 1):
        title = r.get("title", "Untitled")
        source = r.get("source", "Web")
        snippet = r.get("snippet", "")
        url = r.get("url", "")
        lines.append(f"[{idx}] {title} ({source})")
        if url:
            lines.append(f"    URL: {url}")
        lines.append(f"    Summary: {snippet}")
        lines.append("")

    lines.append("Instructions: Synthesize the above live search information to answer the question directly. Cite your sources clearly when referring to facts.")
    return "\n".join(lines)
