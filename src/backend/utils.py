import os
from typing import Optional

from google import genai
import requests
from bs4 import BeautifulSoup
from pydantic import HttpUrl

from .constants import GEMINI_MODEL_NAME, USER_AGENT
from .logger import logger

# --- API Key Configuration ---
# It's highly recommended to set your GOOGLE_API_KEY as an environment variable
# for security. The library will automatically pick it up.
# Example: export GOOGLE_API_KEY="your_api_key_here"
try:
    client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
    AI_ENABLED = True
    logger.info("Google Generative AI configured successfully.")
except KeyError:
    logger.warning("GOOGLE_API_KEY environment variable not set. AI features will be disabled.")
    AI_ENABLED = False


def _fetch_article_text(link: HttpUrl) -> Optional[str]:
    """Fetches and extracts the main text content from a URL."""
    try:
        response = requests.get(str(link), headers={'User-Agent': USER_AGENT}, timeout=20)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        # Heuristic to find main content: look for <article>, then <body>, and get <p> tags.
        main_content = soup.find('article') or soup.find('body')
        if not main_content:
            return None

        paragraphs = main_content.find_all('p')
        return " ".join([p.get_text() for p in paragraphs])
    except requests.RequestException as e:
        logger.error(f"Error fetching article content from {link}: {e}")
        return None


def generate_summary_from_link(link: HttpUrl) -> Optional[str]:
    """Generates a summary for a given URL using the Gemini API."""
    if not AI_ENABLED:
        return None

    logger.info(f"Generating summary for: {link}")
    article_text = _fetch_article_text(link)

    if not article_text or len(article_text.strip()) < 100:  # Don't summarize very short texts
        logger.info("Could not extract sufficient text to summarize. Return the original text instead")
        return article_text

    try:
        prompt = f"Please provide a concise, one-paragraph summary of the following article text:\n\n---\n\n{article_text[:4000]}"
        response = client.models.generate_content(model=GEMINI_MODEL_NAME, contents=[prompt])
        return response.text.strip()
    except Exception as e:
        logger.error(f"Error generating summary with Gemini: {e}")
        return None