"""
This module contains constant values used across the backend application,
such as lists of keywords for filtering or categorization.
"""

# --- Scraper Configuration ---
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"

# --- AI Configuration ---
GEMINI_MODEL_NAME = "gemini-2.5-flash"

# A list of keywords to identify sources of interest.
# This can be expanded with more specific terms related to your focus area,
# such as "multimodal", "llm", "computer vision", etc.
INTERESTED_KEYWORDS = [
    "multimodal",
    "image understanding",
    "video understanding",
    "visual agents",
]

# --- Search Configuration ---
# Higher threshold for research papers to be more selective
RESEARCH_THRESHOLD = 0.65
# Lower threshold for industry content to include more variety
INDUSTRY_THRESHOLD = 0.6
# Discovery mode threshold for finding relevant content without specific topics
DISCOVERY_THRESHOLD = 0.65

# --- RSS Sources Configuration ---
# Maximum number of items to retrieve from each RSS feed
RSS_FEED_LIMIT = 5

# --- Comment Insights Configuration ---
# Minimum number of comments required to generate insights
MIN_COMMENTS_FOR_INSIGHTS = 10
