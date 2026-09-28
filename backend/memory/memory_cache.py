"""
CoMpaNeoN Memory Cache
======================

Fast cache layer between the AI/session layer and MemoryGrid.

ARCHITECTURE
------------

                    ┌──────────────────────┐
                    │      AI / Session    │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │     MemoryCache      │
                    │                      │
                    │  session / recent   │
                    │  retrieval / context│
                    └───────┬───────┬──────┘
                            │       │
             device-facing │       │ cloud-facing
                            │       │
                            ▼       ▼
                    ┌──────────┐  ┌──────────────┐
                    │ Device   │  │ MemoryGrid   │
                    │ Cache    │  │ Cloud Store  │
                    └──────────┘  └──────┬───────┘
                                         │
                              ┌──────────┴──────────┐
                              │                     │
                             STM                   LTM

IMPORTANT
---------

MemoryCache is NOT the authoritative knowledge database.

The authoritative memory remains MemoryGrid.

The device-facing cache exists for:
    - current session
    - recent session context
    - temporary retrieval results
    - fast resume
    - temporary AI interaction state

Permanent knowledge belongs in MemoryGrid.

Memory partitions:
    - STM
    - LTM

remain logically separated.
"""

from __future__ import annotations

import hashlib
import json
import os
import time

from typing import (
    Any,
    Dict,
    List,
    Optional,
)


# =====================================================================
# CACHE PARTITIONS
# =====================================================================

STM = "stm"
LTM = "ltm"
SESSION = "session"
RETRIEVAL = "retrieval"


VALID_PARTITIONS = {
    STM,
    LTM,
    SESSION,
    RETRIEVAL,
}


# =====================================================================
# MEMORY CACHE
# =====================================================================

class MemoryCache:
    """
    Fast cache for CoMpaNeoN memory/session operations.

    The cache has two logical sides:

        CLOUD
        -----
        Temporary cloud-side cache associated with MemoryGrid access.

        DEVICE
        ------
        Device-facing cache containing recent session state.

    Neither cache replaces MemoryGrid.

    MemoryGrid remains the authoritative storage point.
    """

    def __init__(
        self,
        user_id: Optional[str] = None,
        device_id: Optional[str] = None,
        cache_dir: Optional[str] = None,
        session_limit: int = 100,
    ) -> None:

        self.user_id = (
            str(user_id)
            if user_id is not None
            else None
        )

        self.device_id = (
            str(device_id)
            if device_id is not None
            else None
        )

        self.session_limit = max(
            1,
            int(session_limit),
        )

        # --------------------------------------------------------------
        # CLOUD-SIDE CACHE
        #
        # Fast temporary cache associated with MemoryGrid access.
        # --------------------------------------------------------------

        self.cloud_cache: Dict[
            str,
            Dict[str, Any]
        ] = {}

        # --------------------------------------------------------------
        # DEVICE-FACING CACHE
        #
        # Recent session/cache state only.
        #
        # This is intentionally separate from cloud memory.
        # --------------------------------------------------------------

        self.device_cache: Dict[
            str,
            Dict[str, Any]
        ] = {}

        # --------------------------------------------------------------
        # Optional local session persistence.
        #
        # This is NOT the MemoryGrid.
        # It exists only for session/cache continuity.
        # --------------------------------------------------------------

        self.cache_dir = cache_dir

        if self.cache_dir:
            os.makedirs(
                self.cache_dir,
                exist_ok=True,
            )

    # =================================================================
    # KEY GENERATION
    # =================================================================

    def _key(
        self,
        query: str,
        partition: str = SESSION,
    ) -> str:
        """
        Generate a deterministic cache key.

        User and partition information are included so that cached
        memory from different partitions or users cannot accidentally
        collide.
        """

        partition = self._normalize_partition(
            partition
        )

        identity = (
            f"{self.user_id or 'anonymous'}:"
            f"{partition}:"
            f"{query.strip().lower()}"
        )

        return hashlib.sha256(
            identity.encode("utf-8")
        ).hexdigest()

    # =================================================================
    # PARTITION VALIDATION
    # =================================================================

    @staticmethod
    def _normalize_partition(
        partition: str,
    ) -> str:

        partition = str(
            partition or SESSION
        ).strip().lower()

        if partition not in VALID_PARTITIONS:
            raise ValueError(
                f"Unknown memory cache partition: {partition}"
            )

        return partition

    # =================================================================
    # CACHE RECORD
    # =================================================================

    def _record(
        self,
        query: str,
        data: Any,
        partition: str,
        source: str,
        persistent: bool = False,
    ) -> Dict[str, Any]:

        return {
            "query": query,
            "data": data,
            "partition": partition,
            "source": source,
            "user_id": self.user_id,
            "device_id": self.device_id,
            "created_at": time.time(),
            "persistent": bool(persistent),
        }

    # =================================================================
    # CLOUD CACHE
    # =================================================================

    def get(
        self,
        query: str,
        partition: str = SESSION,
    ) -> Any:
        """
        Retrieve temporary cloud-side cached data.

        This is normally used before querying MemoryGrid.
        """

        partition = self._normalize_partition(
            partition
        )

        key = self._key(
            query,
            partition,
        )

        entry = self.cloud_cache.get(key)

        if entry is None:
            return None

        return entry.get("data")

    def get_record(
        self,
        query: str,
        partition: str = SESSION,
    ) -> Optional[Dict[str, Any]]:
        """
        Return the complete cloud-cache record.
        """

        partition = self._normalize_partition(
            partition
        )

        key = self._key(
            query,
            partition,
        )

        entry = self.cloud_cache.get(key)

        if entry is None:
            return None

        return dict(entry)

    def set(
        self,
        query: str,
        data: Any,
        partition: str = SESSION,
    ) -> str:
        """
        Store temporary data in the cloud-side cache.

        This does NOT write permanent knowledge to MemoryGrid.
        """

        partition = self._normalize_partition(
            partition
        )

        key = self._key(
            query,
            partition,
        )

        self.cloud_cache[key] = self._record(
            query=query,
            data=data,
            partition=partition,
            source="memorygrid_cache",
        )

        return key

    # =================================================================
    # MEMORYGRID BRIDGE
    # =================================================================

    def get_or_fetch(
        self,
        query: str,
        memory_grid,
        partition: str = RETRIEVAL,
        fetcher=None,
    ) -> Any:
        """
        Retrieve from cache first, then MemoryGrid.

        Optional fetcher may be supplied for higher-level retrieval
        logic when MemoryGrid itself does not expose a direct query
        method.

        The returned MemoryGrid result is cached temporarily.

        This method does not alter MemoryGrid.
        """

        partition = self._normalize_partition(
            partition
        )

        cached = self.get(
            query,
            partition,
        )

        if cached is not None:
            return cached

        result = None

        if fetcher is not None:
            result = fetcher(
                memory_grid,
                query,
            )

        elif hasattr(
            memory_grid,
            "retrieve",
        ):
            result = memory_grid.retrieve(
                query
            )

        if result is None:
            return None

        self.set(
            query=query,
            data=result,
            partition=partition,
        )

        return result

    # =================================================================
    # STM
    # =================================================================

    def get_stm(
        self,
        query: str,
    ) -> Any:
        """
        Retrieve cached Short-Term Memory.
        """

        return self.get(
            query,
            STM,
        )

    def set_stm(
        self,
        query: str,
        data: Any,
    ) -> str:
        """
        Cache Short-Term Memory.
        """

        return self.set(
            query=query,
            data=data,
            partition=STM,
        )

    # =================================================================
    # LTM
    # =================================================================

    def get_ltm(
        self,
        query: str,
    ) -> Any:
        """
        Retrieve cached Long-Term Memory.
        """

        return self.get(
            query,
            LTM,
        )

    def set_ltm(
        self,
        query: str,
        data: Any,
    ) -> str:
        """
        Cache Long-Term Memory.

        Permanent LTM persistence still belongs to MemoryGrid.
        """

        return self.set(
            query=query,
            data=data,
            partition=LTM,
        )

    # =================================================================
    # RETRIEVAL CACHE
    # =================================================================

    def get_retrieval(
        self,
        query: str,
    ) -> Any:
        """
        Retrieve a cached MemoryGrid retrieval result.
        """

        return self.get(
            query,
            RETRIEVAL,
        )

    def set_retrieval(
        self,
        query: str,
        data: Any,
    ) -> str:
        """
        Cache a MemoryGrid retrieval result.
        """

        return self.set(
            query=query,
            data=data,
            partition=RETRIEVAL,
        )

    # =================================================================
    # DEVICE-FACING SESSION CACHE
    # =================================================================

    def device_get(
        self,
        query: str,
        partition: str = SESSION,
    ) -> Any:
        """
        Retrieve recent session/cache state intended for the user's
        device.

        This is not permanent MemoryGrid knowledge.
        """

        partition = self._normalize_partition(
            partition
        )

        key = self._key(
            query,
            partition,
        )

        entry = self.device_cache.get(key)

        if entry is None:
            return None

        return entry.get("data")

    def device_set(
        self,
        query: str,
        data: Any,
        partition: str = SESSION,
        persist: bool = True,
    ) -> str:
        """
        Store recent session state in the device-facing cache.

        Intended for:
            - active conversation
            - recent context
            - current workspace state
            - temporary retrieval state
            - session resume

        It must not be treated as authoritative knowledge.
        """

        partition = self._normalize_partition(
            partition
        )

        key = self._key(
            query,
            partition,
        )

        self.device_cache[key] = self._record(
            query=query,
            data=data,
            partition=partition,
            source="device_session_cache",
            persistent=persist,
        )

        self._trim_device_cache()

        if persist:
            self._persist_device_cache()

        return key

    # =================================================================
    # SESSION
    # =================================================================

    def cache_session(
        self,
        session_id: str,
        data: Any,
    ) -> str:
        """
        Store the current session in the device-facing cache.
        """

        return self.device_set(
            query=f"session:{session_id}",
            data=data,
            partition=SESSION,
            persist=True,
        )

    def get_session(
        self,
        session_id: str,
    ) -> Any:
        """
        Retrieve a locally cached session.
        """

        return self.device_get(
            query=f"session:{session_id}",
            partition=SESSION,
        )

    # =================================================================
    # DEVICE CACHE LIMIT
    # =================================================================

    def _trim_device_cache(self) -> None:
        """
        Keep only the newest device-facing session/cache records.
        """

        if len(self.device_cache) <= self.session_limit:
            return

        ordered = sorted(
            self.device_cache.items(),
            key=lambda item: item[1].get(
                "created_at",
                0,
            ),
        )

        remove_count = (
            len(self.device_cache)
            - self.session_limit
        )

        for key, _ in ordered[:remove_count]:
            self.device_cache.pop(
                key,
                None,
            )

    # =================================================================
    # DEVICE PERSISTENCE
    # =================================================================

    def _device_file(self) -> Optional[str]:
        """
        Return the device cache file.

        This file contains session/cache state only.
        """

        if not self.cache_dir:
            return None

        identity = (
            self.device_id
            or "default_device"
        )

        safe_identity = hashlib.sha256(
            identity.encode("utf-8")
        ).hexdigest()[:24]

        return os.path.join(
            self.cache_dir,
            f"session_cache_{safe_identity}.json",
        )

    def _persist_device_cache(self) -> None:
        """
        Persist the device-facing cache.

        This remains a cache artifact and is not the MemoryGrid store.
        """

        path = self._device_file()

        if not path:
            return

        serializable = {}

        for key, entry in self.device_cache.items():

            serializable[key] = {
                **entry,
                "created_at": entry.get(
                    "created_at"
                ),
            }

        with open(
            path,
            "w",
            encoding="utf-8",
        ) as file:

            json.dump(
                serializable,
                file,
                ensure_ascii=False,
                indent=2,
                default=str,
            )

    def load_device_cache(self) -> None:
        """
        Restore the recent device-facing session cache.
        """

        path = self._device_file()

        if not path or not os.path.exists(path):
            return

        try:

            with open(
                path,
                "r",
                encoding="utf-8",
            ) as file:

                data = json.load(file)

            if isinstance(data, dict):
                self.device_cache = data

            self._trim_device_cache()

        except (
            OSError,
            json.JSONDecodeError,
        ):
            self.device_cache = {}

    # =================================================================
    # CACHE PARTITION INSPECTION
    # =================================================================

    def partition(
        self,
        partition: str,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Return cloud-cache records belonging to one partition.
        """

        partition = self._normalize_partition(
            partition
        )

        return {
            key: value
            for key, value in self.cloud_cache.items()
            if value.get("partition") == partition
        }

    def device_partition(
        self,
        partition: str,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Return device-cache records belonging to one partition.
        """

        partition = self._normalize_partition(
            partition
        )

        return {
            key: value
            for key, value in self.device_cache.items()
            if value.get("partition") == partition
        }

    # =================================================================
    # CLEARING
    # =================================================================

    def clear_query(
        self,
        query: str,
        partition: str = SESSION,
    ) -> None:
        """
        Remove one cloud-cache entry.
        """

        partition = self._normalize_partition(
            partition
        )

        key = self._key(
            query,
            partition,
        )

        self.cloud_cache.pop(
            key,
            None,
        )

    def clear_device_query(
        self,
        query: str,
        partition: str = SESSION,
    ) -> None:
        """
        Remove one device-facing cache entry.
        """

        partition = self._normalize_partition(
            partition
        )

        key = self._key(
            query,
            partition,
        )

        self.device_cache.pop(
            key,
            None,
        )

        self._persist_device_cache()

    def clear_cloud(self) -> None:
        """
        Clear temporary cloud-side cache.

        MemoryGrid is untouched.
        """

        self.cloud_cache.clear()

    def clear_device(self) -> None:
        """
        Clear the device-facing session/cache.

        MemoryGrid is untouched.
        """

        self.device_cache.clear()

        path = self._device_file()

        if path and os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                pass

    def clear(self) -> None:
        """
        Clear both cache layers.

        MemoryGrid is untouched.
        """

        self.clear_cloud()
        self.clear_device()

    # =================================================================
    # STATISTICS
    # =================================================================

    def stats(self) -> Dict[str, Any]:
        """
        Return cache statistics.
        """

        cloud_partitions = {
            partition: len(
                self.partition(partition)
            )
           for partition in VALID_PARTITIONS
        }

        device_partitions = {
            partition: len(
                self.device_partition(partition)
            )

            for partition in VALID_PARTITIONS
        }

        return {
            "user_id": self.user_id,
            "device_id": self.device_id,
            "cloud_cache_entries": len(
                self.cloud_cache
            ),
            "device_cache_entries": len(
                self.device_cache
            ),
            "cloud_partitions": cloud_partitions,
            "device_partitions": device_partitions,
            "session_limit": self.session_limit,
        }