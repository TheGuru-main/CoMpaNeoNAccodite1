"""
Content-Based Web Crawler Cache

Provides persistent-friendly cache behavior for WebCrawler.

Responsibilities:
    - Cache fetched web content by URL.
    - Generate SHA-256 content signatures.
    - Detect unchanged/changed pages.
    - Track crawl metadata.
    - Support TTL expiration.
    - Return cached content directly to WebCrawler.
    - Preserve source URL and crawl timestamps.

The cache does NOT:
    - tokenize content
    - calculate GSP
    - place words in MemoryGrid
    - crawl MemoryGrid
    - perform ranking

WebCrawler remains responsible for fetching and indexing content.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple


class PageCache:
    """
    Cache layer used directly by WebCrawler.

    Each URL has one cache record:

        {
            "url": ...,
            "data": ...,
            "hash": ...,
            "created_at": ...,
            "updated_at": ...,
            "expires": ...,
            "fetch_count": ...,
        }

    Content itself remains the responsibility of the crawler/cache
    boundary. MemoryGrid indexing happens after WebCrawler obtains
    valid content.
    """

    def __init__(
        self,
        default_ttl_minutes: int = 120,
    ) -> None:

        self.default_ttl = timedelta(
            minutes=max(1, int(default_ttl_minutes))
        )

        self.cache: Dict[str, Dict[str, Any]] = {}

    # ==================================================================
    # TIME
    # ==================================================================

    @staticmethod
    def _now() -> datetime:
        """
        Return timezone-aware UTC time.
        """
        return datetime.now(timezone.utc)

    # ==================================================================
    # CONTENT HASH
    # ==================================================================

    @staticmethod
    def _hash(content: str) -> str:
        """
        Generate a deterministic SHA-256 signature for page content.
        """

        if content is None:
            content = ""

        if not isinstance(content, str):
            content = str(content)

        return hashlib.sha256(
            content.encode("utf-8")
        ).hexdigest()

    # ==================================================================
    # CACHE STATUS
    # ==================================================================

    def contains(self, url: str) -> bool:
        """
        Return True when a URL has a cache record.
        """

        return url in self.cache

    def is_valid(self, url: str) -> bool:
        """
        Return True when cached content exists and has not expired.
        """

        entry = self.cache.get(url)

        if not entry:
            return False

        return self._now() < entry["expires"]

    # ==================================================================
    # GET
    # ==================================================================

    def get(
        self,
        url: str,
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Return cached content and its content hash.

        Returns:

            (data, hash)

        When there is no valid cached entry:

            (None, None)

        Expired entries are not returned as valid content.
        """

        entry = self.cache.get(url)

        if not entry:
            return None, None

        if self._now() >= entry["expires"]:
            return None, None

        return (
            entry.get("data"),
            entry.get("hash"),
        )

    def get_entry(
        self,
        url: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Return the complete cache metadata for a URL.

        Returns None when no valid cache entry exists.
        """

        entry = self.cache.get(url)

        if not entry:
            return None

        if self._now() >= entry["expires"]:
            return None

        return dict(entry)

    # ==================================================================
    # SET
    # ==================================================================

    def set(
        self,
        url: str,
        content_hash: str,
        data: str,
        ttl_minutes: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Store fetched web content.

        The caller may provide an already calculated SHA-256 hash.
        """

        now = self._now()

        if ttl_minutes is None:
            ttl = self.default_ttl
        else:
            ttl = timedelta(
                minutes=max(1, int(ttl_minutes))
            )

        previous = self.cache.get(url)

        entry = {
            "url": url,
            "data": data,
            "hash": content_hash,
            "created_at": (
                previous.get("created_at", now)
                if previous
                else now
            ),
            "updated_at": now,
            "expires": now + ttl,
            "fetch_count": (
                int(previous.get("fetch_count", 0)) + 1
                if previous
                else 1
            ),
        }

        self.cache[url] = entry

        return dict(entry)

    # ==================================================================
    # WEBCRAWLER-FRIENDLY STORE
    # ==================================================================

    def store(
        self,
        url: str,
        content: str,
        ttl_minutes: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Store web-crawled content directly.

        This is the preferred method for WebCrawler when it already
        has the page body and does not need to calculate the hash
        separately.
        """

        content_hash = self._hash(content)

        return self.set(
            url=url,
            content_hash=content_hash,
            data=content,
            ttl_minutes=ttl_minutes,
        )

    # ==================================================================
    # CHANGE DETECTION
    # ==================================================================

    def has_changed(
        self,
        url: str,
        new_content: str,
    ) -> bool:
        """
        Determine whether newly fetched web content differs from the
        most recently known content hash.

        This checks the stored hash even when the previous cache entry
        has expired, allowing WebCrawler to detect content changes
        rather than treating every TTL expiration as a content change.
        """

        entry = self.cache.get(url)

        if not entry:
            return True

        new_hash = self._hash(new_content)

        return entry.get("hash") != new_hash

    def content_hash(
        self,
        url: str,
    ) -> Optional[str]:
        """
        Return the most recently stored content hash for a URL.

        Unlike get(), this can return the hash from an expired entry.
        """

        entry = self.cache.get(url)

        if not entry:
            return None

        return entry.get("hash")

    # ==================================================================
    # REFRESH
    # ==================================================================

    def refresh(
        self,
        url: str,
        content: str,
        ttl_minutes: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Replace the cached content with newly fetched content.
        """

        return self.store(
            url=url,
            content=content,
            ttl_minutes=ttl_minutes,
        )

    # ==================================================================
    # HASH-ONLY UPDATE
    # ==================================================================

    def update_content_hash(
        self,
        url: str,
        new_content: str,
    ) -> None:
        """
        Update only the known content hash.

        Useful when the crawler wants to record the latest signature
        without replacing the currently cached page body.
        """

        new_hash = self._hash(new_content)
        now = self._now()

        entry = self.cache.get(url)

        if entry:
            entry["hash"] = new_hash
            entry["updated_at"] = now
        else:
            self.cache[url] = {
                "url": url,
                "data": None,
                "hash": new_hash,
                "created_at": now,
                "updated_at": now,
                "expires": now,
                "fetch_count": 0,
            }

    # ==================================================================
    # EXPIRATION
    # ==================================================================

    def expire(
        self,
        url: str,
    ) -> bool:
        """
        Immediately expire a cached URL.
        """

        entry = self.cache.get(url)

        if not entry:
            return False

        entry["expires"] = self._now()

        return True

    def remove(
        self,
        url: str,
    ) -> bool:
        """
        Remove a URL completely from the cache.
        """

        if url not in self.cache:
            return False

        del self.cache[url]

        return True

    def clear(self) -> None:
        """
        Clear the entire in-memory cache.
        """

        self.cache.clear()

    def purge_expired(self) -> int:
        """
        Remove expired cache records.

        Returns the number of removed records.
        """

        now = self._now()

        expired = [
            url
            for url, entry in self.cache.items()
            if now >= entry["expires"]
        ]

        for url in expired:
            del self.cache[url]

        return len(expired)

    # ==================================================================
    # WEBCRAWLER ACCESS
    # ==================================================================

    def get_or_fetch(
        self,
        url: str,
        fetcher,
        ttl_minutes: Optional[int] = None,
    ) -> Tuple[str, bool]:
        """
        Cache-aware WebCrawler helper.

        fetcher must be a callable accepting the URL:

            fetcher(url) -> str

        Returns:

            (content, from_cache)

        Behavior:

            1. Return valid cached content when available.
            2. Otherwise fetch from the web.
            3. Store the fetched content.
            4. Return the new content.

        The WebCrawler therefore does not need to duplicate cache
        lookup logic.
        """

        cached_data, _ = self.get(url)

        if cached_data is not None:
            return cached_data, True

        content = fetcher(url)

        if content is None:
            content = ""

        self.store(
            url=url,
            content=content,
            ttl_minutes=ttl_minutes,
        )

        return content, False

    # ==================================================================
    # METADATA
    # ==================================================================

    def stats(self) -> Dict[str, int]:
        """
        Return basic cache statistics.
        """

        now = self._now()

        total = len(self.cache)

        valid = sum(
            1
            for entry in self.cache.values()
            if now < entry["expires"]
        )

        expired = total - valid

        return {
            "total": total,
            "valid": valid,
            "expired": expired,
        }