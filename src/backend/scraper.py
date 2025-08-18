import json
from typing import List

import feedparser
import requests
from bs4 import BeautifulSoup
from pydantic import ValidationError

from .logger import logger
from .constants import USER_AGENT, RSS_FEED_LIMIT
from .schema import SourceSchema
from datetime import datetime
from dateutil import parser as date_parser
import re


def parse_rss_date(date_string: str) -> str:
    """
    Parse RSS date string and return ISO format with timezone.
    Handles multiple common RSS date formats.
    """
    try:
        # Try common RSS date formats first
        formats = [
            "%a, %d %b %Y %H:%M:%S %z",  # RFC 2822 with timezone
            "%a, %d %b %Y %H:%M:%S %Z",  # RFC 2822 with timezone name (GMT, UTC, etc.)
            "%Y-%m-%dT%H:%M:%S%z",  # ISO format
            "%Y-%m-%d %H:%M:%S",  # Simple format
        ]

        for fmt in formats:
            try:
                parsed_date = datetime.strptime(date_string, fmt)
                return parsed_date.strftime("%Y-%m-%dT%H:%M:%S%z")
            except ValueError:
                continue

        # If none of the common formats work, use dateutil parser as fallback
        parsed_date = date_parser.parse(date_string)
        return parsed_date.strftime("%Y-%m-%dT%H:%M:%S%z")

    except Exception as e:
        logger.warning(
            f"Could not parse date '{date_string}': {e}. Using current time."
        )
        return datetime.now().strftime("%Y-%m-%dT%H:%M:%S%z")


def scrape_huggingface_trending_papers() -> List[SourceSchema]:
    """
    Scrapes trending papers from Hugging Face, validates them against the
    SourceSchema, and returns a list of valid SourceSchema objects.

    This function is designed to be robust against minor website structure
    changes by searching for the data payload instead of relying on
    fixed element positions.

    Returns:
        List[SourceSchema]: A list of Pydantic objects, each representing a
                            valid and parsed paper.
    """
    url = "https://huggingface.co/papers/trending"
    headers = {"User-Agent": USER_AGENT}

    try:
        logger.info(f"Attempting to fetch data from: {url}")
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        logger.info("Successfully fetched the webpage. Parsing HTML for JSON data...")
        soup = BeautifulSoup(response.text, "html.parser")

        # More robustly find the data by searching for the 'dailyPapers' key
        # in the 'data-props' of relevant divs, instead of using a fixed index.
        data_divs = soup.find_all("div", class_="SVELTE_HYDRATER contents")
        papers_json_list = []
        for div in data_divs:
            if "data-props" not in div.attrs:
                continue

            try:
                data = json.loads(div["data-props"])
                if "dailyPapers" in data and data["dailyPapers"]:
                    papers_json_list = data["dailyPapers"]
                    logger.info("Successfully found and parsed paper data from JSON.")
                    break
            except json.JSONDecodeError:
                # This div's data-props was not valid JSON, so we skip it.
                continue

        if not papers_json_list:
            logger.warning(
                "Could not find 'dailyPapers' data. The website structure may have changed."
            )
            return []

        validated_papers = []
        for paper_entry in papers_json_list:
            paper_info = paper_entry.get("paper", {})

            # Pre-validate that essential data exists before trying to create a schema object
            paper_id = paper_info.get("id")
            title = paper_info.get("title")
            published_at = paper_info.get("publishedAt")

            if not all([paper_id, title, published_at]):
                logger.warning(
                    f"Skipping paper due to missing essential data (id, title, or date): {title or 'N/A'}"
                )
                continue

            # Prepare data for schema validation, providing sensible defaults
            paper_data_dict = {
                "title": title,
                "authors": [
                    author.get("name", "Unknown Author")
                    for author in paper_info.get("authors", [])
                ],
                "link": f"https://huggingface.co/papers/{paper_id}",
                "source_link": f"https://huggingface.co/papers/{paper_id}",
                "summary": paper_info.get(
                    "ai_summary"
                ),  # Defaults to None if not present
                "keywords": paper_info.get(
                    "ai_keywords"
                ),  # Defaults to None if not present
                "tags": ["research"],
                "date": published_at,
            }

            try:
                validated_paper = SourceSchema(**paper_data_dict)
                validated_papers.append(validated_paper)
            except ValidationError as e:
                logger.warning(f"Skipping paper '{title}' due to validation error: {e}")

    except requests.exceptions.RequestException as err:
        logger.error(f"HTTP Request Error: {err}")
    except Exception as err:
        logger.error(
            f"An unexpected error occurred during Hugging Face scrape: {err}",
            exc_info=True,
        )

    logger.info(
        f"Successfully scraped and validated {len(validated_papers)} papers from Hugging Face."
    )
    return validated_papers


def scrape_rss_sources() -> List[SourceSchema]:
    """
    Scrapes stories from multiple RSS sources including Hacker News and Substack,
    validates them against the SourceSchema, and returns a list of valid SourceSchema objects.

    Returns:
        List[SourceSchema]: A list of Pydantic objects, each representing a
                            valid and parsed story from various RSS sources.
    """
    urls = [
        "https://news.ycombinator.com/rss",
        "https://api.substack.com/feed/podcast/10845.rss",
    ]
    validated_stories = []

    for url in urls:
        logger.info(f"Attempting to fetch data from: {url}")

        try:
            # feedparser handles the request and parsing
            feed = feedparser.parse(url)

            # Check for parsing errors
            if feed.bozo:
                logger.warning(
                    f"Malformed feed from {url}. Reason: {feed.bozo_exception}"
                )

            logger.info(
                f"Successfully fetched and parsed feed. Found {len(feed.entries)} entries."
            )

            # Limit to top RSS_FEED_LIMIT entries for each feed
            entries_to_process = feed.entries[:RSS_FEED_LIMIT]
            logger.info(f"Processing top {len(entries_to_process)} entries from {url}")

            for entry in entries_to_process:
                try:
                    # For Hacker News, use comments link as primary link if available
                    comments_link = getattr(entry, "comments", None)
                    primary_link = comments_link if comments_link else entry.link

                    # Heuristic to determine if the story is a research paper
                    title_lower = entry.title.lower()
                    link_lower = entry.link.lower()
                    is_research = (
                        "arxiv.org" in link_lower
                        or "[pdf]" in title_lower
                        or "paper" in title_lower
                    )

                    story_data = {
                        "title": entry.title,
                        "authors": (
                            [entry.author]
                            if hasattr(entry, "author") and entry.author
                            else ["Unknown Author"]
                        ),
                        "link": primary_link,
                        "source_link": entry.link,
                        "summary": None,
                        "keywords": None,
                        "tags": ["research"] if is_research else ["industry"],
                        "date": parse_rss_date(entry.published),
                    }

                    validated_story = SourceSchema(**story_data)
                    validated_stories.append(validated_story)

                except ValidationError as e:
                    logger.warning(
                        f"Skipping story '{entry.get('title', 'N/A')}' due to validation error: {e}"
                    )

        except Exception as err:
            logger.error(
                f"An unexpected error occurred while scraping {url}: {err}",
                exc_info=True,
            )

    logger.info(
        f"Successfully scraped and validated {len(validated_stories)} stories from {len(urls)} RSS feeds."
    )
    return validated_stories
