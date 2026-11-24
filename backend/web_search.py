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

TYPO_FIXES = {
    r"\binda\b": "India",
    r"\bindai\b": "India",
    r"\bpresidant\b": "president",
    r"\bpresedent\b": "president",
    r"\bminiter\b": "minister",
    r"\bcurren\b": "current",
}

def clean_search_query(prompt: str) -> str:
    """Strips conversational prefixes and normalizes common typos so the search query is focused and effective."""
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
        r"^browse\s+for\s*",
        r"\bplease\b"
    ]
    for pattern in prefixes:
        p = re.sub(pattern, "", p, flags=re.IGNORECASE).strip()

    for typo_pattern, replacement in TYPO_FIXES.items():
        p = re.sub(typo_pattern, replacement, p, flags=re.IGNORECASE)

    # Normalize leader/officeholder queries for search engines (e.g. "current president of India" -> "who is the President of India")
    p = re.sub(
        r"^(who\s+is\s+)?(the\s+)?current\s+(president|prime\s+minister|pm|ceo|governor|chief\s+minister|cm|monarch|king|queen)\s+of\s+",
        r"who is the \3 of ",
        p,
        flags=re.IGNORECASE
    )
    p = re.sub(
        r"^current\s+(president|prime\s+minister|pm|ceo|governor|chief\s+minister|cm|monarch|king|queen)\s+of\s+",
        r"who is the \1 of ",
        p,
        flags=re.IGNORECASE
    )

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

# ----------------- Intelligent AI Search Intent Classification -----------------

# 1. Queries that must NEVER trigger web search (Foundational knowledge, greetings, coding, math)
EXCLUSION_PATTERNS = [
    # Greetings, identity, small talk, pleasantries
    r"^(hi|hello|hey|howdy|greetings|good\s+(morning|afternoon|evening|night)|how\s+are\s+you|what'?s\s+up|yo)\b",
    r"^(who\s+are\s+you|who\s+(created|made|trained|developed)\s+you|what\s+is\s+your\s+name|introduce\s+yourself)\b",
    r"^(thank\s+you|thanks|bye|goodbye|see\s+you|have\s+a\s+good\s+day)\b",
    r"^(tell\s+me\s+a\s+joke|make\s+me\s+laugh|who\s+is\s+nadeem|what\s+is\s+noora)\b",

    # Pure programming, coding, debugging, algorithms
    r"^(write|create|implement|code|generate|debug|fix|refactor)\s+(a\s+|an\s+)?(python|javascript|typescript|c\+\+|c#|java|rust|go|html|css|sql|bash|powershell|script|function|class|method|component|algorithm|regex|query|unit\s+test)\b",
    r"^(how\s+to\s+)?(reverse\s+a\s+string|sort\s+an\s+array|invert\s+a\s+binary\s+tree|implement\s+binary\s+search|parse\s+json|read\s+a\s+file|create\s+a\s+promise)\b",
    r"^(explain|what\s+is)\s+(recursion|polymorphism|inheritance|encapsulation|dependency\s+injection|asynchronous\s+programming|closure|hoisting|pointers?|linked\s+list|stack|queue|binary\s+tree|hash\s+map)\b",
    r"^syntax\s+of\s+",
    r"^(find|fix)\s+(the\s+)?(bug|error|issue|exception)\s+in\s+",

    # Math, arithmetic, logic calculations
    r"^(calculate|compute|solve|evaluate)\s+[\d\s\+\-\*\/\^\(\)\.\%]+$",
    r"^what\s+is\s+\d+\s*[\+\-\*\/]\s*\d+",
    r"^solve\s+(the\s+equation|for\s+[a-z])\b",
    r"^(is\s+\d+\s+a\s+prime|prime\s+factors\s+of|square\s+root\s+of)\b",

    # Text editing, summarization, proofreading, creative writing
    r"^(summarize|rewrite|paraphrase|proofread|correct\s+grammar)\s+(this|the\s+following|the\s+below)[\s:]",
    r"^translate\s+(this|the\s+following)[\s:].+into\s+[a-z]+",
    r"^write\s+(a\s+|an\s+)?(poem|story|essay|cover\s+letter|email|haiku|speech|song|dialogue)\b",

    # Timeless science concepts and foundational general knowledge
    r"^(what\s+is|explain)\s+(photosynthesis|gravity|quantum\s+mechanics|mitosis|the\s+water\s+cycle|the\s+speed\s+of\s+light|newton'?s\s+laws?|theory\s+of\s+relativity|pythagorean\s+theorem|cellular\s+respiration|plate\s+tectonics|dna|rna)\b",
    r"^what\s+is\s+the\s+capital\s+of\s+[a-zA-Z\s]+$",
    r"^who\s+(wrote|painted|discovered|invented)\s+(hamlet|romeo\s+and\s+juliet|mona\s+lisa|gravity|penicillin|electricity|the\s+telephone|the\s+lightbulb)\b"
]

# 2. Queries that MUST trigger web search (Current, recent, live, or externally verifiable information)
INTENT_SEARCH_PATTERNS = [
    # Explicit search instructions
    r"\b(search\s+(the\s+)?web|search\s+online|find\s+online|google|browse\s+(the\s+)?web|look\s+up\s+online)\b",

    # Temporal anchors (Today, current, recent, latest, upcoming)
    r"\b(current|currently|presently|today|yesterday|tonight|this\s+week|this\s+month|this\s+year|right\s+now|at\s+present|at\s+the\s+moment|recent(ly)?|latest|newest|upcoming)\b",

    # Date and time queries
    r"\b(today('?s)?\s+date|date\s+please|what\s+is\s+(the\s+)?(date|time|day)|current\s+(date|time)|time\s+now|date\s+today|what\s+day\s+is\s+(it|today)|what\s+is\s+today)\b",

    # Current officeholders, political leaders, corporate heads, sports captains
    r"\b(current\s+)?(president|prime\s+minister|pm|ceo|governor|chief\s+minister|cm|chancellor|pope|king|queen|monarch|head\s+of\s+state|vice\s+president|defense\s+minister|cabinet\s+minister|foreign\s+minister)\b",
    r"\bwho\s+(is|are|was|currently\s+is|leads?)\b",

    # Recent / future years referencing live events or versions (2024 through 2030)
    r"\b(202[4-9]|203[0-9])\b",

    # Breaking news, headlines, current events
    r"\b(breaking\s+news|top\s+headlines|latest\s+news|what\s+happened\s+(to|in|with)|current\s+status\s+of)\b",

    # Weather, local climate, air quality
    r"\b(weather|temperature|forecast|rain\s+prediction|air\s+quality|aqi)\b",

    # Financial markets, stocks, crypto, valuations
    r"\b(stock\s+price|market\s+cap|crypto\s+price|share\s+price|exchange\s+rate|bitcoin|ethereum|nasdaq|dow\s+jones|nifty|sensex|valuation\s+of)\b",

    # Sports matches, scores, champions, tournaments
    r"\b(match\s+score|who\s+won|score\s+of|game\s+score|championship\s+winner|world\s+cup|fifa|ipl|nba|nfl|super\s+bowl|premier\s+league|tournament|standings?)\b",

    # Software versions, model releases, product launch dates
    r"\b(latest\s+(version|release|update)|release\s+date\s+of|has\s+.+\s+been\s+released|new\s+features\s+in|changelog)\b"
]

def analyze_search_intent(prompt: str) -> Dict[str, Any]:
    """
    Intelligently analyzes the user's prompt to determine whether web search is necessary.
    Decides whether to trigger live search or rely purely on local offline neural knowledge.
    """
    if not prompt or not prompt.strip():
        return {
            "needs_search": False,
            "reason": "Empty prompt",
            "category": "empty"
        }

    p = prompt.strip()
    p_lower = p.lower()

    # Rule 1: Explicit search commands ALWAYS trigger web search (e.g. "search online for python syntax")
    if re.search(r"\b(search\s+(the\s+)?web|search\s+online|find\s+online|look\s+up\s+online|browse\s+(the\s+)?web)\b", p_lower):
        return {
            "needs_search": True,
            "reason": "Explicit search requested by user",
            "category": "explicit_search"
        }

    # Rule 2: Check exclusions (greetings, simple questions, coding, pure math, timeless knowledge)
    for pattern in EXCLUSION_PATTERNS:
        if re.search(pattern, p_lower):
            return {
                "needs_search": False,
                "reason": "Answerable via internal neural model knowledge (greeting/coding/math/timeless concept)",
                "category": "direct_knowledge"
            }

    # Rule 3: Check positive temporal and live-data intent triggers
    for pattern in INTENT_SEARCH_PATTERNS:
        if re.search(pattern, p_lower):
            return {
                "needs_search": True,
                "reason": "Requires recent, updated, or externally verifiable live information",
                "category": "temporal_or_live_data"
            }

    # Default: If not requiring current/recent information, use direct local AI knowledge
    return {
        "needs_search": False,
        "reason": "Standard foundational query answerable from internal model weights",
        "category": "direct_knowledge"
    }

def should_trigger_web_search(prompt: str) -> bool:
    """Intelligent evaluator for AI Mode automatic web search."""
    intent = analyze_search_intent(prompt)
    return intent["needs_search"]

def format_collapsible_sources_markdown(sources: List[Dict[str, str]]) -> str:
    """
    Formats web sources into an expandable/collapsible HTML+Markdown block
    that renders cleanly across all web browsers and markdown viewers.
    """
    if not sources:
        return ""

    count = len(sources)
    lines = [
        "",
        '<details class="noora-sources-accordion" open>',
        f'<summary class="noora-sources-summary">🌐 <strong>Web Sources & Citations</strong> ({count} retrieved)</summary>',
        '<div class="noora-sources-body">',
        ""
    ]

    for idx, s in enumerate(sources, 1):
        title = s.get("title", "Web Source").replace("[", "(").replace("]", ")")
        url = s.get("url", "#")
        source = s.get("source") or "Web"
        snippet = s.get("snippet", "")
        lines.append(f"{idx}. [{title}]({url}) — *{source}*")
        if snippet:
            lines.append(f"   > {snippet[:180]}...")

    lines.extend([
        "",
        "</div>",
        "</details>",
        ""
    ])
    return "\n".join(lines)

def is_datetime_query(prompt: str) -> bool:
    """Checks if the user is asking for the current date, time, or day."""
    if not prompt:
        return False
    p = prompt.lower().strip()
    return bool(re.search(
        r"\b(today('?s)?\s+date|date\s+please|what\s+is\s+(the\s+)?(date|time|day)|current\s+(date|time)|time\s+now|date\s+today|what\s+day\s+is\s+(it|today)|what\s+is\s+today|time\s+please)\b",
        p
    ))

def get_datetime_search_data() -> Dict[str, Any]:
    """Provides instant, 100% authoritative date and time data without external web scraping lag."""
    import datetime
    now_dt = datetime.datetime.now()
    formatted_date = now_dt.strftime("%A, %B %d, %Y")
    formatted_time = now_dt.strftime("%I:%M %p")
    return {
        "online": True,
        "query": "current date and time",
        "results": [
            {
                "title": f"Current Date: {formatted_date}",
                "url": "https://time.is",
                "source": "Local System Clock",
                "snippet": f"Today is {formatted_date}. Current local time is {formatted_time}."
            }
        ],
        "count": 1,
        "is_datetime": True,
        "formatted_date": formatted_date,
        "formatted_time": formatted_time
    }

def format_search_context(search_data: Dict[str, Any]) -> str:
    """Formats retrieved web results into a clean system instruction context."""
    if search_data.get("is_datetime"):
        d = search_data["formatted_date"]
        t = search_data["formatted_time"]
        return (
            f"[AUTHORITATIVE REAL-TIME CLOCK & CALENDAR DATA]\n"
            f"Today's Exact Date: {d}\n"
            f"Current Local Time: {t}\n"
            f"Day of Week: {d.split(',')[0]}\n\n"
            f"Instructions: Answer directly using the exact date and time above. "
            f"State clearly: 'Today is {d}, and the current time is {t}.' "
            f"NEVER output template placeholders like '[current date and time]'."
        )

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

    lines.append(
        "Instructions: Synthesize the above live search information to answer the question directly. "
        "Cite your sources clearly when referring to facts. "
        "CRITICAL: Never output template placeholders like '[current name of the current president]' or '[current date and time]'. "
        "Always output real, factual names and details directly from the search context."
    )
    return "\n".join(lines)
