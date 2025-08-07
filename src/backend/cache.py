import json
import os
from typing import Dict, Optional

from logger import logger

# Keep legacy JSON cache for migration purposes
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
CACHE_FILE_PATH = os.path.join(PROJECT_ROOT, "summary_cache.json")

# Import new database functions
try:
    from db_cache import (
        get_summary_from_db, 
        add_summary_to_db,
        initialize_database
    )
    DATABASE_AVAILABLE = True
    # Initialize database on import
    try:
        initialize_database()
    except Exception as e:
        logger.warning(f"Database initialization failed, falling back to JSON: {e}")
        DATABASE_AVAILABLE = False
except ImportError as e:
    logger.warning(f"Database module not available, using JSON cache: {e}")
    DATABASE_AVAILABLE = False


def load_cache() -> Dict[str, str]:
    """Loads the summary cache from a JSON file (legacy)."""
    if not os.path.exists(CACHE_FILE_PATH):
        return {}
    try:
        with open(CACHE_FILE_PATH, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def save_cache(cache_data: Dict[str, str]):
    """Saves the summary cache to a JSON file (legacy)."""
    try:
        with open(CACHE_FILE_PATH, 'w') as f:
            json.dump(cache_data, f, indent=2)
    except IOError as e:
        logger.error(f"Error saving cache: {e}")


def get_summary_from_cache(link: str, cache: Dict[str, str] = None) -> Optional[str]:
    """Retrieves a summary for a given link from the cache."""
    if DATABASE_AVAILABLE:
        return get_summary_from_db(link)
    else:
        # Fallback to JSON cache
        if cache is None:
            cache = load_cache()
        return cache.get(link)


def add_summary_to_cache(link: str, summary: str, cache: Dict[str, str] = None):
    """Adds a new summary to the cache."""
    if DATABASE_AVAILABLE:
        add_summary_to_db(link, summary)
    else:
        # Fallback to JSON cache
        if cache is None:
            cache = load_cache()
        cache[link] = summary
        save_cache(cache)