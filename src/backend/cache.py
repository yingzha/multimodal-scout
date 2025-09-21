"""
Unified Cache Management

Consolidates all caching mechanisms across the backend:
1. Content Cache - Scraped content with 5-min TTL
2. Source Processing Cache - Recently processed sources
3. Comment Insights Cache - HN comment processing with 10-min TTL
4. LRU Cache utilities
"""

import time
from functools import lru_cache
from collections import OrderedDict
from typing import Dict, Any, Optional, List
from .logger import logger
from .schema import SourceSchema
from .constants import INTERESTED_KEYWORDS


# ============================================================================
# 1. Content Cache - Main performance optimization
# ============================================================================


class ContentCache:
    """Cache scraped and processed content with TTL"""

    def __init__(self, ttl_seconds: int = 300):  # 5 minutes
        self.ttl_seconds = ttl_seconds
        self.cache_entry: Optional[Dict[str, Any]] = None

    def get_cached_content(self, selected_days: int) -> Optional[Dict[str, Any]]:
        """Get cached scraped content if valid"""
        if not self.cache_entry:
            return None

        # Check if cache is expired
        if time.time() - self.cache_entry["timestamp"] > self.ttl_seconds:
            logger.info("Content cache expired, clearing...")
            self.cache_entry = None
            return None

        # Check if selected_days matches (database query depends on this)
        if self.cache_entry.get("selected_days") != selected_days:
            logger.info(
                f"Cache miss: selected_days changed from {self.cache_entry.get('selected_days')} to {selected_days}"
            )
            return None

        logger.info("Content cache HIT - skipping expensive scraping and DB operations")
        return {
            "fresh_sources": self.cache_entry["fresh_sources"],
            "all_sources": self.cache_entry["all_sources"],
            "source_names": self.cache_entry["source_names"],
        }

    def set_cached_content(
        self,
        fresh_sources: List[SourceSchema],
        all_sources: List[SourceSchema],
        source_names: List[str],
        selected_days: int,
    ):
        """Cache the scraped and processed content"""
        self.cache_entry = {
            "fresh_sources": fresh_sources,
            "all_sources": all_sources,
            "source_names": source_names,
            "selected_days": selected_days,
            "timestamp": time.time(),
        }
        logger.info(
            f"Content cache SET - cached {len(fresh_sources)} fresh + {len(all_sources)} total sources"
        )

    def clear(self):
        """Clear cache"""
        self.cache_entry = None
        logger.info("Content cache cleared")

    def get_cache_age(self) -> Optional[float]:
        """Get cache age in seconds"""
        if not self.cache_entry:
            return None
        return time.time() - self.cache_entry["timestamp"]


# ============================================================================
# 2. Source Processing Cache - Prevents duplicate processing
# ============================================================================


class SourceProcessingCache:
    """LRU cache to track recently processed sources"""

    def __init__(self, max_size: int = 10000):
        self._cache: OrderedDict[str, bool] = OrderedDict()
        self._max_size = max_size

    def is_recently_processed(self, link: str) -> bool:
        """Check if a source was recently processed and update its position in LRU"""
        if link in self._cache:
            # Move to end (most recently used)
            self._cache.move_to_end(link)
            return True
        return False

    def mark_as_processed(self, link: str):
        """Mark a source as recently processed using LRU eviction"""
        if link in self._cache:
            # Move to end (most recently used)
            self._cache.move_to_end(link)
        else:
            # Add new entry
            self._cache[link] = True

            # Remove least recently used items if over capacity
            while len(self._cache) > self._max_size:
                oldest_link = next(iter(self._cache))
                del self._cache[oldest_link]

        if len(self._cache) % 1000 == 0:  # Log periodically
            logger.info(
                f"Source processing cache size: {len(self._cache)}/{self._max_size}"
            )

    def clear(self):
        """Clear the cache"""
        self._cache.clear()

    def size(self) -> int:
        """Get current cache size"""
        return len(self._cache)


# ============================================================================
# 3. Comment Insights Cache - HN comment processing with TTL
# ============================================================================


class CommentInsightsCache:
    """Cache for HN comment insights processing with 10-minute TTL"""

    def __init__(self, ttl_seconds: int = 600):  # 10 minutes
        self.ttl_seconds = ttl_seconds
        self._cache: Dict[str, float] = {}  # link -> timestamp

    def is_recently_processed(self, link: str) -> bool:
        """Check if comment insights were recently processed for this link"""
        if link not in self._cache:
            return False

        if time.time() - self._cache[link] > self.ttl_seconds:
            # Expired, remove from cache
            del self._cache[link]
            return False

        return True

    def mark_as_processed(self, link: str):
        """Mark comment insights as processed for this link"""
        self._cache[link] = time.time()

        # Periodic cleanup of expired entries
        if len(self._cache) % 100 == 0:
            self._cleanup_expired()

    def _cleanup_expired(self):
        """Remove expired entries from cache"""
        current_time = time.time()
        expired_links = [
            link
            for link, timestamp in self._cache.items()
            if current_time - timestamp > self.ttl_seconds
        ]
        for link in expired_links:
            del self._cache[link]

        if expired_links:
            logger.info(
                f"Comment insights cache cleanup: Removed {len(expired_links)} expired entries"
            )


# ============================================================================
# 4. LRU Cache Utilities
# ============================================================================


@lru_cache(maxsize=1)
def get_cached_topics():
    """Cache static topics data - imported and used in app.py"""
    return {"topics": INTERESTED_KEYWORDS}


# ============================================================================
# Global Cache Instances
# ============================================================================

# Main content cache for performance optimization
content_cache = ContentCache(ttl_seconds=300)  # 5 minutes

# Source processing cache for database operations
source_processing_cache = SourceProcessingCache(max_size=10000)

# Comment insights cache for HN comment processing
comment_insights_cache = CommentInsightsCache(ttl_seconds=600)  # 10 minutes


# ============================================================================
# Cache Management Functions
# ============================================================================


def clear_all_caches():
    """Clear all in-memory caches"""
    content_cache.clear()
    source_processing_cache.clear()
    comment_insights_cache._cache.clear()
    get_cached_topics.cache_clear()
    logger.info("All in-memory caches cleared")


def get_cache_stats() -> Dict[str, Any]:
    """Get statistics for all caches"""
    content_age = content_cache.get_cache_age()

    return {
        "content_cache": {
            "has_data": content_cache.cache_entry is not None,
            "age_seconds": content_age,
            "ttl_seconds": content_cache.ttl_seconds,
            "expired": content_age is not None
            and content_age > content_cache.ttl_seconds,
        },
        "source_processing_cache": {
            "size": source_processing_cache.size(),
            "max_size": source_processing_cache._max_size,
        },
        "comment_insights_cache": {
            "size": len(comment_insights_cache._cache),
            "ttl_seconds": comment_insights_cache.ttl_seconds,
        },
        "lru_caches": {"topics_cache_info": get_cached_topics.cache_info()._asdict()},
    }
