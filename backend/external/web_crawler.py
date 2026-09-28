"""
CoMpaNeoN Web Crawler

External knowledge acquisition and MemoryGrid ingestion layer.

ARCHITECTURE

                external.py
                     |
          External source directions
                     |
                     v
             CrawlerScheduler
                     |
                     v
                WebCrawler
                     |
      +--------------+--------------+
      |              |              |
    Web          YouTube        ApiTube/API
      |              |              |
      +--------------+--------------+
                     |
                     v
             Content extraction
                     |
             checksum + metadata
                     |
                     v
                tokenizer.py
                     |
                     v
                MemoryGrid
                     |
      +--------------+--------------+
      |              |              |
   Letter Grid    Word Grid     Storage Grid
                                       |
                                       v
                               GridCrawler / GridCV
                                       |
                                       v
                                CrawlerRetrieval
                                       |
                                       v
                               Higher AI retrieval

RESPONSIBILITIES

WebCrawler:
  - acquire external information
  - accept scheduler directions
  - fetch HTML/API/video metadata
  - extract readable text
  - acquire subtitles/transcripts when available
  - calculate content checksums
  - detect unchanged content
  - attach source metadata
  - resolve language
  - send complete documents into MemoryGrid
  - coordinate scheduled crawling
  - expose crawl statistics

WebCrawler does NOT own:
  - GSP mathematics
  - alphabet mathematics
  - Word Grid mathematics
  - ranking
  - WordChain
  - WordUnderstanding
  - PromptManager
  - AI response generation
  - MemoryGrid placement mathematics

IMPORTANT

MemoryGrid remains the canonical indexing authority.
WebCrawler acquires.
MemoryGrid tokenizes and places.
CrawlerScheduler determines when crawling occurs.
"""

from __future__ import annotations

import hashlib
import inspect
import re

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx
from bs4 import BeautifulSoup


# ===========================================================================
# INTERNAL DEPENDENCIES
# ===========================================================================

from page_cache import PageCache

from crawler_scheduler import (
    CrawlerScheduler,
    ContentType,
)

from tokenizer import (
    normalize_lang,
    tokenize,
)


# ===========================================================================
# OPTIONAL EXTERNAL SOURCE ADAPTERS
# ===========================================================================

try:
    from external import (
        fetch_dictionary,
        fetch_news,
        fetch_books,
        fetch_elibrary,
        fetch_wikipedia,
        fetch_github_ebooks,
        fetch_code_textbook,
        fetch_alphavantage,
        fetch_financial_modelling_prep,
        fetch_youtube,
        fetch_apitube,
    )
except ImportError:
    fetch_dictionary = None
    fetch_news = None
    fetch_books = None
    fetch_elibrary = None
    fetch_wikipedia = None
    fetch_github_ebooks = None
    fetch_code_textbook = None
    fetch_alphavantage = None
    fetch_financial_modelling_prep = None
    fetch_youtube = None
    fetch_apitube = None


# ===========================================================================
# WEB CRAWLER
# ===========================================================================

class WebCrawler:
    """
    CoMpaNeoN external knowledge acquisition layer.

    The WebCrawler receives a shared MemoryGrid.
    It does not own a separate knowledge store.
    All acquired knowledge converges into MemoryGrid.add_document().

    Example
    -------
        crawler = WebCrawler(memory_grid)
        crawler.crawl("https://example.com")
        crawler.schedule("https://example.com")
        await crawler.acquire_external(source="wikipedia", query="quantum mechanics")
    """

    # -----------------------------------------------------------------------
    # INITIALIZATION
    # -----------------------------------------------------------------------
    def __init__(
        self,
        memory_grid: Any,
        timeout: float = 15.0,
        user_agent: str = "CoMpaNeoN-WebCrawler/1.0",
        scheduler: Optional[CrawlerScheduler] = None,
    ) -> None:

        self.memory = memory_grid
        self.page_cache = PageCache()

        self.scheduler = (
            scheduler if scheduler is not None else CrawlerScheduler()
        )

        self.timeout = float(timeout)
        self.user_agent = str(user_agent)

        # Statistics
        self.pages_crawled = 0
        self.pages_cached = 0
        self.pages_unchanged = 0
        self.documents_indexed = 0
        self.tokens_indexed = 0
        self.external_requests = 0
        self.external_documents = 0
        self.video_sources = 0
        self.transcripts_acquired = 0
        self.scheduled_jobs = 0
        self.scheduler_runs = 0

        # Source registry
        self.external_sources = {
            "dictionary": fetch_dictionary,
            "news": fetch_news,
            "books": fetch_books,
            "elibrary": fetch_elibrary,
            "wikipedia": fetch_wikipedia,
            "github_ebooks": fetch_github_ebooks,
            "code_textbook": fetch_code_textbook,
            "alphavantage": fetch_alphavantage,
            "financial_modeling_prep": fetch_financial_modelling_prep,
            "youtube": fetch_youtube,
            "apitube": fetch_apitube,
        }

    # -----------------------------------------------------------------------
    # TIME
    # -----------------------------------------------------------------------
    @staticmethod
    def _timestamp() -> str:
        return datetime.now(timezone.utc).isoformat()

    # -----------------------------------------------------------------------
    # HASH
    # -----------------------------------------------------------------------
    @staticmethod
    def content_hash(text: str) -> str:
        normalized = str(text).strip().replace("\r\n", "\n")
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    @staticmethod
    def source_hash(url: str) -> str:
        return hashlib.sha256(str(url).strip().encode("utf-8")).hexdigest()

    # -----------------------------------------------------------------------
    # HEADERS
    # -----------------------------------------------------------------------
    def _headers(self) -> Dict[str, str]:
        return {
            "User-Agent": self.user_agent,
            "Accept": (
                "text/html,"
                "application/xhtml+xml,"
                "application/json,"
                "text/plain"
            ),
        }

    # -----------------------------------------------------------------------
    # LANGUAGE
    # -----------------------------------------------------------------------
    def _resolve_language(self, lang: Optional[str]) -> str:
        return normalize_lang(lang or "en")

    def detect_language(self, text: str, fallback: str = "en") -> str:
        if not str(text).strip():
            return self._resolve_language(fallback)
        try:
            from langdetect import detect
            return normalize_lang(detect(text))
        except Exception:
            return self._resolve_language(fallback)

    # -----------------------------------------------------------------------
    # TEXT NORMALIZATION
    # -----------------------------------------------------------------------
    @staticmethod
    def normalize_text(text: str) -> str:
        text = str(text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    # -----------------------------------------------------------------------
    # FETCH
    # -----------------------------------------------------------------------
    def fetch_text(self, url: str) -> str:
        response = httpx.get(
            url,
            timeout=self.timeout,
            follow_redirects=True,
            headers=self._headers(),
        )
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        for element in soup(
            ["script", "style", "noscript", "template", "svg", "canvas"]
        ):
            element.decompose()

        return soup.get_text(separator=" ", strip=True)

    def fetch_json(
        self, url: str, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        response = httpx.get(
            url,
            params=params,
            timeout=self.timeout,
            follow_redirects=True,
            headers=self._headers(),
        )
        response.raise_for_status()
        data = response.json()
        if isinstance(data, dict):
            return data
        return {"data": data}

    # -----------------------------------------------------------------------
    # TOKENIZATION DIAGNOSTICS
    # -----------------------------------------------------------------------
    def inspect_tokens(self, text: str, lang: str = "en") -> Dict[str, Any]:
        lang = self._resolve_language(lang)
        tokens = tokenize(text, lang)
        return {
            "language": lang,
            "tokens": tokens,
            "token_count": len(tokens),
        }

    # -----------------------------------------------------------------------
    # METADATA
    # -----------------------------------------------------------------------
    def build_metadata(
        self,
        *,
        url: str = "",
        source_type: str = "web",
        lang: str = "en",
        title: str = "",
        content_hash: str = "",
        content_type: str = "text",
        author: str = "",
        published_at: Optional[str] = None,
        duration: Optional[float] = None,
        subtitles: bool = False,
        transcript: bool = False,
        extra: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:

        metadata: Dict[str, Any] = {
            "source": source_type,
            "source_url": url,
            "source_id": self.source_hash(url) if url else "",
            "title": title,
            "language": lang,
            "content_type": content_type,
            "content_hash": content_hash,
            "author": author,
            "published_at": published_at,
            "duration": duration,
            "subtitles_available": subtitles,
            "transcript_available": transcript,
            "acquired_at": self._timestamp(),
            "crawler": "CoMpaNeoN-WebCrawler",
            "crawler_version": "1.0",
        }

        if extra:
            metadata.update(extra)

        return metadata

    # -----------------------------------------------------------------------
    # MEMORY INGESTION
    # -----------------------------------------------------------------------
    def index_into_memory(
        self,
        text: str,
        *,
        url: str = "",
        lang: str = "en",
        source_type: Any = "web",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:

        text = self.normalize_text(text)
        if not text:
            return {"indexed": False, "reason": "empty_content"}

        lang = self._resolve_language(lang)
        token_data = self.inspect_tokens(text, lang)

        source_label = str(source_type)
        if url:
            source_label = f"{source_label}:{url}"

        try:
            doc_id = self.memory.add_document(
                text=text,
                lang=lang,
                source=source_label,
                metadata=metadata or {},
            )
        except TypeError:
            # Compatibility with MemoryGrid signatures that don't accept metadata.
            doc_id = self.memory.add_document(
                text=text,
                lang=lang,
                source=source_label,
            )

        self.documents_indexed += 1
        self.tokens_indexed += token_data["token_count"]

        return {
            "indexed": True,
            "doc_id": doc_id,
            "language": lang,
            "token_count": token_data["token_count"],
            "metadata": metadata or {},
        }

    # -----------------------------------------------------------------------
    # COMMON DOCUMENT ACQUISITION
    # -----------------------------------------------------------------------
    def acquire_document(
        self,
        text: str,
        *,
        url: str = "",
        lang: Optional[str] = None,
        source_type: str = "web",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:

        text = self.normalize_text(text)
        if not text:
            return {"indexed": False, "text": ""}

        resolved_lang = (
            self.detect_language(text)
            if lang is None
            else self._resolve_language(lang)
        )

        checksum = self.content_hash(text)

        final_metadata = (
            metadata
            or self.build_metadata(
                url=url,
                source_type=source_type,
                lang=resolved_lang,
                content_hash=checksum,
            )
        )
        final_metadata.setdefault("content_hash", checksum)
        final_metadata.setdefault("source_url", url)

        result = self.index_into_memory(
            text=text,
            url=url,
            lang=resolved_lang,
            source_type=source_type,
            metadata=final_metadata,
        )

        result.update(
            {
                "url": url,
                "source_type": source_type,
                "content_hash": checksum,
            }
        )
        return result

    # -----------------------------------------------------------------------
    # CRAWL ONE PAGE
    # -----------------------------------------------------------------------
    def crawl(
        self,
        url: str,
        source_type: Any = ContentType.NORMAL_WEB,
        lang: Optional[str] = None,
    ) -> Dict[str, Any]:

        requested_lang = (
            self._resolve_language(lang) if lang else None
        )

        # Fetch
        try:
            text = self.fetch_text(url)
        except Exception as exc:
            return {
                "url": url,
                "cached": False,
                "changed": False,
                "indexed": False,
                "error": str(exc),
            }

        text = self.normalize_text(text)
        if not text:
            return {
                "url": url,
                "cached": False,
                "changed": False,
                "indexed": False,
                "text": "",
            }

        self.pages_crawled += 1

        checksum = self.content_hash(text)
        changed = self.page_cache.has_changed(url, text)

        resolved_lang = (
            requested_lang or self.detect_language(text)
        )

        # Unchanged content
        if not changed:
            self.pages_unchanged += 1
            return {
                "url": url,
                "cached": True,
                "changed": False,
                "indexed": False,
                "language": resolved_lang,
                "content_hash": checksum,
            }

        metadata = self.build_metadata(
            url=url,
            source_type=str(source_type),
            lang=resolved_lang,
            content_hash=checksum,
            content_type="text/html",
        )

        indexed = self.acquire_document(
            text=text,
            url=url,
            lang=resolved_lang,
            source_type=str(source_type),
            metadata=metadata,
        )

        self.page_cache.set(url, checksum, text)

        return {
            "url": url,
            "cached": False,
            "changed": True,
            "language": resolved_lang,
            "content_hash": checksum,
            "indexed": indexed.get("indexed", False),
            "doc_id": indexed.get("doc_id"),
            "token_count": indexed.get("token_count", 0),
        }

    # -----------------------------------------------------------------------
    # SCHEDULING
    # -----------------------------------------------------------------------
    def schedule(
        self,
        url: str,
        source_type: Any = ContentType.NORMAL_WEB,
        lang: str = "en",
    ) -> Any:
        self.scheduled_jobs += 1
        return self.scheduler.schedule(
            url=url,
            source_type=source_type,
            lang=self._resolve_language(lang),
        )

    def schedule_many(
        self,
        urls: List[str],
        source_type: Any = ContentType.NORMAL_WEB,
        lang: str = "en",
    ) -> List[Any]:
        jobs = []
        for url in urls:
            jobs.append(
                self.schedule(url=url, source_type=source_type, lang=lang)
            )
        return jobs

    # -----------------------------------------------------------------------
    # SCHEDULER EXECUTION
    # -----------------------------------------------------------------------
    def run_scheduled(
        self, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:

        self.scheduler_runs += 1
        results: List[Dict[str, Any]] = []
        processed = 0

        # Direct run() API
        if hasattr(self.scheduler, "run"):
            try:
                scheduled_result = self.scheduler.run()
                if scheduled_result is not None:
                    if isinstance(scheduled_result, list):
                        for item in scheduled_result:
                            results.extend(self._execute_scheduled_item(item))
                            processed += 1
                            if limit is not None and processed >= limit:
                                return results
                        return results
            except TypeError:
                pass

        # Queue-style API
        resolver = None
        for method_name in ("next_job", "get_next", "next", "pop"):
            method = getattr(self.scheduler, method_name, None)
            if callable(method):
                resolver = method
                break

        if resolver is None:
            return results

        while True:
            if limit is not None and processed >= limit:
                break
            try:
                job = resolver()
            except Exception:
                break
            if job is None:
                break
            results.extend(self._execute_scheduled_item(job))
            processed += 1

        return results

    def _execute_scheduled_item(
        self, job: Any
    ) -> List[Dict[str, Any]]:

        if job is None:
            return []

        if isinstance(job, str):
            return [self.crawl(url=job)]

        if not isinstance(job, dict):
            return []

        url = job.get("url") or job.get("source_url")
        if not url:
            return []

        return [
            self.crawl(
                url=url,
                source_type=job.get("source_type", ContentType.NORMAL_WEB),
                lang=job.get("lang"),
            )
        ]

    # -----------------------------------------------------------------------
    # CRAWL MANY
    # -----------------------------------------------------------------------
    def crawl_many(
        self,
        urls: List[str],
        source_type: Any = ContentType.NORMAL_WEB,
        lang: Optional[str] = None,
    ) -> List[Dict[str, Any]]:

        results = []
        for url in urls:
            results.append(
                self.crawl(url=url, source_type=source_type, lang=lang)
            )
        return results

    # -----------------------------------------------------------------------
    # EXTERNAL SOURCE DISPATCH
    # -----------------------------------------------------------------------
    async def acquire_external(
        self,
        source: str,
        query: str,
        **kwargs: Any,
    ) -> Dict[str, Any]:

        source_key = str(source).strip().lower()
        adapter = self.external_sources.get(source_key)

        if adapter is None:
            return {
                "source": source_key,
                "query": query,
                "indexed": False,
                "error": f"No external adapter registered for {source_key}",
            }

        if not callable(adapter):
            return {
                "source": source_key,
                "query": query,
                "indexed": False,
                "error": f"Adapter unavailable: {source_key}",
            }

        self.external_requests += 1

        # Try with kwargs first, then fall back to query-only.
        try:
            result = adapter(query, **kwargs)
            if inspect.isawaitable(result):
                result = await result
        except TypeError:
            try:
                result = adapter(query)
                if inspect.isawaitable(result):
                    result = await result
            except Exception as exc:
                return {
                    "source": source_key,
                    "query": query,
                    "indexed": False,
                    "error": str(exc),
                }
        except Exception as exc:
            return {
                "source": source_key,
                "query": query,
                "indexed": False,
                "error": str(exc),
            }

        documents = self._extract_external_documents(result)
        indexed_documents = []

        for document in documents:
            text = document.get("text", "")
            if not text:
                continue

            indexed = self.acquire_document(
                text=text,
                url=document.get("url", ""),
                lang=document.get("language"),
                source_type=source_key,
                metadata=document.get("metadata", {}),
            )
            indexed_documents.append(indexed)

        self.external_documents += len(indexed_documents)

        return {
            "source": source_key,
            "query": query,
            "documents": indexed_documents,
            "document_count": len(indexed_documents),
            "indexed": bool(indexed_documents),
        }

    # -----------------------------------------------------------------------
    # EXTERNAL RESULT NORMALIZATION
    # -----------------------------------------------------------------------
    def _extract_external_documents(
        self, result: Any
    ) -> List[Dict[str, Any]]:

        documents: List[Dict[str, Any]] = []

        if result is None:
            return documents

        if isinstance(result, dict):
            # Direct text payload
            if result.get("text"):
                documents.append(
                    {
                        "text": result["text"],
                        "url": result.get("url", ""),
                        "language": result.get("language"),
                        "metadata": result.get("metadata", {}),
                    }
                )

            # Collection payloads
            for key in (
                "articles",
                "ebooks",
                "books",
                "elibrary",
                "code_books",
                "results",
                "items",
            ):
                items = result.get(key, [])
                if not isinstance(items, list):
                    continue

                for item in items:
                    if not isinstance(item, dict):
                        continue

                    text_parts = []
                    for field in (
                        "title",
                        "description",
                        "extract",
                        "summary",
                        "content",
                        "text",
                        "author",
                    ):
                        value = item.get(field)
                        if value:
                            text_parts.append(str(value))

                    if not text_parts:
                        continue

                    documents.append(
                        {
                            "text": "\n".join(text_parts),
                            "url": item.get("url") or item.get("infoLink", ""),
                            "language": item.get("language"),
                            "metadata": {"external_record": item},
                        }
                    )

            # Video results
            videos = result.get("videos", [])
            if isinstance(videos, list):
                for video in videos:
                    if isinstance(video, dict):
                        documents.extend(self._video_to_documents(video))

            # Direct transcript
            transcript = result.get("transcript")
            if transcript:
                documents.append(
                    {
                        "text": str(transcript),
                        "url": result.get("url", ""),
                        "language": result.get("language"),
                        "metadata": {
                            "content_type": "video_transcript",
                            "transcript": True,
                        },
                    }
                )

        elif isinstance(result, list):
            for item in result:
                documents.extend(self._extract_external_documents(item))

        return documents

    # -----------------------------------------------------------------------
    # VIDEO NORMALIZATION
    # -----------------------------------------------------------------------
    def _video_to_documents(
        self, video: Dict[str, Any]
    ) -> List[Dict[str, Any]]:

        self.video_sources += 1
        documents: List[Dict[str, Any]] = []

        title = video.get("title", "")
        description = video.get("description", "")
        url = video.get("url") or video.get("video_url", "")
        language = video.get("language")

        metadata = {
            "content_type": "video",
            "video_id": video.get("id"),
            "channel": video.get("channel"),
            "author": video.get("author"),
            "published_at": video.get("published_at"),
            "duration": video.get("duration"),
            "thumbnail": video.get("thumbnail"),
        }

        metadata_text = "\n".join(
            part for part in (title, description) if part
        )

        if metadata_text:
            documents.append(
                {
                    "text": metadata_text,
                    "url": url,
                    "language": language,
                    "metadata": metadata,
                }
            )

        subtitles = video.get("subtitles")
        if subtitles:
            subtitle_text = self._normalize_subtitles(subtitles)
            if subtitle_text:
                self.transcripts_acquired += 1
                documents.append(
                    {
                        "text": subtitle_text,
                        "url": url,
                        "language": language,
                        "metadata": {
                            **metadata,
                            "content_type": "video_subtitles",
                            "subtitles": True,
                        },
                    }
                )

        transcript = video.get("transcript")
        if transcript:
            self.transcripts_acquired += 1
            documents.append(
                {
                    "text": str(transcript),
                    "url": url,
                    "language": language,
                    "metadata": {
                        **metadata,
                        "content_type": "video_transcript",
                        "transcript": True,
                    },
                }
            )

        return documents

    # -----------------------------------------------------------------------
    # SUBTITLE NORMALIZATION
    # -----------------------------------------------------------------------
    def _normalize_subtitles(self, subtitles: Any) -> str:

        if isinstance(subtitles, str):
            return self.normalize_text(subtitles)

        if not isinstance(subtitles, list):
            return ""

        lines = []
        for item in subtitles:
            if isinstance(item, str):
                lines.append(item)
            elif isinstance(item, dict):
                text = (
                    item.get("text")
                    or item.get("caption")
                    or item.get("content")
                )
                if text:
                    lines.append(str(text))

        return self.normalize_text(" ".join(lines))

    # -----------------------------------------------------------------------
    # CONVENIENCE: YOUTUBE / APITUBE
    # -----------------------------------------------------------------------
    async def crawl_youtube(self, query: str, **kwargs: Any) -> Dict[str, Any]:
        return await self.acquire_external(
            source="youtube", query=query, **kwargs
        )

    async def crawl_apitube(self, query: str, **kwargs: Any) -> Dict[str, Any]:
        return await self.acquire_external(
            source="apitube", query=query, **kwargs
        )

    # -----------------------------------------------------------------------
    # SOURCE REGISTRY
    # -----------------------------------------------------------------------
    def register_source(self, name: str, adapter: Any) -> None:
        key = str(name).strip().lower()
        if not key:
            raise ValueError("Source name cannot be empty.")
        if not callable(adapter):
            raise TypeError("Source adapter must be callable.")
        self.external_sources[key] = adapter

    def available_sources(self) -> List[str]:
        return sorted(
            key
            for key, adapter in self.external_sources.items()
            if callable(adapter)
        )

    # -----------------------------------------------------------------------
    # STATISTICS
    # -----------------------------------------------------------------------
    def stats(self) -> Dict[str, Any]:
        return {
            "pages_crawled": self.pages_crawled,
            "pages_cached": self.pages_cached,
            "pages_unchanged": self.pages_unchanged,
            "documents_indexed": self.documents_indexed,
            "tokens_indexed": self.tokens_indexed,
            "external_requests": self.external_requests,
            "external_documents": self.external_documents,
            "video_sources": self.video_sources,
            "transcripts_acquired": self.transcripts_acquired,
            "scheduled_jobs": self.scheduled_jobs,
            "scheduler_runs": self.scheduler_runs,
            "available_sources": self.available_sources(),
        }


# ===========================================================================
# DEVELOPMENT TEST
# ===========================================================================
if __name__ == "__main__":
    print("CoMpaNeoN WebCrawler")
    print("WebCrawler requires a shared MemoryGrid instance.")