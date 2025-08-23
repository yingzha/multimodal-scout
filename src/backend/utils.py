import re
import time
from typing import Optional

import requests
from bs4 import BeautifulSoup
from pydantic import HttpUrl

from .constants import GEMINI_MODEL_NAME, USER_AGENT
from .logger import logger
from .client import genai_client, is_genai_enabled


def _retry_with_backoff(func, max_retries=3, base_delay=1.0):
    """Retry a function with exponential backoff."""
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise e

            delay = base_delay * (2**attempt)
            logger.warning(
                f"Attempt {attempt + 1} failed: {e}. Retrying in {delay:.1f}s..."
            )
            time.sleep(delay)


def _fetch_article_text(link: HttpUrl) -> Optional[str]:
    """Fetches and extracts the main text content from a URL, including image alt text."""
    try:
        response = requests.get(
            str(link), headers={"User-Agent": USER_AGENT}, timeout=20
        )
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        # Heuristic to find main content: look for <article>, then <body>, and get <p> tags.
        main_content = soup.find("article") or soup.find("body")
        if not main_content:
            return None

        # Extract content in document order (paragraphs and images)
        content_parts = []

        # Find all paragraphs and images in document order
        for element in main_content.find_all(["p", "img"]):
            if element.name == "p":
                text = element.get_text().strip()
                if text:  # Only add non-empty paragraphs
                    content_parts.append(text)
            elif element.name == "img":
                alt_text = element.get("alt", "").strip()
                if alt_text and len(alt_text) > 3:  # Only meaningful alt text
                    content_parts.append(f"[Image: {alt_text}]")

        return " ".join(content_parts)
    except requests.RequestException as e:
        logger.error(f"Error fetching article content from {link}: {e}")
        return None


def _is_non_english_summary(text: str) -> bool:
    """
    Basic heuristic to detect if a summary might not be in English.
    Checks for common non-English patterns and character sets.
    """
    if not text:
        return False

    # Check for common non-English character patterns
    # Chinese/Japanese/Korean characters
    if re.search(r"[\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff\uac00-\ud7af]", text):
        return True

    # Arabic characters
    if re.search(r"[\u0600-\u06ff]", text):
        return True

    # Cyrillic characters
    if re.search(r"[\u0400-\u04ff]", text):
        return True

    # Use word boundaries to avoid false positives in English text
    # Common French words (basic check) - using word boundaries
    french_patterns = [
        r"\ble\b",
        r"\bla\b",
        r"\bles\b",
        r"\bdu\b",
        r"\bun\b",
        r"\bune\b",
        r"\bet\b",
        r"\best\b",
        r"\bdans\b",
        r"\bsur\b",
        r"\bavec\b",
        r"\bpour\b",
        r"\bpar\b",
        r"\bcomme\b",
        r"\bmais\b",
        r"\bqui\b",
        r"\bque\b",
        r"\bce\b",
        r"\bcette\b",
        r"\bces\b",
    ]
    french_count = sum(
        1 for pattern in french_patterns if re.search(pattern, text.lower())
    )
    if french_count > 5:  # Increased threshold to reduce false positives
        return True

    # Common German words (basic check) - using word boundaries and excluding common English words
    german_patterns = [
        r"\bder\b",
        r"\bdie\b",
        r"\bdas\b",
        r"\bden\b",
        r"\bdem\b",
        r"\beine\b",
        r"\beinen\b",
        r"\bund\b",
        r"\bist\b",
        r"\bmit\b",
        r"\bvon\b",
        r"\bzu\b",
        r"\bfür\b",
        r"\bauf\b",
        r"\bals\b",
        r"\bbei\b",
        r"\bnach\b",
        r"\büber\b",
        r"\bdurch\b",
    ]
    german_count = sum(
        1 for pattern in german_patterns if re.search(pattern, text.lower())
    )
    if german_count > 5:  # Increased threshold to reduce false positives
        return True

    # Common Spanish words (basic check) - using word boundaries
    spanish_patterns = [
        r"\bel\b",
        r"\bla\b",
        r"\blos\b",
        r"\blas\b",
        r"\bdel\b",
        r"\bun\b",
        r"\buna\b",
        r"\by\b",
        r"\bes\b",
        r"\ben\b",
        r"\bcon\b",
        r"\bpor\b",
        r"\bpara\b",
        r"\bcomo\b",
        r"\bmás\b",
        r"\bpero\b",
        r"\bque\b",
        r"\bse\b",
        r"\bsu\b",
        r"\bsus\b",
        r"\beste\b",
        r"\besta\b",
        r"\bestos\b",
        r"\bestas\b",
    ]
    spanish_count = sum(
        1 for pattern in spanish_patterns if re.search(pattern, text.lower())
    )
    if spanish_count > 5:  # Increased threshold to reduce false positives
        return True

    return False


def generate_summary_from_link(link: HttpUrl, title: str = None) -> Optional[str]:
    """Generates a summary for a given URL using the Gemini API."""
    if not is_genai_enabled():
        return None

    # Skip obvious test/invalid URLs to avoid unnecessary network requests
    link_str = str(link).lower()
    if any(
        test_domain in link_str
        for test_domain in ["example.com", "example.org", "test.com", "localhost"]
    ):
        logger.warning(f"Skipping summary generation for test URL: {link}")
        return None

    logger.info(f"Generating summary for: {link}")
    article_text = _fetch_article_text(link)

    if (
        not article_text or len(article_text.strip()) < 100
    ):  # Don't summarize very short texts
        logger.info(
            f"Could not extract sufficient text to summarize. Returning title as fallback: {title}"
        )
        return title or "No summary available"

    def _generate_summary():
        prompt = f"""Please provide a concise, one-paragraph summary of the following article text in English only.

Regardless of the source language, always respond in English. Focus on the key points and main insights.

Article text:
---
{article_text[:4000]}"""

        response = genai_client.models.generate_content(
            model=GEMINI_MODEL_NAME, contents=[prompt]
        )
        summary = response.text.strip()

        # Return the generated summary directly - if it's problematic, title fallback happens at higher level

        # Validate that the summary is in English by checking for common non-English patterns
        if _is_non_english_summary(summary):
            logger.warning(
                f"Generated summary appears to be non-English, regenerating..."
            )
            # Try again with more explicit English instruction
            english_prompt = f"""IMPORTANT: You must respond in English only. Do not use any other language.

Summarize this article in English, even if the source is in another language:

{article_text[:4000]}

Provide a concise English summary focusing on the main points."""

            response = genai_client.models.generate_content(
                model=GEMINI_MODEL_NAME, contents=[english_prompt]
            )
            summary = response.text.strip()

            # Return the regenerated summary directly

        return summary

    try:
        return _retry_with_backoff(_generate_summary, max_retries=3, base_delay=2.0)
    except Exception as e:
        logger.error(f"Error generating summary with Gemini after retries: {e}")
        return title or "No summary available"


def extract_title_from_url(url: HttpUrl) -> Optional[str]:
    """Extract title from a webpage."""
    try:
        response = requests.get(
            str(url), headers={"User-Agent": USER_AGENT}, timeout=20
        )
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        title_tag = soup.find("title")
        if title_tag:
            return title_tag.get_text().strip()

        # Fallback to h1 tag
        h1_tag = soup.find("h1")
        if h1_tag:
            return h1_tag.get_text().strip()

        return None
    except requests.RequestException as e:
        logger.error(f"Error extracting title from {url}: {e}")
        return None


def categorize_content(title: str, content: str, url: str) -> str:
    """Categorize content as Research, Industry, or General based on various signals."""
    if not is_genai_enabled():
        return "General"

    try:
        # Check for obvious research indicators in URL and title
        research_indicators = [
            "arxiv.org",
            "papers.nips.cc",
            "aclanthology.org",
            "openreview.net",
            "proceedings.",
            "conference",
            "journal",
            "acm.org",
            "ieee.org",
            "research.",
            "paper",
            "arxiv",
            "doi.org",
            "scholar.google",
        ]

        industry_indicators = [
            "blog",
            "medium.com",
            "dev.to",
            "hackernews",
            "techcrunch",
            "venturebeat",
            "wired.com",
            "theverge.com",
            "arstechnica",
            "company.",
            "startup",
            "product",
            "release",
            "announcement",
        ]

        url_lower = url.lower()
        title_lower = title.lower()

        # Strong signals from URL and title
        for indicator in research_indicators:
            if indicator in url_lower or indicator in title_lower:
                return "Research"

        for indicator in industry_indicators:
            if indicator in url_lower or indicator in title_lower:
                return "Industry"

        # Use AI to categorize based on content
        def _categorize():
            prompt = f"""Analyze the following article and categorize it as exactly one of: "Research", "Industry", or "General"

Guidelines:
- Research: Academic papers, research findings, scientific studies, conference proceedings, peer-reviewed content
- Industry: Product announcements, company news, startup updates, industry analysis, commercial applications
- General: Tutorials, opinion pieces, general news, educational content

Title: {title}
Content preview: {content[:1000]}

Respond with only one word: Research, Industry, or General"""

            response = genai_client.models.generate_content(
                model=GEMINI_MODEL_NAME, contents=[prompt]
            )
            return response.text.strip()

        try:
            category = _retry_with_backoff(_categorize, max_retries=2, base_delay=1.0)

            # Validate the response
            if category in ["Research", "Industry", "General"]:
                return category
            else:
                logger.warning(
                    f"AI returned invalid category '{category}', defaulting to General"
                )
                return "General"
        except Exception as inner_e:
            logger.warning(
                f"Failed to categorize with AI after retries: {inner_e}, defaulting to General"
            )
            return "General"

    except Exception as e:
        logger.error(f"Error categorizing content: {e}")
        return "General"
