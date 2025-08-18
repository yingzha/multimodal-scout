#!/usr/bin/env python3
"""
Centralized LLM client initialization for Google Gemini.
"""

import os
from google import genai
from .logger import logger

# --- AI Client Initialization ---
try:
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY environment variable not set")

    genai_client = genai.Client(api_key=api_key)
    AI_ENABLED = True
    logger.info("Google Gemini client initialized successfully")
except (ValueError, ImportError) as e:
    logger.warning(
        f"Google Gemini client initialization failed. AI features will be disabled. Error: {e}"
    )
    genai_client = None
    AI_ENABLED = False
