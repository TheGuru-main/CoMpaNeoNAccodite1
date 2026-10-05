"""
Accodite Seed Crawler — Domain Dispatcher
=========================================
Bootstraps the memory grid with 100 documents across 9 domains.

Per domain, calls the matching adapter from external.py, normalizes the
result, and writes to the grid through the shared WebCrawler/grid path.
The crawler_scheduler still governs refetch timing for URLs; this module
only handles the *first* fill.

Domain plan (100 docs):
    code        25
    language    15
    knowledge   15
    news         8
    finance      8
    literature   8
    media        8   (ScrapingBee)
    religion     7
    dialect      6
"""
from __future__ import annotations
import os
from typing import Any, Dict, List, Optional

try:
    from training.caps import MAX_EXTERNAL_LINKS_PER_RUN
except ImportError:
    MAX_EXTERNAL_LINKS_PER_RUN = 100


# ============================================================================
# DOMAIN PLAN + QUERIES
# ============================================================================

DOMAIN_PLAN = [
    ("code",       25),
    ("language",   15),
    ("knowledge",  15),
    ("news",        8),
    ("finance",     8),
    ("literature",  8),
    ("media",       8),
    ("religion",    7),
    ("dialect",     6),
]


DOMAIN_QUERIES: Dict[str, List[str]] = {
    "code": [
        "python", "typescript", "javascript", "rust", "go",
        "sql", "docker", "kubernetes", "fastapi", "pytorch",
        "react", "node", "algorithms", "data structures", "regex",
        "async", "concurrency", "testing", "git", "rest api",
        "graphql", "postgres", "redis", "websocket", "auth",
    ],
    "language": [
        "algorithm", "recursion", "concurrency", "abstraction",
        "encapsulation", "polymorphism", "inheritance", "closure",
        "immutability", "asynchronous", "middleware", "idempotent",
        "serialization", "deserialization", "throughput",
    ],
    "knowledge": [
        "Artificial intelligence", "Machine learning",
        "Programming language", "Database", "Operating system",
        "Computer network", "Software engineering", "Compiler",
        "Cryptography", "Distributed computing", "Cloud computing",
        "Neural network", "Version control", "Application programming interface",
        "Web development",
    ],
    "news": [
        "technology", "artificial intelligence", "software",
        "cybersecurity", "open source", "startup", "developer tools",
        "cloud computing",
    ],
    "finance": [
        "AAPL", "MSFT", "GOOGL", "TSLA", "AMZN",
        "NVDA", "META", "JPM",
    ],
    "literature": [
        "programming", "machine learning", "software engineering",
        "algorithms", "data science", "computer science",
        "systems design", "coding interview",
    ],
    "media": [
        "https://en.wikipedia.org/wiki/Python_(programming_language)",
        "https://en.wikipedia.org/wiki/JavaScript",
        "https://en.wikipedia.org/wiki/Artificial_intelligence",
        "https://en.wikipedia.org/wiki/Distributed_computing",
        "https://en.wikipedia.org/wiki/Functional_programming",
        "https://en.wikipedia.org/wiki/Compiler",
        "https://en.wikipedia.org/wiki/Operating_system",
        "https://en.wikipedia.org/wiki/Machine_learning",
    ],
    "religion": [
        "Islamic ethics", "Quran", "Hadith", "Fiqh",
        "Islamic Golden Age", "Sharia", "Tafsir",
    ],
    "dialect": [
        "Nigerian Pidgin", "Hausa language", "Yoruba language",
        "Igbo language", "Naija slang", "West African English",
    ],
}


# ============================================================================
# ADAPTER CALL (defensive)
# ============================================================================

def _call_adapter(name: str, **kwargs) -> Any:
    """
    Import and call the named function from external.py.
    Tolerates module paths ('external' or 'external.external') and
    multiple call signatures.
    """
    fn = None
    for path in ("external", "external.external"):
        try:
            mod = __import__(path, fromlist=[name])
            fn = getattr(mod, name, None)
            if fn is not None:
                break
        except ImportError:
            continue
    if fn is None:
        return None

    # try kwarg-shape calls first, fall back to single positional
    attempts = [
        lambda: fn(**kwargs),
        lambda: fn(kwargs.get("query") or kwargs.get("word") or kwargs.get("url") or ""),
        lambda: fn(),
    ]
    for attempt in attempts:
        try:
            return attempt()
        except TypeError:
            continue
        except Exception as e:
            return {"__error__": f"{type(e).__name__}: {e}"}
    return None


def _normalize(result: Any) -> List[str]:
    """Flatten any adapter result into a list of text chunks."""
    out: List[str] = []
    if result is None:
        return out
    if isinstance(result, str):
        if result.strip():
            out.append(result)
        return out
    if isinstance(result, dict):
        if "__error__" in result:
            return out
        for key in ("text", "extract", "content", "summary", "body", "html"):
            v = result.get(key)
            if isinstance(v, str) and v.strip():
                out.append(v)
        # nested lists (e.g. news items)
        for key in ("articles", "results", "items", "hits", "entries", "definitions"):
            v = result.get(key)
            if isinstance(v, list):
                for item in v:
                    out.extend(_normalize(item))
        return out
    if isinstance(result, list):
        for item in result:
            out.extend(_normalize(item))
        return out
    return out


# ============================================================================
# PER-DOMAIN FETCHERS
# ============================================================================

def _fetch_code(query: str) -> List[str]:
    r = _call_adapter("fetch_github", query=query)
    return _normalize(r)


def _fetch_language(query: str) -> List[str]:
    out = []
    r1 = _call_adapter("fetch_dictionary", word=query, query=query)
    out.extend(_normalize(r1))
    r2 = _call_adapter("fetch_datamuse", query=query, op="ml")
    out.extend(_normalize(r2))
    return out


def _fetch_knowledge(query: str) -> List[str]:
    r = _call_adapter("fetch_wikipedia", query=query, topic=query)
    return _normalize(r)


def _fetch_news(query: str) -> List[str]:
    r = _call_adapter("fetch_news", query=query, topic=query)
    return _normalize(r)


def _fetch_finance(query: str) -> List[str]:
    out = []
    r1 = _call_adapter("fetch_alpha_vantage", query=query, symbol=query)
    out.extend(_normalize(r1))
    r2 = _call_adapter("fetch_fmp", query=query, symbol=query)
    out.extend(_normalize(r2))
    return out


def _fetch_literature(query: str) -> List[str]:
    out = []
    r1 = _call_adapter("fetch_books", query=query, topic=query)
    out.extend(_normalize(r1))
    r2 = _call_adapter("fetch_elibrary", query=query, topic=query)
    out.extend(_normalize(r2))
    return out


def _fetch_media(url: str) -> List[str]:
    """Media domain now goes through ScrapingBee."""
    try:
        from external.scrapingbee import fetch_page
    except ImportError:
        try:
            from scrapingbee import fetch_page  # type: ignore
        except ImportError:
            return []
    r = fetch_page(url, render_js=True)
    if not r.get("ok"):
        return []
    html = r.get("html") or ""
    # strip tags crudely; the memory_grid will tokenize what's left
    import re
    text = re.sub(r"<script[\s\S]*?</script>", " ", html, flags=re.I)
    text = re.sub(r"<style[\s\S]*?</style>", " ", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return [text] if text else []


def _fetch_religion(query: str) -> List[str]:
    out = []
    r1 = _call_adapter("fetch_wikipedia", query=query, topic=query)
    out.extend(_normalize(r1))
    r2 = _call_adapter("fetch_books", query=query, topic=query)
    out.extend(_normalize(r2))
    return out


def _fetch_dialect(query: str) -> List[str]:
    out = []
    r1 = _call_adapter("fetch_wikipedia", query=query, topic=query)
    out.extend(_normalize(r1))
    r2 = _call_adapter("fetch_dictionary", word=query, query=query)
    out.extend(_normalize(r2))
    return out


DISPATCH = {
    "code":       _fetch_code,
    "language":   _fetch_language,
    "knowledge":  _fetch_knowledge,
    "news":       _fetch_news,
    "finance":    _fetch_finance,
    "literature": _fetch_literature,
    "media":      _fetch_media,
    "religion":   _fetch_religion,
    "dialect":    _fetch_dialect,
}


# ============================================================================
# MAIN ENTRY
# ============================================================================

def seed_crawl(
    *,
    grid=None,
    per_domain_override: Optional[Dict[str, int]] = None,
    domain_filter: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Fill the grid with the planned 100 docs across 9 domains.
    `per_domain_override` can shrink targets for testing.
    `domain_filter` limits which domains run.
    """
    stats: Dict[str, Any] = {
        "planned": 0, "written": 0, "failed": 0,
        "by_domain": {}, "errors": [],
    }

    # resolve grid
    if grid is None:
        try:
            from integration import get_state
            grid = get_state().get("grid")
        except Exception:
            grid = None
    if grid is None:
        try:
            from memory_grid import MemoryGrid  # type: ignore
            grid = MemoryGrid()
        except Exception:
            stats["errors"].append("no grid available")
            return stats

    plan = DOMAIN_PLAN
    if domain_filter:
        plan = [(d, n) for (d, n) in plan if d in domain_filter]
    if per_domain_override:
        plan = [(d, per_domain_override.get(d, n)) for (d, n) in plan]

    for domain, target in plan:
        queries = DOMAIN_QUERIES.get(domain, [])
        if not queries:
            continue
        fetcher = DISPATCH.get(domain)
        if fetcher is None:
            continue

        written = 0
        failed = 0
        for i in range(target):
            q = queries[i % len(queries)]
            stats["planned"] += 1
            try:
                chunks = fetcher(q) or []
                if not chunks:
                    failed += 1
                    continue
                for chunk in chunks:
                    if not isinstance(chunk, str) or not chunk.strip():
                        continue
                    try:
                        grid.add_document(
                            chunk[:8192],
                            source=f"seed:{domain}",
                        )
                        written += 1
                    except Exception as e:
                        failed += 1
                        stats["errors"].append(f"{domain}: add_document {e}")
            except Exception as e:
                failed += 1
                stats["errors"].append(f"{domain}: {type(e).__name__}: {e}")

        stats["by_domain"][domain] = {"written": written, "failed": failed}
        stats["written"] += written
        stats["failed"] += failed
        print(f"[seed] {domain:11s} written={written:3d} failed={failed:3d}")

    print(
        f"[seed] TOTAL written={stats['written']} failed={stats['failed']} "
        f"planned={stats['planned']}"
    )
    return stats


# Backwards-compatible alias for the older autostart call
def seed_crawl_legacy(*args, **kwargs):
    return seed_crawl(*args, **kwargs)
