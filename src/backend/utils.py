import re
import time
from typing import Optional, Tuple, List, Dict

import requests
from bs4 import BeautifulSoup
from pydantic import HttpUrl

from .constants import (
    GEMINI_MODEL_NAME,
    USER_AGENT,
    MIN_COMMENTS_FOR_INSIGHTS,
    COMMENT_INSIGHTS_ENABLED,
)
from .logger import logger
from .client import genai_client, is_genai_enabled
from .database import db_manager

# Module-level cache for recently processed comment insights with 5-minute TTL
_processed_comment_insights = {}  # link -> timestamp (when processed)
_comment_insights_ttl = 600  # 10 minutes in seconds


def is_comment_insight_recently_processed(link: str) -> bool:
    """Check if comment insights were processed within the last 10 minutes."""
    if link not in _processed_comment_insights:
        return False

    current_time = time.time()
    processed_time = _processed_comment_insights[link]

    # Check if within TTL
    if current_time - processed_time <= _comment_insights_ttl:
        return True
    else:
        # Clean up expired entry
        del _processed_comment_insights[link]
        return False


def mark_comment_insight_as_processed(link: str) -> None:
    """Mark a comment insight as recently processed."""
    _processed_comment_insights[link] = time.time()


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
        prompt = f"""IMPORTANT: You must respond in English only, regardless of the source language.

Please provide a concise, one-paragraph summary of the following article text. If the source text is in another language, translate and summarize it in English. Focus on the key points and main insights.

Article text:
---
{article_text[:4000]}

Provide a clear English summary:"""

        response = genai_client.models.generate_content(
            model=GEMINI_MODEL_NAME, contents=[prompt]
        )
        return response.text.strip()

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


def fetch_hackernews_comments(hn_comment_link: str, max_comments: int = 50) -> dict:
    """
    Fetch comments for a Hacker News item using the existing comment link.
    Returns comment data only if there are 10+ total comments.
    Now recursively fetches nested comments to get more comprehensive insights.
    """
    try:
        # Extract item ID from the existing comment link
        match = re.search(r"item\?id=(\d+)", hn_comment_link)
        if not match:
            logger.warning(f"Could not extract item ID from HN link: {hn_comment_link}")
            return {"comments": [], "comment_count": 0}

        item_id = match.group(1)

        # Get the item details from HN API
        item_url = f"https://hacker-news.firebaseio.com/v0/item/{item_id}.json"
        response = requests.get(
            item_url, timeout=10, headers={"User-Agent": USER_AGENT}
        )
        response.raise_for_status()

        item_data = response.json()
        if not item_data:
            return {"comments": [], "comment_count": 0}

        total_comments = item_data.get("descendants", 0)

        # Only process if there are enough comments
        if total_comments < MIN_COMMENTS_FOR_INSIGHTS:
            logger.info(
                f"HN post has {total_comments} comments, need {MIN_COMMENTS_FOR_INSIGHTS}+ for insights"
            )
            return {"comments": [], "comment_count": total_comments}

        # Recursively fetch comments up to max_comments limit
        def fetch_comment_recursive(comment_id, depth=0, max_depth=4):
            """Recursively fetch a comment and its nested replies"""
            if depth > max_depth:  # Prevent infinite recursion
                return []

            try:
                comment_url = (
                    f"https://hacker-news.firebaseio.com/v0/item/{comment_id}.json"
                )
                comment_response = requests.get(
                    comment_url, timeout=5, headers={"User-Agent": USER_AGENT}
                )
                comment_response.raise_for_status()

                comment_data = comment_response.json()
                if not comment_data:
                    return []

                comments = []

                # Process current comment if it has text and isn't deleted
                if comment_data.get("text") and not comment_data.get("deleted"):
                    # Clean up HTML entities and tags
                    soup = BeautifulSoup(comment_data["text"], "html.parser")
                    clean_text = soup.get_text().strip()

                    if len(clean_text) > 50:  # Only substantial comments
                        comments.append(
                            {
                                "text": clean_text,
                                "author": comment_data.get("by", "Anonymous"),
                                "score": comment_data.get("score", 0),
                            }
                        )

                # Recursively fetch nested comments (replies)
                if comment_data.get("kids") and len(comments) < max_comments:
                    for kid_id in comment_data.get("kids", []):
                        nested_comments = fetch_comment_recursive(
                            kid_id, depth + 1, max_depth
                        )
                        comments.extend(nested_comments)
                        if len(comments) >= max_comments:
                            break

                return comments

            except Exception as e:
                logger.warning(f"Failed to fetch comment {comment_id}: {e}")
                return []

        # Start with top-level comments and recursively fetch nested ones
        all_comments = []
        top_level_ids = item_data.get("kids", [])

        for comment_id in top_level_ids:
            if len(all_comments) >= max_comments:
                break
            nested_comments = fetch_comment_recursive(comment_id)
            all_comments.extend(nested_comments)

        # Limit to max_comments if we got too many
        all_comments = all_comments[:max_comments]

        logger.info(
            f"Fetched {len(all_comments)} comments from HN item {item_id} (total descendants: {total_comments})"
        )
        return {"comments": all_comments, "comment_count": total_comments}

    except Exception as e:
        logger.error(f"Error fetching HN comments from {hn_comment_link}: {e}")
        return {"comments": [], "comment_count": 0}


def generate_comment_insights(comments: list, title: str) -> Optional[str]:
    """Generate key insights from HN comments using Gemini API."""
    if not comments:
        return None

    if not COMMENT_INSIGHTS_ENABLED:
        logger.info("Comment insights disabled to manage API costs")
        return None

    if not is_genai_enabled():
        logger.warning("GenAI not enabled, skipping comment insights generation")
        return None

    try:
        # Prepare comment text for analysis
        comment_texts = []
        short_comments = 0

        for comment in comments:
            if len(comment["text"]) > 50:  # Focus on substantial comments
                comment_texts.append(f"• {comment['text']}")
            else:
                short_comments += 1

        logger.info(
            f"📊 Comment filtering for '{title[:50]}...': {len(comments)} total → {len(comment_texts)} substantial (≥50 chars), {short_comments} filtered out"
        )

        if len(comment_texts) < MIN_COMMENTS_FOR_INSIGHTS:
            logger.warning(
                f"❌ Not enough substantial comments for '{title[:50]}...': {len(comment_texts)} < {MIN_COMMENTS_FOR_INSIGHTS} minimum after filtering"
            )
            return None

        combined_comments = "\n".join(comment_texts)

        prompt = f"""Analyze these Hacker News comments for "{title}" (total: {len(comment_texts)} comments) and extract 3-4 key insights about the community discussion.

Focus on:
- Main themes and technical concerns
- Expert insights and real-world experiences  
- Different perspectives or debates
- Practical takeaways

Format as concise bullet points (max 4 points).

Comments:
{combined_comments}

Key Insights:"""

        def generate_insights():
            response = genai_client.models.generate_content(
                model=GEMINI_MODEL_NAME, contents=[prompt]
            )
            summary = response.text.strip()
            return summary

        logger.info(
            f"🤖 Calling Gemini API for insights on '{title[:50]}...' with {len(comment_texts)} substantial comments"
        )
        insights = _retry_with_backoff(generate_insights)

        if insights and len(insights) > 50:
            logger.info(
                f"✅ Successfully generated {len(insights)} chars of insights for '{title[:50]}...'"
            )
            return insights
        else:
            logger.warning(
                f"❌ Generated insights too short or empty for '{title[:50]}...': {len(insights) if insights else 0} chars (need >50)"
            )
            return None

    except Exception as e:
        logger.error(f"Error generating comment insights: {e}")
        return None


async def get_hn_comment_insights_with_summaries(
    links: List[str], original_summaries: Dict[str, str], user_id: str = None
) -> Dict[str, Tuple[str, Optional[str], Optional[int]]]:
    """
    Get HN comment insights and create combined summaries for multiple links (batch processing).

    Args:
        links: List of links to process
        original_summaries: Dict mapping link -> original summary
        user_id: User ID (insights only shown to registered users)

    Returns:
        Dict mapping link -> (final_summary, comment_insights, comment_count)
    """
    results = {}

    # Filter to only HN links
    hn_links = [link for link in links if "news.ycombinator.com" in link.lower()]

    # If no user_id or no HN links, return original summaries
    if not user_id or not hn_links:
        for link in links:
            original_summary = original_summaries.get(link, "No summary available")
            results[link] = (original_summary, None, None)
        return results

    # Batch get insights for all HN links
    insights_map = db_manager.get_comment_insights(hn_links)

    # Process each link
    for link in links:
        original_summary = original_summaries.get(link, "No summary available")

        if "news.ycombinator.com" not in link.lower():
            results[link] = (original_summary, None, None)
            continue

        insights_data = insights_map.get(link)
        if not insights_data:
            results[link] = (original_summary, None, None)
            continue

        comment_insights = insights_data.insights
        comment_count = insights_data.comment_count

        if not comment_insights:
            results[link] = (original_summary, comment_insights, comment_count)
            continue

        # Clean up insights by removing introductory line
        lines = comment_insights.split("\n")
        if lines and "here are" in lines[0].lower():
            comment_insights = "\n".join(lines[1:]).strip()

        # Create two-section summary
        bullet_points = comment_insights
        final_summary = f"**Content Summary:**\n{original_summary}\n\n**Community Discussion ({comment_count} comments):**\n{bullet_points}"

        results[link] = (final_summary, comment_insights, comment_count)

    return results
