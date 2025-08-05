import json
import os
from typing import Dict, Optional

from .logger import logger

# Determine the project root directory (which is two levels up from this file's directory)
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
CACHE_FILE_PATH = os.path.join(PROJECT_ROOT, "summary_cache.json")


def load_cache() -> Dict[str, str]:
    """Loads the summary cache from a JSON file."""
    if not os.path.exists(CACHE_FILE_PATH):
        return {}
    try:
        with open(CACHE_FILE_PATH, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def save_cache(cache_data: Dict[str, str]):
    """Saves the summary cache to a JSON file."""
    try:
        with open(CACHE_FILE_PATH, 'w') as f:
            json.dump(cache_data, f, indent=2)
    except IOError as e:
        logger.error(f"Error saving cache: {e}")


def get_summary_from_cache(link: str, cache: Dict[str, str]) -> Optional[str]:
    """Retrieves a summary for a given link from the cache."""
    return cache.get(link)


def add_summary_to_cache(link: str, summary: str, cache: Dict[str, str]):
    """Adds a new summary to the cache."""
    cache[link] = summary