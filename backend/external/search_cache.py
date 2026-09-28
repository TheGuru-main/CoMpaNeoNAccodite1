from datetime import datetime, timedelta
import hashlib
import json

class SearchCache:
    def __init__(self, ttl_seconds=300):
        self.cache = {}
        self.ttl = timedelta(seconds=ttl_seconds)

    def _key(self, query: str) -> str:
        # Normalize and hash query for stable key
        q = query.strip().lower()
        return hashlib.sha256(q.encode()).hexdigest()

    def get(self, query: str):
        key = self._key(query)
        entry = self.cache.get(key)
        if entry and datetime.utcnow() < entry["expires"]:
            return entry["data"]
        # Cleanup expired
        if entry:
            del self.cache[key]
        return None

    def set(self, query: str, data):
        key = self._key(query)
        self.cache[key] = {
            "data": data,
            "expires": datetime.utcnow() + self.ttl
        }

    def clear(self):
        self.cache.clear()