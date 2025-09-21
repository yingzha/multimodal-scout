"""
Content Cache - Cache scraped and processed content with 5-min TTL
"""

import time
from typing import Dict, Any, Optional, List

from .logger import logger
from .schema import SourceSchema


class ContentCache:
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
            logger.info(f"Cache miss: selected_days changed from {self.cache_entry.get('selected_days')} to {selected_days}")
            return None

        logger.info("Content cache HIT - skipping expensive scraping and DB operations")
        return {
            "fresh_sources": self.cache_entry["fresh_sources"],
            "all_sources": self.cache_entry["all_sources"],
            "source_names": self.cache_entry["source_names"]
        }

    def set_cached_content(self, fresh_sources: List[SourceSchema], all_sources: List[SourceSchema],
                          source_names: List[str], selected_days: int):
        """Cache the scraped and processed content"""
        self.cache_entry = {
            "fresh_sources": fresh_sources,
            "all_sources": all_sources,
            "source_names": source_names,
            "selected_days": selected_days,
            "timestamp": time.time()
        }
        logger.info(f"Content cache SET - cached {len(fresh_sources)} fresh + {len(all_sources)} total sources")

    def clear(self):
        """Clear cache"""
        self.cache_entry = None
        logger.info("Content cache cleared")

    def get_cache_age(self) -> Optional[float]:
        """Get cache age in seconds"""
        if not self.cache_entry:
            return None
        return time.time() - self.cache_entry["timestamp"]


# Global instance
content_cache = ContentCache()