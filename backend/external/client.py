"""
CoMpaNeoN External Source Adapter Layer
========================================

External acquisition providers used by web_crawler.py.

Responsibilities
----------------
- Define external source directions/endpoints.
- Provide normalized adapters for external APIs.
- Support dictionaries, news, books, e-library, Wikipedia,
  GitHub, financial sources, APITube and YouTube.
- Return normalized external documents to web_crawler.py.
- Preserve source identity and provenance.
- Detect language where possible.
- Provide video metadata, subtitles and transcript information
  where legitimately available.

IMPORTANT
---------
external.py does NOT:

- crawl autonomously
- decide MemoryGrid placement
- perform GSP placement
- rank knowledge
- build WordChain relationships
- perform WordUnderstanding
- manage STM/LTM
- generate prompts
- generate AI responses

Architecture
------------

                external.py
                     │
             source adapters
                     │
                     ▼
               web_crawler.py
                     │
       ┌─────────────┼─────────────┐
       │             │             │
   validate       checksum      normalize
       │             │             │
       └─────────────┼─────────────┘
                     ▼
                MemoryGrid
                     │
                     ▼
                  Ranking
                     │
                     ▼
                 WordChain
                     │
                     ▼
              WordUnderstanding

The crawler is the owner of acquisition.
This module simply knows how to communicate with external sources.
"""

from __future__ import annotations

import hashlib
import os
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

import httpx

try:
    from langdetect import detect as detect_language
except ImportError:
    detect_language = None


# ============================================================================
# CONFIGURATION
# ============================================================================

DEFAULT_TIMEOUT = 20.0
DEFAULT_LIMIT = 5


# ============================================================================
# SOURCE REGISTRY
# ============================================================================

EXTERNAL_SOURCES: Dict[str, Dict[str, Any]] = {

    "dictionary": {
        "type": "dictionary",
        "provider": "dictionaryapi.dev",
        "base_url": (
            "https://api.dictionaryapi.dev/api/v2/entries/en"
        ),
        "requires_key": False,
        "capabilities": [
            "definitions",
            "meanings",
            "phonetics",
        ],
    },

    "news": {
        "type": "news",
        "provider": "gnews",
        "base_url": (
            "https://gnews.io/api/v4/search"
        ),
        "requires_key": True,
        "environment_key": "GNEWS_API_KEY",
        "capabilities": [
            "search",
            "articles",
            "publication_date",
        ],
    },

    "openlibrary": {
        "type": "book",
        "provider": "openlibrary",
        "base_url": (
            "https://openlibrary.org/search.json"
        ),
        "requires_key": False,
        "capabilities": [
            "books",
            "authors",
            "subjects",
            "publication_year",
        ],
    },

    "google_books": {
        "type": "ebook",
        "provider": "google_books",
        "base_url": (
            "https://www.googleapis.com/books/v1/volumes"
        ),
        "requires_key": False,
        "capabilities": [
            "books",
            "authors",
            "subjects",
            "metadata",
            "preview",
        ],
    },

    "wikipedia": {
        "type": "encyclopedia",
        "provider": "wikipedia",
        "base_url": (
            "https://en.wikipedia.org/w/api.php"
        ),
        "requires_key": False,
        "capabilities": [
            "search",
            "summary",
            "encyclopedia",
        ],
    },

    "github": {
        "type": "repository",
        "provider": "github",
        "base_url": (
            "https://api.github.com"
        ),
        "requires_key": False,
        "environment_key": "GITHUB_TOKEN",
        "capabilities": [
            "repositories",
            "code",
            "documentation",
            "ebooks",
        ],
    },

    "alphavantage": {
        "type": "financial",
        "provider": "alpha_vantage",
        "base_url": (
            "https://www.alphavantage.co/query"
        ),
        "requires_key": True,
        "environment_key": "ALPHA_VANTAGE_API_KEY",
        "capabilities": [
            "stocks",
            "market_data",
        ],
    },

    "financial_modeling_prep": {
        "type": "financial",
        "provider": "financial_modeling_prep",
        "base_url": (
            "https://financialmodelingprep.com/api/v3"
        ),
        "requires_key": True,
        "environment_key": "FMP_API_KEY",
        "capabilities": [
            "company_profile",
            "financial_data",
        ],
    },

    "apitube": {
        "type": "video",
        "provider": "apitube",
        "base_url": (
            "https://api.apitube.io"
        ),
        "requires_key": True,
        "environment_key": "APITUBE_API_KEY",
        "capabilities": [
            "video_search",
            "video_metadata",
            "media_discovery",
        ],
    },

    "youtube": {
        "type": "video",
        "provider": "youtube",
        "base_url": (
            "https://www.googleapis.com/youtube/v3"
        ),
        "requires_key": True,
        "environment_key": "YOUTUBE_API_KEY",
        "capabilities": [
            "video_search",
            "video_metadata",
            "channel_metadata",
            "captions",
        ],
    },
}


# ============================================================================
# NORMALIZATION
# ============================================================================

def normalize_source(
    source: str,
) -> str:
    """
    Normalize an external source name.
    """

    return str(
        source or ""
    ).strip().lower()


def get_source(
    source: str,
) -> Optional[Dict[str, Any]]:
    """
    Return source configuration.
    """

    return EXTERNAL_SOURCES.get(
        normalize_source(source)
    )


def list_sources() -> List[str]:
    """
    Return all registered external sources.
    """

    return list(
        EXTERNAL_SOURCES.keys()
    )


# ============================================================================
# LANGUAGE
# ============================================================================

def detect_content_language(
    text: str,
) -> Optional[str]:
    """
    Detect language using langdetect when available.

    This is deliberately advisory.

    tokenizer.py remains the canonical linguistic tokenizer.
    """

    if not text:
        return None

    if detect_language is None:
        return None

    try:
        return detect_language(
            str(text)
        )
    except Exception:
        return None


# ============================================================================
# CHECKSUM
# ============================================================================

def content_checksum(
    content: str,
) -> str:
    """
    Produce a deterministic SHA-256 checksum.

    The crawler can use this to identify duplicate content.
    """

    return hashlib.sha256(
        str(content).encode(
            "utf-8"
        )
    ).hexdigest()


# ============================================================================
# NORMALIZED DOCUMENT
# ============================================================================

def normalize_document(
    *,
    source: str,
    source_type: str,
    content: str = "",
    title: str = "",
    url: str = "",
    external_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Convert an external result into the common crawler document format.

    web_crawler.py consumes this structure.
    """

    metadata = dict(
        metadata or {}
    )

    language = (
        metadata.get("language")
        or detect_content_language(
            content
        )
    )

    return {
        "source": normalize_source(
            source
        ),

        "source_type": source_type,

        "external_id": external_id,

        "url": url,

        "title": title,

        "content": content,

        "language": language,

        "checksum": content_checksum(
            content
        ) if content else None,

        "metadata": metadata,
    }


# ============================================================================
# HTTP CLIENT
# ============================================================================

def _client() -> httpx.AsyncClient:
    """
    Construct a standard external HTTP client.

    The crawler controls when requests are made.
    """

    return httpx.AsyncClient(
        timeout=DEFAULT_TIMEOUT,
        follow_redirects=True,
        headers={
            "User-Agent": (
                "CoMpaNeoN-WebCrawler/1.0"
            )
        },
    )


# ============================================================================
# DICTIONARY
# ============================================================================

async def fetch_dictionary(
    word: str,
) -> Dict[str, Any]:

    source = get_source(
        "dictionary"
    )

    if not source:
        return {
            "documents": []
        }

    url = (
        f"{source['base_url']}/"
        f"{word}"
    )

    async with _client() as client:

        try:

            response = await client.get(
                url
            )

            if response.status_code != 200:
                return {
                    "documents": []
                }

            data = response.json()

            if not data:
                return {
                    "documents": []
                }

            entry = data[0]

            meanings = entry.get(
                "meanings",
                []
            )

            content = (
                f"{word}\n"
                f"{meanings}"
            )

            document = normalize_document(
                source="dictionary",
                source_type="dictionary",
                content=content,
                title=word,
                url=url,
                external_id=word,
                metadata={
                    "meanings": meanings,
                    "phonetics": entry.get(
                        "phonetics",
                        []
                    ),
                },
            )

            return {
                "documents": [
                    document
                ]
            }

        except Exception as exc:

            return {
                "documents": [],
                "error": str(exc),
            }


# ============================================================================
# NEWS
# ============================================================================

async def fetch_news(
    query: str,
    limit: int = DEFAULT_LIMIT,
) -> Dict[str, Any]:

    api_key = os.getenv(
        "GNEWS_API_KEY"
    )

    if not api_key:
        return {
            "documents": [],
            "note": (
                "GNEWS_API_KEY not set"
            ),
        }

    source = get_source(
        "news"
    )

    params = {
        "q": query,
        "token": api_key,
        "lang": "en",
        "max": limit,
    }

    async with _client() as client:

        try:

            response = await client.get(
                source["base_url"],
                params=params,
            )

            if response.status_code != 200:
                return {
                    "documents": []
                }

            articles = response.json().get(
                "articles",
                []
            )

            documents = []

            for article in articles:

                content = (
                    article.get(
                        "content"
                    )
                    or article.get(
                        "description"
                    )
                    or ""
                )

                documents.append(
                    normalize_document(
                        source="news",
                        source_type="article",
                        content=content,
                        title=article.get(
                            "title",
                            "",
                        ),
                        url=article.get(
                            "url",
                            "",
                        ),
                        external_id=article.get(
                            "url"
                        ),
                        metadata={
                            "published_at": article.get(
                                "publishedAt"
                            ),
                            "source_name": (
                                article.get(
                                    "source",
                                    {}
                                ).get(
                                    "name"
                                )
                            ),
                            "image": article.get(
                                "image"
                            ),
                        },
                    )
                )

            return {
                "documents": documents
            }

        except Exception as exc:

            return {
                "documents": [],
                "error": str(exc),
            }


# ============================================================================
# OPENLIBRARY
# ============================================================================

async def fetch_books(
    query: str,
    category: str = "",
    limit: int = DEFAULT_LIMIT,
) -> Dict[str, Any]:

    source = get_source(
        "openlibrary"
    )

    params = {
        "q": query,
        "limit": limit,
    }

    if category:
        params[
            "subject"
        ] = category

    async with _client() as client:

        try:

            response = await client.get(
                source["base_url"],
                params=params,
            )

            if response.status_code != 200:
                return {
                    "documents": []
                }

            docs = response.json().get(
                "docs",
                []
            )

            documents = []

            for book in docs:

                title = book.get(
                    "title",
                    ""
                )

                authors = book.get(
                    "author_name",
                    []
                )

                content = (
                    f"Title: {title}\n"
                    f"Authors: "
                    f"{', '.join(authors)}\n"
                    f"Subjects: "
                    f"{', '.join(book.get('subject', [])[:10])}"
                )

                documents.append(
                    normalize_document(
                        source="openlibrary",
                        source_type="book",
                        content=content,
                        title=title,
                        external_id=str(
                            book.get(
                                "key",
                                title,
                            )
                        ),
                        metadata={
                            "authors": authors,
                            "year": book.get(
                                "first_publish_year"
                            ),
                            "subjects": book.get(
                                "subject",
                                []
                            )[:20],
                        },
                    )
                )

            return {
                "documents": documents
            }

        except Exception as exc:

            return {
                "documents": [],
                "error": str(exc),
            }


# ============================================================================
# GOOGLE BOOKS / E-LIBRARY
# ============================================================================

async def fetch_elibrary(
    query: str,
    category: str = "",
    limit: int = DEFAULT_LIMIT,
) -> Dict[str, Any]:

    source = get_source(
        "google_books"
    )

    params = {
        "q": query,
        "maxResults": limit,
    }

    if category:
        params[
            "subject"
        ] = category

    async with _client() as client:

        try:

            response = await client.get(
                source["base_url"],
                params=params,
            )

            if response.status_code != 200:
                return {
                    "documents": []
                }

            items = response.json().get(
                "items",
                []
            )

            documents = []

            for item in items:

                info = item.get(
                    "volumeInfo",
                    {}
                )

                title = info.get(
                    "title",
                    ""
                )

                authors = info.get(
                    "authors",
                    []
                )

                description = info.get(
                    "description",
                    ""
                )

                content = (
                    f"Title: {title}\n"
                    f"Authors: "
                    f"{', '.join(authors)}\n"
                    f"{description}"
                )

                documents.append(
                    normalize_document(
                        source="google_books",
                        source_type="ebook",
                        content=content,
                        title=title,
                        url=info.get(
                            "infoLink",
                            "",
                        ),
                        external_id=item.get(
                            "id"
                        ),
                        metadata={
                            "authors": authors,
                            "published_date": info.get(
                                "publishedDate"
                            ),
                            "categories": info.get(
                                "categories",
                                []
                            ),
                            "description": description,
                        },
                    )
                )

            return {
                "documents": documents
            }

        except Exception as exc:

            return {
                "documents": [],
                "error": str(exc),
            }


# ============================================================================
# WIKIPEDIA
# ============================================================================

async def fetch_wikipedia(
    query: str,
    lang: str = "en",
    limit: int = 3,
) -> Dict[str, Any]:

    search_url = (
        f"https://{lang}.wikipedia.org/"
        "w/api.php"
    )

    summary_base = (
        f"https://{lang}.wikipedia.org/"
        "api/rest_v1/page/summary/"
    )

    params = {
        "action": "query",
        "list": "search",
        "srsearch": query,
        "format": "json",
        "srlimit": limit,
        "srprop": "",
    }

    async with _client() as client:

        try:

            response = await client.get(
                search_url,
                params=params,
            )

            if response.status_code != 200:
                return {
                    "documents": []
                }

            search_results = response.json().get(
                "query",
                {}
            ).get(
                "search",
                []
            )

            documents = []

            for result in search_results:

                title = result.get(
                    "title",
                    ""
                )

                try:

                    summary_response = await client.get(
                        f"{summary_base}{title}"
                    )

                    if summary_response.status_code != 200:
                        continue

                    data = summary_response.json()

                    extract = data.get(
                        "extract",
                        ""
                    )

                    documents.append(
                        normalize_document(
                            source="wikipedia",
                            source_type="encyclopedia",
                            content=extract,
                            title=title,
                            url=(
                                data.get(
                                    "content_urls",
                                    {}
                                )
                                .get(
                                    "desktop",
                                    {}
                                )
                                .get(
                                    "page",
                                    ""
                                )
                            ),
                            external_id=title,
                            metadata={
                                "language": lang,
                                "description": data.get(
                                    "description"
                                ),
                            },
                        )
                    )

                except Exception:
                    continue

            return {
                "documents": documents
            }

        except Exception as exc:

            return {
                "documents": [],
                "error": str(exc),
            }


# ============================================================================
# GITHUB
# ============================================================================

async def fetch_github_ebooks(
    query: str,
    limit: int = DEFAULT_LIMIT,
) -> Dict[str, Any]:

    token = os.getenv(
        "GITHUB_TOKEN"
    )

    headers = {
        "Accept": (
            "application/vnd.github+json"
        )
    }

    if token:
        headers[
            "Authorization"
        ] = f"Bearer {token}"

    source = get_source(
        "github"
    )

    params = {
        "q": f"{query} ebook",
        "per_page": limit,
    }

    async with _client() as client:

        try:

            response = await client.get(
                f"{source['base_url']}/search/repositories",
                headers=headers,
                params=params,
            )

            if response.status_code != 200:
                return {
                    "documents": []
                }

            items = response.json().get(
                "items",
                []
            )

            documents = []

            for repo in items:

                content = (
                    repo.get(
                        "description"
                    )
                    or ""
                )

                documents.append(
                    normalize_document(
                        source="github",
                        source_type="repository",
                        content=content,
                        title=repo.get(
                            "full_name",
                            ""
                        ),
                        url=repo.get(
                            "html_url",
                            ""
                        ),
                        external_id=str(
                            repo.get(
                                "id"
                            )
                        ),
                        metadata={
                            "stars": repo.get(
                                "stargazers_count"
                            ),
                            "language": repo.get(
                                "language"
                            ),
                            "description": repo.get(
                                "description"
                            ),
                        },
                    )
                )

            return {
                "documents": documents
            }

        except Exception as exc:

            return {
                "documents": [],
                "error": str(exc),
            }


# ============================================================================
# CODE TEXTBOOK
# ============================================================================

async def fetch_code_textbook(
    query: str,
) -> Dict[str, Any]:

    return await fetch_elibrary(
        f"{query} programming"
    )


# ============================================================================
# ALPHA VANTAGE
# ============================================================================

async def fetch_alphavantage(
    symbol: str,
) -> Dict[str, Any]:

    api_key = os.getenv(
        "ALPHA_VANTAGE_API_KEY"
    )

    if not api_key:
        return {
            "documents": [],
            "note": (
                "ALPHA_VANTAGE_API_KEY not set"
            ),
        }

    source = get_source(
        "alphavantage"
    )

    params = {
        "function": "GLOBAL_QUOTE",
        "symbol": symbol,
        "apikey": api_key,
    }

    async with _client() as client:

        try:

            response = await client.get(
                source["base_url"],
                params=params,
            )

            if response.status_code != 200:
                return {
                    "documents": []
                }

            quote = response.json().get(
                "Global Quote",
                {}
            )

            content = str(
                quote
            )

            return {
                "documents": [
                    normalize_document(
                        source="alphavantage",
                        source_type="financial",
                        content=content,
                        title=symbol,
                        external_id=symbol,
                        metadata={
                            "quote": quote
                        },
                    )
                ]
            }

        except Exception as exc:

            return {
                "documents": [],
                "error": str(exc),
            }


# ============================================================================
# FINANCIAL MODELING PREP
# ============================================================================

async def fetch_financial_modelling_prep(
    symbol: str,
) -> Dict[str, Any]:

    api_key = os.getenv(
        "FMP_API_KEY"
    )

    if not api_key:
        return {
            "documents": [],
            "note": (
                "FMP_API_KEY not set"
            ),
        }

    source = get_source(
        "financial_modeling_prep"
    )

    url = (
        f"{source['base_url']}/"
        f"profile/{symbol}"
    )

    params = {
        "apikey": api_key
    }

    async with _client() as client:

        try:

            response = await client.get(
                url,
                params=params,
            )

            if response.status_code != 200:
                return {
                    "documents": []
                }

            data = response.json()

            profile = (
                data[0]
                if data
                else {}
            )

            content = str(
                profile
            )

            return {
                "documents": [
                    normalize_document(
                        source=(
                            "financial_modeling_prep"
                        ),
                        source_type="financial",
                        content=content,
                        title=symbol,
                        external_id=symbol,
                        metadata={
                            "profile": profile
                        },
                    )
                ]
            }

        except Exception as exc:

            return {
                "documents": [],
                "error": str(exc),
            }


# ============================================================================
# YOUTUBE
# ============================================================================

async def fetch_youtube_videos(
    query: str,
    limit: int = DEFAULT_LIMIT,
) -> Dict[str, Any]:
    """
    Search YouTube and return normalized video documents.

    This retrieves metadata through the YouTube Data API.

    Transcript/subtitle acquisition is intentionally a separate step.
    web_crawler.py can decide whether transcript retrieval is required.
    """

    api_key = os.getenv(
        "YOUTUBE_API_KEY"
    )

    if not api_key:
        return {
            "documents": [],
            "note": (
                "YOUTUBE_API_KEY not set"
            ),
        }

    source = get_source(
        "youtube"
    )

    params = {
        "part": "snippet",
        "q": query,
        "type": "video",
        "maxResults": limit,
        "key": api_key,
    }

    async with _client() as client:

        try:

            response = await client.get(
                f"{source['base_url']}/search",
                params=params,
            )

            if response.status_code != 200:
                return {
                    "documents": []
                }

            items = response.json().get(
                "items",
                []
            )

            documents = []

            for item in items:

                video_id = (
                    item.get(
                        "id",
                        {}
                    ).get(
                        "videoId"
                    )
                )

                snippet = item.get(
                    "snippet",
                    {}
                )

                title = snippet.get(
                    "title",
                    ""
                )

                description = snippet.get(
                    "description",
                    ""
                )

                content = (
                    f"{title}\n"
                    f"{description}"
                )

                documents.append(
                    normalize_document(
                        source="youtube",
                        source_type="video",
                        content=content,
                        title=title,
                        url=(
                            f"https://www.youtube.com/"
                            f"watch?v={video_id}"
                        ),
                        external_id=video_id,
                        metadata={
                            "channel_id": snippet.get(
                                "channelId"
                            ),
                            "channel_title": snippet.get(
                                "channelTitle"
                            ),
                            "published_at": snippet.get(
                                "publishedAt"
                            ),
                            "thumbnails": snippet.get(
                                "thumbnails",
                                {}
                            ),
                            "transcript_available": False,
                            "subtitles_available": False,
                        },
                    )
                )

            return {
                "documents": documents
            }

        except Exception as exc:

            return {
                "documents": [],
                "error": str(exc),
            }


# ============================================================================
# YOUTUBE VIDEO METADATA
# ============================================================================

async def fetch_youtube_metadata(
    video_id: str,
) -> Dict[str, Any]:
    """
    Fetch detailed metadata for one YouTube video.
    """

    api_key = os.getenv(
        "YOUTUBE_API_KEY"
    )

    if not api_key:
        return {
            "documents": [],
            "note": (
                "YOUTUBE_API_KEY not set"
            ),
        }

    source = get_source(
        "youtube"
    )

    params = {
        "part": (
            "snippet,"
            "contentDetails,"
            "statistics"
        ),
        "id": video_id,
        "key": api_key,
    }

    async with _client() as client:

        try:

            response = await client.get(
                f"{source['base_url']}/videos",
                params=params,
            )

            if response.status_code != 200:
                return {
                    "documents": []
                }

            items = response.json().get(
                "items",
                []
            )

            if not items:
                return {
                    "documents": []
                }

            item = items[0]

            snippet = item.get(
                "snippet",
                {}
            )

            content_details = item.get(
                "contentDetails",
                {}
            )

            statistics = item.get(
                "statistics",
                {}
            )

            title = snippet.get(
                "title",
                ""
            )

            description = snippet.get(
                "description",
                ""
            )

            content = (
                f"{title}\n"
                f"{description}"
            )

            return {
                "documents": [
                    normalize_document(
                        source="youtube",
                        source_type="video",
                        content=content,
                        title=title,
                        url=(
                            f"https://www.youtube.com/"
                            f"watch?v={video_id}"
                        ),
                        external_id=video_id,
                        metadata={
                            "channel_id": snippet.get(
                                "channelId"
                            ),
                            "channel_title": snippet.get(
                                "channelTitle"
                            ),
                            "published_at": snippet.get(
                                "publishedAt"
                            ),
                            "duration": content_details.get(
                                "duration"
                            ),
                            "definition": content_details.get(
                                "definition"
                            ),
                            "statistics": statistics,
                            "caption_flag": content_details.get(
                                "caption"
                            ),
                        },
                    )
                ]
            }

        except Exception as exc:

            return {
                "documents": [],
                "error": str(exc),
            }


# ============================================================================
# APITUBE
# ============================================================================

async def fetch_apitube_videos(
    query: str,
    limit: int = DEFAULT_LIMIT,
) -> Dict[str, Any]:
    """
    APITube video/media discovery adapter.

    The exact API route may vary according to the APITube account/product
    being used. Therefore the endpoint is configurable through:

        APITUBE_API_BASE_URL

    rather than being permanently embedded into the crawler.
    """

    api_key = os.getenv(
        "APITUBE_API_KEY"
    )

    if not api_key:
        return {
            "documents": [],
            "note": (
                "APITUBE_API_KEY not set"
            ),
        }

    base_url = os.getenv(
        "APITUBE_API_BASE_URL",
        "https://api.apitube.io",
    )

    endpoint = os.getenv(
        "APITUBE_VIDEO_SEARCH_PATH",
        "/v1/videos/search",
    )

    params = {
        "q": query,
        "limit": limit,
        "api_key": api_key,
    }

    async with _client() as client:

        try:

            response = await client.get(
                f"{base_url.rstrip('/')}"
                f"/{endpoint.lstrip('/')}",
                params=params,
            )

            if response.status_code != 200:
                return {
                    "documents": [],
                    "error": (
                        f"HTTP "
                        f"{response.status_code}"
                    ),
                }

            data = response.json()

            items = (
                data.get("results")
                or data.get("items")
                or data.get("videos")
                or []
            )

            documents = []

            for item in items:

                title = (
                    item.get("title")
                    or ""
                )

                description = (
                    item.get(
                        "description"
                    )
                    or ""
                )

                url = (
                    item.get("url")
                    or item.get(
                        "web_url"
                    )
                    or ""
                )

                external_id = (
                    item.get("id")
                    or item.get(
                        "video_id"
                    )
                )

                content = (
                    f"{title}\n"
                    f"{description}"
                )

                documents.append(
                    normalize_document(
                        source="apitube",
                        source_type="video",
                        content=content,
                        title=title,
                        url=url,
                        external_id=(
                            str(external_id)
                            if external_id
                            else None
                        ),
                        metadata={
                            "raw_provider": item,
                            "transcript_available": bool(
                                item.get(
                                    "transcript"
                                )
                            ),
                            "subtitles_available": bool(
                                item.get(
                                    "subtitles"
                                )
                            ),
                        },
                    )
                )

            return {
                "documents": documents
            }

        except Exception as exc:

            return {
                "documents": [],
                "error": str(exc),
            }


# ============================================================================
# VIDEO TRANSCRIPT NORMALIZATION
# ===================================================

def normalize_video_transcript(
    *,
    source: str,
    video_id: str,
    transcript: str,
    title: str = "",
    url: str = "",
    metadata: Optional[
        Dict[str, Any]
    ] = None,
) -> Dict[str, Any]:
    """
    Convert a retrieved video transcript into a crawler document.

    The actual transcript acquisition is deliberately left to the
    appropriate provider/crawler implementation.
    """

    metadata = dict(
        metadata or {}
    )

    metadata[
        "transcript_available"
    ] = bool(
        transcript
    )

    return normalize_document(
        source=source,
        source_type="video_transcript",
        content=transcript,
        title=title,
        url=url,
        external_id=video_id,
        metadata=metadata,
    )


# ============================================================================
# PROVIDER DISPATCH
# ============================================================================

async def search_external(
    source: str,
    query: str,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Generic provider dispatcher.

    web_crawler.py can call:

        await search_external(
            "youtube",
            query,
        )

    without knowing the implementation details of the provider.
    """

    source = normalize_source(
        source
    )

    if source == "dictionary":
        return await fetch_dictionary(
            query
        )

    if source == "news":
        return await fetch_news(
            query,
            **kwargs,
        )

    if source == "openlibrary":
        return await fetch_books(
            query,
            **kwargs,
        )

    if source == "google_books":
        return await fetch_elibrary(
            query,
            **kwargs,
        )

    if source == "wikipedia":
        return await fetch_wikipedia(
            query,
            **kwargs,
        )

    if source == "github":
        return await fetch_github_ebooks(
            query,
            **kwargs,
        )

    if source == "youtube":
        return await fetch_youtube_videos(
            query,
            **kwargs,
        )

    if source == "apitube":
        return await fetch_apitube_videos(
            query,
            **kwargs,
        )

    raise ValueError(
        f"Unsupported external source: "
        f"{source}"
    )


# ============================================================================
# SOURCE METADATA
# ============================================================================

def source_metadata(
    source: str,
) -> Dict[str, Any]:
    """
    Return crawler-facing information about a source.
    """

    config = get_source(
        source
    )

    if not config:
        return {}

    result = dict(
        config
    )

    environment_key = config.get(
        "environment_key"
    )

    if environment_key:
        result[
            "configured"
        ] = bool(
            os.getenv(
                environment_key
            )
        )
    else:
        result[
            "configured"
        ] = True

    return result


# ============================================================================
# REGISTRY
# ============================================================================

def external_registry() -> Dict[str, Any]:
    """
    Return the complete external provider registry.

    Useful for web_crawler.py initialization and diagnostics.
    """

    return {
        source: source_metadata(
            source
        )
        for source in list_sources()
    }


# ============================================================================
# DEVELOPMENT TEST
# ============================================================================

if __name__ == "__main__":

    print(
        "Registered external sources:"
    )

    for source in list_sources():

        info = source_metadata(
            source
        )

        print(
            source,
            "->",
            info.get(
                "provider"
            ),
            "| configured:",
            info.get(
                "configured"
            ),
        )