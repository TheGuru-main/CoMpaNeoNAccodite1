"""
CoMpaNeoN Crawler Scheduler
============================

Controls when and why external sources should be crawled.

Responsibilities
----------------

CrawlerScheduler owns:

    - crawl frequency
    - priority
    - source type
    - crawl depth
    - next crawl time
    - content hash
    - crawl status
    - retry scheduling
    - queue ordering
    - duplicate URL prevention

CrawlerScheduler does NOT own:

    - HTTP requests
    - HTML extraction
    - API requests
    - tokenization
    - MemoryGrid indexing
    - grid traversal
    - ranking
    - data mixing
    - response generation

Architecture
------------

external.py
    ↓
WebCrawler
    ↓
CrawlerScheduler
    ↓
external source acquisition
    ↓
MemoryGrid
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional


# ======================================================================
# CONTENT TYPES
# ======================================================================

class ContentType(str, Enum):
    """
    Determines how frequently a source should normally be revisited.
    """

    HOT_NEWS = "hot_news"

    NORMAL_WEB = "normal_web"

    LOW_CHANGE = "low_change"

    DOCUMENTATION = "documentation"

    REFERENCE = "reference"

    VIDEO = "video"

    AUDIO = "audio"

    API = "api"


# ======================================================================
# DEFAULT CRAWL FREQUENCIES
# ======================================================================

FREQUENCIES: Dict[
    ContentType,
    timedelta,
] = {

    # Rapidly changing information.
    ContentType.HOT_NEWS:
        timedelta(minutes=30),

    # Ordinary websites.
    ContentType.NORMAL_WEB:
        timedelta(days=2),

    # Relatively static material.
    ContentType.LOW_CHANGE:
        timedelta(weeks=2),

    # Technical documentation.
    ContentType.DOCUMENTATION:
        timedelta(days=7),

    # Encyclopedic/reference material.
    ContentType.REFERENCE:
        timedelta(days=14),

    # Video metadata/subtitles/transcripts may change.
    ContentType.VIDEO:
        timedelta(days=3),

    # Audio metadata/transcripts.
    ContentType.AUDIO:
        timedelta(days=7),

    # API resources may need relatively frequent refresh.
    ContentType.API:
        timedelta(hours=6),
}


# ======================================================================
# PRIORITIES
# ======================================================================

DEFAULT_PRIORITIES: Dict[
    ContentType,
    int,
] = {

    ContentType.HOT_NEWS: 1,

    ContentType.API: 2,

    ContentType.NORMAL_WEB: 5,

    ContentType.VIDEO: 5,

    ContentType.AUDIO: 6,

    ContentType.DOCUMENTATION: 7,

    ContentType.REFERENCE: 8,

    ContentType.LOW_CHANGE: 10,
}


# ======================================================================
# QUEUE ITEM
# ======================================================================

@dataclass
class CrawlQueueItem:

    url: str

    source_type: ContentType = (
        ContentType.NORMAL_WEB
    )

    priority: int = 5

    depth: int = 0

    frequency: timedelta = field(
        default_factory=lambda:
            FREQUENCIES[
                ContentType.NORMAL_WEB
            ]
    )

    last_crawled: Optional[
        datetime
    ] = None

    next_crawl: Optional[
        datetime
    ] = None

    content_hash: Optional[
        str
    ] = None

    status: str = "pending"

    attempts: int = 0

    max_attempts: int = 3

    last_error: Optional[
        str
    ] = None

    created_at: datetime = field(
        default_factory=datetime.utcnow
    )

    updated_at: datetime = field(
        default_factory=datetime.utcnow
    )

    metadata: Dict[str, object] = field(
        default_factory=dict
    )

    @property
    def due(self) -> bool:
        """
        Whether this source is currently due for crawling.
        """

        if self.status not in {
            "pending",
            "scheduled",
            "retry",
        }:
            return False

        if self.next_crawl is None:
            return True

        return (
            datetime.utcnow()
            >= self.next_crawl
        )


# ======================================================================
# SCHEDULER
# ======================================================================

class CrawlerScheduler:

    def __init__(self) -> None:

        # URL → queue item
        self.queue: Dict[
            str,
            CrawlQueueItem
        ] = {}

    # ==================================================================
    # ADD / UPDATE
    # ==================================================================

    def schedule(
        self,
        url: str,
        source_type: ContentType = (
            ContentType.NORMAL_WEB
        ),
        depth: int = 0,
        priority: Optional[int] = None,
        metadata: Optional[
            Dict[str, object]
        ] = None,
    ) -> CrawlQueueItem:
        """
        Add a source to the crawl queue.

        Existing URLs are updated rather than duplicated.
        """

        source_type = ContentType(
            source_type
        )

        if priority is None:

            priority = (
                DEFAULT_PRIORITIES[
                    source_type
                ]
            )

        frequency = (
            FREQUENCIES[
                source_type
            ]
        )

        existing = self.queue.get(
            url
        )

        if existing is not None:

            # Upgrade priority if necessary.
            existing.priority = min(
                existing.priority,
                priority,
            )

            # Preserve the most specific
            # source classification.
            existing.source_type = (
                source_type
            )

            existing.frequency = (
                frequency
            )

            existing.depth = min(
                existing.depth,
                depth,
            )

            if metadata:
                existing.metadata.update(
                    metadata
                )

            existing.updated_at = (
                datetime.utcnow()
            )

            return existing

        item = CrawlQueueItem(
            url=url,
            source_type=source_type,
            priority=priority,
            depth=depth,
            frequency=frequency,
            metadata=metadata or {},
        )

        self.queue[url] = item

        return item

    # ==================================================================
    # ALIAS
    # ==================================================================

    def add_url(
        self,
        url: str,
        source_type: ContentType = (
            ContentType.NORMAL_WEB
        ),
        depth: int = 0,
        priority: Optional[int] = None,
    ) -> CrawlQueueItem:
        """
        Compatibility alias for schedule().
        """

        return self.schedule(
            url=url,
            source_type=source_type,
            depth=depth,
            priority=priority,
        )

    # ==================================================================
    # PRIORITY CALCULATION
    # ==================================================================

    def _sort_key(
        self,
        item: CrawlQueueItem,
    ):
        """
        Lower priority number = higher priority.
        Earlier due time = earlier crawl.
        """

        due_time = (
            item.next_crawl
            or datetime.min
        )

        return (
            item.priority,
            due_time,
            item.depth,
            item.created_at,
        )

    # ==================================================================
    # NEXT DUE SOURCE
    # ==================================================================

    def get_next_due(
        self,
    ) -> Optional[
        CrawlQueueItem
    ]:
        """
        Return the highest-priority source currently due.
        """

        due_items = [
            item
            for item in self.queue.values()
            if item.due
        ]

        if not due_items:
            return None

        due_items.sort(
            key=self._sort_key
        )

        item = due_items[0]

        item.status = "crawling"

        item.updated_at = (
            datetime.utcnow()
        )

        return item

    # ==================================================================
    # MARK CRAWL SUCCESS
    # ==================================================================

    def mark_crawled(
        self,
        url: str,
        content_hash: Optional[str] = None,
        next_crawl: Optional[
            datetime
        ] = None,
    ) -> Optional[
        CrawlQueueItem
    ]:
        """
        Mark a source as successfully crawled.

        If next_crawl is not explicitly supplied,
        frequency determines the next crawl time.
        """

        item = self.queue.get(
            url
        )

        if item is None:
            return None

        now = datetime.utcnow()

        item.last_crawled = now

        item.content_hash = (
            content_hash
        )

        item.next_crawl = (
            next_crawl
            or now + item.frequency
        )

        item.status = "scheduled"

        item.attempts = 0

        item.last_error = None

        item.updated_at = now

        return item

    # ==================================================================
    # MARK FAILURE
    # ==================================================================

    def mark_failed(
        self,
        url: str,
        error: str,
        retry: bool = True,
    ) -> Optional[
        CrawlQueueItem
    ]:
        """
        Record a crawl failure.

        Failed sources can be retried using a small exponential
        backoff rather than immediately hammering the source.
        """

        item = self.queue.get(
            url
        )

        if item is None:
            return None

        now = datetime.utcnow()

        item.attempts += 1

        item.last_error = str(
            error
        )

        item.updated_at = now

        if (
            retry
            and item.attempts
            < item.max_attempts
        ):

            # 5m → 10m → 20m
            backoff_minutes = (
                5 * (
                    2 ** (
                        item.attempts - 1
                    )
                )
            )

            item.next_crawl = (
                now
                + timedelta(
                    minutes=backoff_minutes
                )
            )

            item.status = "retry"

        else:

            item.status = "failed"

            item.next_crawl = None

        return item

    # ==================================================================
    # CONTENT HASH
    # ==================================================================

    def update_hash(
        self,
        url: str,
        content_hash: str,
    ) -> Optional[
        CrawlQueueItem
    ]:
        """
        Update the known content checksum without changing
        scheduling state.
        """

        item = self.queue.get(
            url
        )

        if item is None:
            return None

        item.content_hash = (
            content_hash
        )

        item.updated_at = (
            datetime.utcnow()
        )

        return item

    # ==================================================================
    # CHECK HASH
    # ==================================================================

    def has_changed(
        self,
        url: str,
        content_hash: str,
    ) -> bool:
        """
        Compare a newly acquired checksum against the known checksum.
        """

        item = self.queue.get(
            url
        )

        if item is None:
            return True

        if not item.content_hash:
            return True

        return (
            item.content_hash
            != content_hash
        )

    # ==================================================================
    # RESCHEDULE
    # ==================================================================

    def reschedule(
        self,
        url: str,
        next_crawl: datetime,
    ) -> Optional[
        CrawlQueueItem
    ]:

        item = self.queue.get(
            url
        )

        if item is None:
            return None

        item.next_crawl = (
            next_crawl
        )

        item.status = "scheduled"

        item.updated_at = (
            datetime.utcnow()
        )

        return item

    # ==================================================================
    # REMOVE
    # ==================================================================

    def remove(
        self,
        url: str,
    ) -> bool:
        """
        Remove a source from the scheduler.
        """

        if url not in self.queue:
            return False

        del self.queue[url]

        return True

    # ==================================================================
    # GET
    # ==================================================================

    def get(
        self,
        url: str,
    ) -> Optional[
        CrawlQueueItem
    ]:

        return self.queue.get(
            url
        )

    # ==================================================================
    # PENDING
    # ==================================================================

    def pending(
        self,
    ) -> List[
        CrawlQueueItem
    ]:
        """
        Return all pending/scheduled/retry sources ordered by priority.
        """

        items = [
            item
            for item in self.queue.values()
            if item.status in {
                "pending",
                "scheduled",
                "retry",
            }
        ]

        items.sort(
            key=self._sort_key
        )

        return items

    # ==================================================================
    # STATS
    # ==================================================================

    def stats(
        self,
    ) -> Dict[str, int]:
        counts = {}

        for item in self.queue.values():

            counts[
                item.status
            ] = (
                counts.get(
                    item.status,
                    0,
                ) + 1
            )

        return {
            "total": len(
                self.queue
            ),
            **counts,
        }