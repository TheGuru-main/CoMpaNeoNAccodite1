"""
Accodite Seed Crawler — Domain Dispatcher
=========================================
Bootstraps the memory grid with about 9000 documents across 90 domains.

Per domain, calls the matching adapter from external.py, normalizes the
result, and writes to the grid through the shared WebCrawler/grid path.
The crawler_scheduler still governs refetch timing for URLs; this module
only handles the *first* fill.

Domain plan (9000+ docs / 90 domains (min 100 per domain)):
"""
from __future__ import annotations
import os
from typing import Any, Dict, List, Optional

try:
    from training.caps import MAX_EXTERNAL_LINKS_PER_RUN
except ImportError:
    MAX_EXTERNAL_LINKS_PER_RUN = 2500


# ============================================================================
# DOMAIN PLAN + QUERIES
# ============================================================================
DOMAIN_PLAN = [
    # ====================== CORE CODE (Heavy) ======================
    ("code", 100),
    ("gsp", 100),
    ("sandbox", 100),
    ("rules", 100),
    ("workflows", 100),
    ("console", 100),
    ("licensing", 100),
    ("systems", 100),
    ("ai_ml", 100),
    ("data", 100),
    ("security", 100),
    ("cloud", 100),
    ("devops", 100),
    ("testing", 100),
    ("api_design", 100),
    ("databases", 100),
    ("frontend", 100),
    ("backend", 100),
    ("mobile", 100),
    ("protocols", 100),
    # ====================== LANGUAGE ======================
    ("language", 100),
    ("dialect", 100),
    ("nlp", 100),
    ("yoruba", 100),
    ("french", 100),
    ("translation", 100),
    ("linguistics", 100),
    ("speech", 100),
    # ====================== KNOWLEDGE / SCIENCE ======================
    ("knowledge", 100),
    ("science", 100),
    ("mathematics", 100),
    ("engineering", 100),
    ("physics", 100),
    ("biology", 100),
    ("chemistry", 100),
    ("research", 100),
    # ====================== BUSINESS ======================
    ("finance", 100),
    ("business", 100),
    ("startup", 100),
    ("news", 100),
    ("markets", 100),
    ("product", 100),
    ("growth", 100),
    ("ops", 100),
    # ====================== CULTURE / SOCIETY ======================
    ("literature", 100),
    ("religion", 100),
    ("education", 100),
    ("philosophy", 100),
    ("history", 100),
    ("ethics", 100),
    ("policy", 100),
    ("civic", 100),
    # ====================== MEDIA / INFRA / PRODUCT ======================
    ("media", 100),
    ("design", 100),
    ("health", 100),
    ("law", 100),
    ("agriculture", 100),
    ("energy", 100),
    ("climate", 100),
    ("transport", 100),
    ("logistics", 100),
    ("maps", 100),
    ("geo", 100),
    ("iot", 100),
    ("hardware", 100),
    ("robotics", 100),
    ("gaming", 100),
    ("ux", 100),
    ("accessibility", 100),
    ("privacy", 100),
    ("compliance", 100),
    ("observability", 100),
    ("messaging", 100),
    ("search", 100),
    ("indexing", 100),
    ("cdn", 100),
    ("streaming", 100),
    ("realtime", 100),
    ("auth", 100),
    ("identity", 100),
    ("payments", 100),
    ("ecommerce", 100),
    ("community", 100),
    ("collaboration", 100),
    ("docs", 100),
    ("opensource", 100),
    ("multilingual", 100),
    ("nigeria", 100),
    ("africa_tech", 100),
    ("yc_startup", 100),
]






DOMAIN_QUERIES: Dict[str, List[str]] = {
    # ====================== CORE CODE ======================
    "code": [
        "python best practices", "typescript patterns", "javascript clean code",
        "rust ownership", "go concurrency", "sql optimization", "docker best practices",
        "kubernetes patterns", "fastapi tutorial", "pytorch training loop",
        "react hooks", "nodejs architecture", "algorithms explained", "data structures",
        "regex advanced", "async await patterns", "concurrency models", "unit testing",
        "git workflows", "rest api design", "graphql schema", "postgres indexing",
        "redis caching", "websocket patterns", "authentication jwt", "solid principles",
        "design patterns", "clean architecture",
    ],
    "gsp": [
        "Guru Scatter Protocol", "GSP placement formula", "GSP keyboard grid",
        "L S c placement", "start_row formula", "fragment coordinates GSP",
        "elastic cloud GSP", "typo tolerant neighbourhood", "GSP point-node",
        "keyboard mapping GSP", "QWERTY GSP columns", "GSP row step D",
        "Guru Separation Protocol", "cell id L+S+c", "GSP anomaly detection",
        "GSP sharding", "GSP replication factor K", "GSP grid 26 columns 64 rows",
    ],
    "sandbox": [
        "python sandbox execution", "restricted python environment", "code execution sandbox",
        "EOF append file", "append to file terminal", "cat << EOF", "tee command",
        "self modifying code", "safe code execution", "docker sandbox",
        "firejail sandbox", "nsjail", "process isolation", "resource limits cgroups",
        "temporary file handling", "secure subprocess",
    ],
    "rules": [
        "coding standards", "style guide python", "pep8", "clean code rules",
        "code review checklist", "naming conventions", "error handling best practices",
        "logging best practices", "security coding rules", "input validation rules",
        "immutability rules", "function length rules", "commenting standards",
        "dependency rules",
    ],
    "workflows": [
        "git flow", "github flow", "trunk based development", "ci cd pipeline",
        "continuous integration", "continuous deployment", "code review workflow",
        "feature branch workflow", "release workflow", "hotfix workflow",
        "pull request process", "semantic versioning", "changelog management",
        "deployment strategies",
    ],
    "console": [
        "bash scripting", "linux commands", "shell scripting", "command line tools",
        "awk sed grep", "find command", "xargs", "tmux usage", "screen command",
        "ssh tips", "terminal multiplexers", "cli productivity",
    ],
    "licensing": [
        "MIT license explained", "Apache 2.0 license", "GPL vs MIT", "BSD license",
        "open source license compatibility", "license compliance", "copyright software",
        "copyleft explained", "permissive licenses", "software license obligations",
    ],
    "systems": [
        "operating system concepts", "linux kernel", "process management",
        "memory management", "file systems", "networking basics", "tcp ip",
        "distributed systems", "consensus algorithms", "load balancing",
        "caching strategies", "message queues",
    ],
    "ai_ml": [
        "transformer architecture", "attention mechanism", "training loop pytorch",
        "fine tuning llm", "lora fine tuning", "tokenization", "embedding models",
        "gradient descent", "backpropagation", "model evaluation", "overfitting",
        "data loader pytorch", "mixed precision training", "distributed training",
    ],
    "data": [
        "data modeling", "etl pipeline", "data warehouse", "olap vs oltp",
        "data quality", "feature engineering", "data versioning", "parquet format",
        "sql vs nosql", "data pipelines", "streaming data", "batch processing",
    ],
    "security": [
        "owasp top 10", "authentication best practices", "authorization models",
        "encryption at rest", "encryption in transit", "jwt security", "cors",
        "sql injection prevention", "xss prevention", "csrf protection",
        "secrets management", "zero trust",
    ],
    "cloud": [
        "aws fundamentals", "kubernetes architecture", "docker networking",
        "serverless patterns", "infrastructure as code", "terraform basics",
        "ci cd cloud", "observability", "monitoring cloud", "auto scaling",
        "cloud security shared responsibility",
    ],

    # ====================== LANGUAGE & LINGUISTICS ======================
    "language": [
        "programming paradigms", "type systems", "functional programming",
        "object oriented programming", "concurrency theory", "memory models",
        "compilers", "interpreters", "static vs dynamic typing", "metaprogramming",
    ],
    "dialect": [
        "Nigerian Pidgin", "Hausa language", "Yoruba language", "Igbo language",
        "Naija slang", "West African English", "code switching Africa",
        "African English varieties", "local language computing",
    ],
    "nlp": [
        "tokenization methods", "word embeddings", "named entity recognition",
        "sentiment analysis", "language models", "text classification",
        "sequence to sequence", "attention in nlp",
    ],

    # ====================== KNOWLEDGE & SCIENCE ======================
    "knowledge": [
        "Artificial intelligence", "Machine learning", "Computer science",
        "Software engineering", "Database systems", "Operating systems",
        "Computer networks", "Distributed computing", "Cloud computing",
        "Information retrieval",
    ],
    "science": [
        "physics fundamentals", "biology basics", "chemistry concepts",
        "scientific method", "research methodology", "experimental design",
        "data analysis science", "peer review",
    ],
    "mathematics": [
        "linear algebra", "calculus", "probability", "statistics",
        "discrete mathematics", "graph theory", "optimization", "number theory",
    ],
    "engineering": [
        "software engineering principles", "system design", "architecture patterns",
        "reliability engineering", "performance engineering", "scalability",
        "technical debt", "engineering management",
    ],

    # ====================== BUSINESS & WORLD ======================
    "finance": [
        "AAPL stock", "MSFT stock", "financial statements", "valuation methods",
        "startup finance", "venture capital", "unit economics", "burn rate",
    ],
    "business": [
        "business models", "go to market", "product market fit", "customer development",
        "pricing strategies", "business strategy", "operations management",
    ],
    "startup": [
        "yc application", "startup advice", "founder experience", "seed funding",
        "product led growth", "startup metrics", "pitch deck",
    ],
    "news": [
        "technology news", "artificial intelligence news", "startup news",
        "open source news", "cybersecurity news", "developer tools news",
        "cloud computing news",
    ],

    # ====================== CULTURE & SOCIETY ======================
    "literature": [
        "technical writing", "documentation best practices", "software literature",
        "computer science books", "programming books", "systems design books",
    ],
    "religion": [
        "Islamic ethics", "Quran", "Hadith", "Fiqh", "Islamic Golden Age",
        "Sharia", "Tafsir",
    ],
    "education": [
        "learning systems", "curriculum design", "pedagogy", "online learning",
        "knowledge transfer", "deliberate practice", "skill acquisition",
    ],
    "philosophy": [
        "philosophy of technology", "ethics of ai", "epistemology", "logic",
        "philosophy of mind",
    ],
    "history": [
        "history of computing", "history of internet", "history of open source",
        "history of artificial intelligence", "history of programming languages",
    ],

    # ====================== MEDIA & OTHERS ======================
    "media": [
        "https://en.wikipedia.org/wiki/Python_(programming_language)",
        "https://en.wikipedia.org/wiki/Artificial_intelligence",
        "https://en.wikipedia.org/wiki/Machine_learning",
        "https://en.wikipedia.org/wiki/Distributed_computing",
        "https://en.wikipedia.org/wiki/Operating_system",
        "https://en.wikipedia.org/wiki/Compiler",
    ],
    "design": [
        "system design", "api design", "ux for developers", "interface design",
        "design systems",
    ],
    "health": [
        "digital health", "health informatics", "medical data", "healthcare systems",
        "public health technology",
    ],
    "law": [
        "software law", "intellectual property software", "privacy law", "gdpr",
        "cyber law",
    ],
    "agriculture": [
        "agritech", "precision agriculture", "agricultural data", "food systems",
        "sustainable agriculture technology",
    ],
    "devops": [
        "ci cd pipeline", "infrastructure as code", "gitops", "release engineering", "sre practices",
    ],
    "testing": [
        "unit testing", "integration testing", "test driven development", "pytest", "mocking strategies",
    ],
    "api_design": [
        "rest api design", "openapi", "graphql schema", "api versioning", "rate limiting",
    ],
    "databases": [
        "postgres indexing", "sql optimization", "nosql patterns", "database migrations", "replication",
    ],
    "frontend": [
        "react hooks", "css architecture", "web accessibility", "spa routing", "state management",
    ],
    "backend": [
        "fastapi tutorial", "nodejs architecture", "service design", "middleware patterns", "background jobs",
    ],
    "mobile": [
        "mobile app architecture", "react native", "android development", "ios patterns", "offline first",
    ],
    "protocols": [
        "http2", "grpc", "websocket patterns", "tcp ip", "quic protocol",
    ],
    "yoruba": [
        "Yoruba language", "Yoruba orthography", "Yoruba computing", "Yoruba NLP", "tone marking Yoruba",
    ],
    "french": [
        "French language", "French grammar", "French NLP", "AZERTY keyboard", "French technical writing",
    ],
    "translation": [
        "machine translation", "multilingual embeddings", "code switching", "localization engineering",
    ],
    "linguistics": [
        "phonology", "morphology", "syntax", "computational linguistics",
    ],
    "speech": [
        "speech recognition", "text to speech", "audio features", "voice interfaces",
    ],
    "physics": [
        "classical mechanics", "electromagnetism", "thermodynamics", "quantum basics",
    ],
    "biology": [
        "cell biology", "genetics basics", "bioinformatics", "molecular biology",
    ],
    "chemistry": [
        "organic chemistry basics", "chemical bonding", "stoichiometry", "materials chemistry",
    ],
    "research": [
        "research methodology", "literature review", "experimental design", "scientific writing",
    ],
    "markets": [
        "market structure", "liquidity", "order books", "market microstructure",
    ],
    "product": [
        "product management", "roadmaps", "user research", "prioritization frameworks",
    ],
    "growth": [
        "growth loops", "acquisition channels", "retention metrics", "activation",
    ],
    "ops": [
        "operations management", "process design", "incident response", "oncall",
    ],
    "ethics": [
        "ethics of ai", "responsible AI", "fairness in ML", "tech ethics",
    ],
    "policy": [
        "tech policy", "digital regulation", "data governance", "platform policy",
    ],
    "civic": [
        "civic technology", "open government data", "digital public services",
    ],
    "energy": [
        "renewable energy systems", "grid systems", "energy data", "power systems basics",
    ],
    "climate": [
        "climate data", "climate models", "sustainability technology",
    ],
    "transport": [
        "transport systems", "mobility data", "logistics routing",
    ],
    "logistics": [
        "supply chain", "inventory systems", "warehouse automation",
    ],
    "maps": [
        "OpenStreetMap", "geocoding", "map tiles", "spatial indexing",
    ],
    "geo": [
        "GIS basics", "spatial databases", "coordinate systems",
    ],
    "iot": [
        "iot protocols", "mqtt", "edge computing", "sensor networks",
    ],
    "hardware": [
        "computer architecture", "embedded systems", "hardware software co design",
    ],
    "robotics": [
        "robot control", "path planning", "ros basics", "sensors actuators",
    ],
    "gaming": [
        "game loops", "physics engines", "multiplayer networking",
    ],
    "ux": [
        "user experience design", "interaction design", "usability testing",
    ],
    "accessibility": [
        "wcag", "screen readers", "accessible web", "inclusive design",
    ],
    "privacy": [
        "privacy by design", "differential privacy", "data minimization",
    ],
    "compliance": [
        "gdpr compliance", "soc2", "security compliance",
    ],
    "observability": [
        "metrics logs traces", "opentelemetry", "alerting", "slo sli",
    ],
    "messaging": [
        "message queues", "pubsub", "kafka patterns", "event driven architecture",
    ],
    "search": [
        "information retrieval", "full text search", "ranking algorithms", "search indexing",
    ],
    "indexing": [
        "inverted index", "vector index", "bm25", "approximate nearest neighbor",
    ],
    "cdn": [
        "content delivery network", "edge caching", "cache invalidation",
    ],
    "streaming": [
        "live streaming protocols", "hls dash", "media pipelines",
    ],
    "realtime": [
        "realtime systems", "websockets", "crdt", "presence systems",
    ],
    "auth": [
        "oauth2", "oidc", "session management", "mfa",
    ],
    "identity": [
        "identity management", "sso", "directory services",
    ],
    "payments": [
        "payment rails", "checkout flows", "pci awareness",
    ],
    "ecommerce": [
        "catalog systems", "cart checkout", "inventory ecommerce",
    ],
    "community": [
        "community platforms", "moderation systems", "forums",
    ],
    "collaboration": [
        "collaborative editing", "shared workspaces", "permissions models",
    ],
    "docs": [
        "technical documentation", "docs as code", "api docs",
    ],
    "opensource": [
        "open source governance", "contributor guides", "license compliance",
    ],
    "multilingual": [
        "multilingual search", "unicode handling", "language detection",
    ],
    "nigeria": [
        "Nigeria technology", "Nigerian startup ecosystem", "local payments Nigeria", "NITDA",
    ],
    "africa_tech": [
        "African startups", "mobile money", "last mile connectivity", "africa developer ecosystem",
    ],
    "yc_startup": [
        "yc application", "startup advice", "seed funding", "product market fit", "pitch deck",
    ],

}

# ============================================================================
# ADAPTER CALL (defensive)
# ============================================================================

def _call_adapter(name: str, **kwargs) -> Any:
    """
    Import and call an adapter.

    Supports both synchronous and asynchronous adapters. Any coroutine
    returned by an adapter is resolved before the result reaches
    _normalize().
    """
    aliases = {
        "fetch_github": "fetch_github_ebooks",
        "fetch_alpha_vantage": "fetch_alphavantage",
        "fetch_fmp": "fetch_financial_modelling_prep",
    }

    actual_name = aliases.get(name, name)

    fn = None

    # Normal external package/module locations.
    for path in ("external", "external.external"):
        try:
            mod = __import__(path, fromlist=[actual_name])
            fn = getattr(mod, actual_name, None)
            if fn is not None:
                break
        except ImportError:
            continue

    # Datamuse lives in its own adapter module.
    if fn is None and actual_name == "fetch_datamuse":
        try:
            from external.datamuse import fetch_datamuse
            fn = fetch_datamuse
        except ImportError:
            try:
                from datamuse import fetch_datamuse
                fn = fetch_datamuse
            except ImportError:
                fn = None

    if fn is None:
        return None

    attempts = [
        lambda: fn(**kwargs),
        lambda: fn(
            kwargs.get("query")
            or kwargs.get("word")
            or kwargs.get("url")
            or ""
        ),
        lambda: fn(),
    ]

    for attempt in attempts:
        try:
            result = attempt()

            if _inspect.isawaitable(result):
                loop = _get_seed_loop()

                if loop.is_running():
                    nested_loop = _aio.new_event_loop()
                    try:
                        return nested_loop.run_until_complete(result)
                    finally:
                        nested_loop.close()

                return loop.run_until_complete(result)

            return result

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
        for key in ("text", "extract", "content", "summary", "body", "html", "title"):
            v = result.get(key)
            if isinstance(v, str) and v.strip():
                out.append(v)
        # nested lists — include external.py "documents"
        for key in ("documents", "articles", "results", "items", "hits", "entries", "definitions"):
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

def _fetch_video_knowledge(
    query: str,
    domain: str,
    limit: int = 2,
) -> List[str]:
    """
    Supplement a domain with APITube video metadata.

    Only include records with an explicitly declared license accepted
    by the existing four-tier seed licensing policy.
    Video descriptions are not treated as verified transcripts.
    """
    try:
        result = _call_adapter(
            "fetch_apitube_videos",
            query=query,
            limit=limit,
        )
    except Exception as exc:
        print(
            f"[video-enrichment] {domain}: "
            f"{type(exc).__name__}: {exc}"
        )
        return []

    if not isinstance(result, dict):
        return []

    documents = result.get("documents") or []
    if not isinstance(documents, list):
        return []

    output: List[str] = []

    for document in documents:
        if not isinstance(document, dict):
            continue

        metadata = document.get("metadata")
        if not isinstance(metadata, dict):
            metadata = {}

        provider = metadata.get("raw_provider")
        if not isinstance(provider, dict):
            provider = {}

        raw_license = (
            document.get("license")
            or document.get("license_name")
            or metadata.get("license")
            or metadata.get("license_name")
            or provider.get("license")
            or provider.get("license_name")
            or provider.get("license_type")
            or provider.get("licence")
            or provider.get("licence_name")
            or provider.get("licence_type")
            or ""
        )

        if isinstance(raw_license, dict):
            raw_license = (
                raw_license.get("name")
                or raw_license.get("title")
                or raw_license.get("type")
                or raw_license.get("spdx_id")
                or raw_license.get("identifier")
                or ""
            )

        # Only explicitly recognized license names are accepted.
        if not isinstance(raw_license, str):
            raw_license = ""

        if not normalize_license(raw_license):
            print(
                f"[video-enrichment] Skipped unverified license "
                f"for domain={domain!r}, "
                f"url={document.get('url', '')!r}"
            )
            continue

        title = str(document.get("title") or "").strip()
        description = str(
            document.get("description")
            or document.get("summary")
            or document.get("content")
            or ""
        ).strip()
        media_url = str(document.get("url") or "").strip()

        parts = [f"Domain: {domain}", f"Search topic: {query}"]

        if title:
            parts.append(f"Video title: {title}")
        if description:
            parts.append(f"Video description: {description[:4000]}")
        if media_url:
            parts.append(f"Source URL: {media_url}")
        parts.append(f"Declared license: {raw_license}")

        if title or description:
            output.append("[Licensed video metadata]\n" + "\n".join(parts))

    return output


def _fetch_code(query: str) -> List[str]:
    r = _call_adapter("fetch_github_ebooks", query=query)
    out = _normalize(r)
    out.extend(_fetch_video_knowledge(query, "code"))
    return out


def _fetch_language(query: str) -> List[str]:
    out = []
    r1 = _call_adapter("fetch_dictionary", word=query, query=query)
    out.extend(_normalize(r1))
    r2 = _call_adapter("fetch_datamuse", query=query, op="ml")
    out.extend(_normalize(r2))
    out.extend(_fetch_video_knowledge(query, "language"))
    return out


def _fetch_knowledge(query: str) -> List[str]:
    r = _call_adapter("fetch_wikipedia", query=query, topic=query)
    out = _normalize(r)
    out.extend(_fetch_video_knowledge(query, "knowledge"))
    return out


def _fetch_news(query: str) -> List[str]:
    r = _call_adapter("fetch_news", query=query, topic=query)
    out = _normalize(r)
    out.extend(_fetch_video_knowledge(query, "news"))
    return out


def _fetch_finance(query: str) -> List[str]:
    out = []
    r1 = _call_adapter("fetch_alphavantage", query=query, symbol=query)
    out.extend(_normalize(r1))
    r2 = _call_adapter("fetch_financial_modelling_prep", query=query, symbol=query)
    out.extend(_normalize(r2))
    out.extend(_fetch_video_knowledge(query, "finance"))
    return out


def _fetch_literature(query: str) -> List[str]:
    out = []
    r1 = _call_adapter("fetch_books", query=query, topic=query)
    out.extend(_normalize(r1))
    r2 = _call_adapter("fetch_elibrary", query=query, topic=query)
    out.extend(_normalize(r2))
    out.extend(_fetch_video_knowledge(query, "literature"))
    return out


def _fetch_media(url: str) -> List[str]:
    """Combine APITube media discovery with ScrapingBee page retrieval."""
    import re
    from urllib.parse import urlparse, unquote

    output: List[str] = []
    seen_urls = set()

    # Derive a search query from the current seed URL.
    parsed = urlparse(url)
    query = unquote(parsed.path.rstrip("/").rsplit("/", 1)[-1])
    query = query.replace("_", " ").replace("-", " ").strip()

    if not query:
        query = parsed.netloc or url

    # 1. APITube discovers related media and supplies metadata.
    apitube_result = _call_adapter(
        "fetch_apitube_videos",
        query=query,
        limit=3,
    )

    discovered_urls = []

    if isinstance(apitube_result, dict):
        documents = apitube_result.get("documents", [])

        if isinstance(documents, list):
            for document in documents:
                if not isinstance(document, dict):
                    continue

                title = str(document.get("title") or "").strip()
                content = str(
                    document.get("content")
                    or document.get("description")
                    or document.get("summary")
                    or ""
                ).strip()
                media_url = str(document.get("url") or "").strip()

                # Keep APITube metadata even if page retrieval fails.
                parts = []
                if title:
                    parts.append(f"Title: {title}")
                if media_url:
                    parts.append(f"Media URL: {media_url}")
                if content:
                    parts.append(content)

                if parts:
                    output.append(
                        "[Media discovery: APITube] " + "\\n".join(parts)
                    )

                if (
                    media_url.startswith(("https://", "http://"))
                    and media_url not in discovered_urls
                ):
                    discovered_urls.append(media_url)

    # 2. ScrapingBee retrieves the original seed page and discovered pages.
    # A failure on one URL must not discard results from other URLs.
    page_urls = [url] + discovered_urls

    try:
        from external.scrapingbee import fetch_page
    except ImportError:
        try:
            from scrapingbee import fetch_page
        except ImportError:
            fetch_page = None

    if fetch_page is not None:
        for page_url in page_urls:
            if page_url in seen_urls:
                continue
            seen_urls.add(page_url)

            try:
                result = fetch_page(page_url, render_js=True)
                if not isinstance(result, dict) or not result.get("ok"):
                    continue

                html = result.get("html") or ""
                text = re.sub(
                    r"<(script|style|noscript)[^>]*>[\\s\\S]*?</\\1>",
                    " ",
                    html,
                    flags=re.I,
                )
                text = re.sub(r"<[^>]+>", " ", text)
                text = re.sub(r"\\s+", " ", text).strip()

                if text:
                    output.append(
                        f"[Media page: {page_url}] {text[:12000]}"
                    )

            except Exception as exc:
                print(
                    f"[media-fetch] {page_url}: "
                    f"{type(exc).__name__}: {exc}"
                )

    return output

def _fetch_religion(query: str) -> List[str]:
    out = []
    r1 = _call_adapter("fetch_wikipedia", query=query, topic=query)
    out.extend(_normalize(r1))
    r2 = _call_adapter("fetch_books", query=query, topic=query)
    out.extend(_normalize(r2))
    out.extend(_fetch_video_knowledge(query, "religion"))
    return out


def _fetch_dialect(query: str) -> List[str]:
    out = []
    r1 = _call_adapter("fetch_wikipedia", query=query, topic=query)
    out.extend(_normalize(r1))
    r2 = _call_adapter("fetch_dictionary", word=query, query=query)
    out.extend(_normalize(r2))
    out.extend(_fetch_video_knowledge(query, "dialect"))
    return out



# LOCAL_SEED_FALLBACK — offline / failed-API bootstrap for train
LOCAL_SEED_TEXTS = {
    "code": [
        "Python best practices: use virtual environments, type hints, and explicit exception handling.",
        "FastAPI patterns: dependency injection, pydantic models, and async route handlers.",
        "Git workflows: feature branches, pull requests, and conventional commits.",
        "REST API design: resource nouns, status codes, idempotent methods, and pagination.",
        "PyTorch training loop: dataset, dataloader, forward, loss, backward, optimizer step.",
    ],
    "gsp": [
        "GSP start_row = ((L + S - 1) mod R) + 1. Fragments: row_k = ((start_row - 1 + k*D) mod R) + 1, col_k = (c + k) mod C.",
        "GSP point-node is fragment k=0. Elastic cloud perturbs L, S, and first-letter column c for typo tolerance.",
        "MemoryGrid is the central store. crawl_query routes letter, word, and storage grids into ranked candidates.",
        "Cell identity can be derived from L+S+c parameters used in placement.",
    ],
    "knowledge": [
        "Artificial intelligence systems learn patterns from data and apply them to new inputs.",
        "Machine learning includes supervised, unsupervised, and reinforcement learning paradigms.",
        "Information retrieval ranks documents by relevance to a query using indexes and scoring.",
    ],
    "sandbox": [
        "EOF append: cat << 'EOF' >> file.py then paste content then EOF. Safe subprocess with timeouts.",
        "Code sandboxes isolate execution with resource limits and restricted imports.",
    ],
}

def _local_fallback(domain: str, query: str) -> list:
    texts = LOCAL_SEED_TEXTS.get(domain) or LOCAL_SEED_TEXTS.get("knowledge") or []
    if not texts:
        return [f"Seed topic ({domain}): {query}. Accodite MemoryGrid training document."]
    # rotate by query hash
    i = abs(hash(query)) % len(texts)
    return [texts[i], f"Query context ({domain}): {query}"]

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

# LICENSE-SEQUENTIAL
#
# Four allowed license tiers, tried in order:
#   1. MIT
#   2. Apache-2.0
#   3. BSD-3-Clause
#   4. CC0-1.0
#
# Each fetched URL is assigned to the first tier its metadata declares.
# URLs with no declared license are rejected.
# Per-link and per-run caps come from training.caps.

LICENSE_TIERS = ("MIT", "Apache-2.0", "BSD-3-Clause", "CC0-1.0")

_LICENSE_ALIASES = {
    "MIT": "MIT",
    "MIT License": "MIT",
    "Apache-2.0": "Apache-2.0",
    "Apache 2.0": "Apache-2.0",
    "Apache License 2.0": "Apache-2.0",
    "BSD-3-Clause": "BSD-3-Clause",
    "BSD 3-Clause": "BSD-3-Clause",
    "BSD 3-Clause License": "BSD-3-Clause",
    "CC0-1.0": "CC0-1.0",
    "CC0": "CC0-1.0",
    "CC0 1.0": "CC0-1.0",
    "Creative Commons Zero v1.0 Universal": "CC0-1.0",
}

def normalize_license(text: str) -> str | None:
    """Return a tier name or None if not in the allowed set."""
    if not text:
        return None
    text = text.strip()
    for alias, tier in _LICENSE_ALIASES.items():
        if alias.lower() in text.lower():
            return tier
    return None


def filter_by_license(items, declared_license_of):
    """
    items               — iterable of fetched results
    declared_license_of — callable(item) -> raw license string (from metadata)
    Returns a dict {tier: [items]} for tiers 1-4, in order.
    """
    buckets = {tier: [] for tier in LICENSE_TIERS}
    for it in items:
        tier = normalize_license(declared_license_of(it) or "")
        if tier:
            buckets[tier].append(it)
    return buckets


def collect_seed_sequential(fetch_batch, declared_license_of, *, per_tier_cap=20):
    """
    For each license tier in order, run fetch_batch and collect up to
    per_tier_cap items. Stops early once total reaches the run cap.
    """
    from training.caps import (
        MAX_EXTERNAL_LINKS_PER_RUN, MAX_EXTERNAL_BYTES_PER_LINK,
    )
    out = []
    seen_urls = set()
    for tier in LICENSE_TIERS:
        if len(out) >= MAX_EXTERNAL_LINKS_PER_RUN:
            break
        try:
            items = fetch_batch(tier) or []
        except Exception as e:
            print(f"[seed] tier {tier} fetch failed: {type(e).__name__}: {e}")
            continue
        taken = 0
        for it in items:
            if taken >= per_tier_cap:
                break
            if len(out) >= MAX_EXTERNAL_LINKS_PER_RUN:
                break
            url = (it.get("url") if isinstance(it, dict) else None) or ""
            if url and url in seen_urls:
                continue
            if url:
                seen_urls.add(url)
            out.append({"tier": tier, "item": it})
            taken += 1
    return out


# ASYNC-FETCH-FIX
import asyncio as _aio
import inspect as _inspect

# FETCH-ERRORS
import asyncio as _aio
import inspect as _inspect
import concurrent.futures as _cf

def _run_fetcher(fetcher, query):
    """
    Fetchers may be sync or async. Run either form and return the list.
    Works whether or not we're already inside a running event loop.
    """
    res = fetcher(query)
    if _inspect.isawaitable(res):
        def runner():
            loop = _aio.new_event_loop()
            try:
                _aio.set_event_loop(loop)
                return loop.run_until_complete(res)
            finally:
                try: loop.close()
                except Exception: pass
        with _cf.ThreadPoolExecutor(max_workers=1) as ex:
            return ex.submit(runner).result()
    return res


_SEED_LOOP = None


def _get_seed_loop():
    global _SEED_LOOP
    if _SEED_LOOP is None or _SEED_LOOP.is_closed():
        try:
            _SEED_LOOP = _aio.get_event_loop()
        except RuntimeError:
            _SEED_LOOP = _aio.new_event_loop()
            _aio.set_event_loop(_SEED_LOOP)
    if _SEED_LOOP.is_running():
        # already inside a running loop — use a fresh one for sync calls
        new = _aio.new_event_loop()
        return new
    return _SEED_LOOP



# ACCD-SEED-CHUNK
def _chunk_text_for_grid(text: str, max_chars: int = 512, min_chars: int = 40):
    """Split one adapter body into paragraph/sentence chunks for unique grid docs."""
    text = (text or "").strip()
    if not text:
        return []
    if len(text) <= max_chars:
        return [text] if len(text) >= min_chars else ([text] if text else [])
    import re
    parts = re.split(r"\n\s*\n|(?<=[.!?])\s+(?=[A-Z0-9])", text)
    out = []
    buf = ""
    for part in parts:
        part = (part or "").strip()
        if not part:
            continue
        if len(part) > max_chars:
            if buf:
                out.append(buf.strip())
                buf = ""
            for i in range(0, len(part), max_chars):
                piece = part[i:i + max_chars].strip()
                if len(piece) >= min_chars:
                    out.append(piece)
            continue
        if len(buf) + len(part) + 1 <= max_chars:
            buf = (buf + " " + part).strip()
        else:
            if len(buf) >= min_chars:
                out.append(buf)
            buf = part
    if buf and len(buf) >= min_chars:
        out.append(buf)
    return out or ([text[:max_chars]] if text else [])

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
            # domains without dedicated API still get local/wiki path
            fetcher = DISPATCH.get("knowledge") or (lambda q: _local_fallback(domain, q))


        written = 0
        failed = 0
        for i in range(target):
            q = queries[i % len(queries)]
            stats["planned"] += 1
            try:
                chunks = _run_fetcher(fetcher, q) or []
                if not chunks:
                    chunks = _local_fallback(domain, q)
                if not chunks:
                    failed += 1
                    continue
                for chunk in chunks:
                    if not isinstance(chunk, str) or not chunk.strip():
                        continue
                    # ACCD-SEED-CHUNK: paragraph/sentence units → unique hashes → more grid docs
                    units = _chunk_text_for_grid(chunk[:8192])
                    for ui, unit in enumerate(units):
                        try:
                            grid.add_document(
                                unit,
                                source=f"seed:{domain}",
                                metadata={"domain": domain, "chunk_i": ui},
                            )
                            written += 1
                        except Exception as e:
                            failed += 1
                            stats["errors"].append(f"{domain}: add_document {e}")
                            print(f"[seed-err] {domain}: {type(e).__name__}: {e}")
            except Exception as e:
                failed += 1
                stats["errors"].append(f"{domain}: {type(e).__name__}: {e}")
                print(f"[fetch-err] {domain}: {type(e).__name__}: {e}")  # FETCH-ERRORS

        stats["by_domain"][domain] = {"written": written, "failed": failed}
        stats["written"] += written
        stats["failed"] += failed
        print(f"[seed] {domain:11s} written={written:3d} failed={failed:3d}")

    print(
        f"[seed] TOTAL written={stats['written']} failed={stats['failed']} "
        f"planned={stats['planned']}"
    )
    try:
        nd = len(getattr(grid, "documents", {}) or {})
        dup = int(getattr(grid, "duplicates_detected", 0) or 0)
        tok = int(getattr(grid, "tokens_added", 0) or 0)
        print(f"[seed] grid_unique_docs={nd} duplicates_detected={dup} tokens_indexed={tok}")
    except Exception as e:
        print("[seed] grid stats error", e)
    return stats


# Backwards-compatible alias for the older autostart call
def seed_crawl_legacy(*args, **kwargs):
    return seed_crawl(*args, **kwargs)
