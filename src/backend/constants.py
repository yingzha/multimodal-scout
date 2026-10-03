"""
This module contains constant values used across the backend application,
such as lists of keywords for filtering or categorization.
"""

# --- Scraper Configuration ---
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"

# --- AI Configuration ---
# Model names, endpoint and similarity thresholds are environment settings (see config.py)
# Bounds for the keyword-suggestion prompt so it fits a local model's default context window
MAX_SUGGESTION_SUMMARY_CHARS = 300
MAX_SUGGESTION_PROMPT_CHARS = 6000

# A list of keywords to identify sources of interest.
# This can be expanded with more specific terms related to your focus area,
# such as "multimodal", "llm", "computer vision", etc.
INTERESTED_KEYWORDS = [
    "multimodal",
    "image understanding",
    "video understanding",
    "visual agents",
]

# --- RSS Sources Configuration ---
# Maximum number of items to retrieve from each RSS feed
RSS_FEED_LIMIT = 30

# --- Comment Insights Configuration ---
# Feature flag to enable/disable comment insights (disabled to keep pipeline runs short)
COMMENT_INSIGHTS_ENABLED = False
# Minimum number of comments required to generate insights
MIN_COMMENTS_FOR_INSIGHTS = 10
