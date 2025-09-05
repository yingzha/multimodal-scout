#!/usr/bin/env python3
"""
Centralized LLM client initialization for Google Gemini.
"""

from google import genai
from .config import config
from .logger import logger

# --- AI Client Initialization ---
try:
    api_key = config.google_api_key
    if not api_key:
        raise ValueError("Google API key not configured")

    genai_client = genai.Client(api_key=api_key)
    logger.info("Google Gemini client initialized successfully")
except (ValueError, ImportError) as e:
    logger.warning(
        f"Google Gemini client initialization failed. AI features will be disabled. Error: {e}"
    )
    genai_client = None


def is_genai_enabled() -> bool:
    """Check if Google Gemini AI features are available."""
    return genai_client is not None
