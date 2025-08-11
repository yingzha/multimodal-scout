from typing import List

from .constants import INTERESTED_KEYWORDS, SEMANTIC_SIMILARITY_THRESHOLD
from .schema import SourceSchema
from .logger import logger
from .database import db_manager
from .utils import generate_summary_from_link


def filter_sources(
    sources: List[SourceSchema], keywords: List[str]
) -> List[SourceSchema]:
    """
    Filters sources using a two-pass approach: keyword and semantic search.

    1. A fast, normalized keyword search is run on all sources.
    2. For sources with summaries that did not match via keywords,
       a semantic search is performed to find conceptually similar content.

    Args:
        sources: A list of SourceSchema objects to filter.
        keywords: A list of strings to search for.
    Returns:
        A new list of SourceSchema objects that match the criteria.
    """
    # --- Pass 1: Keyword Search ---
    logger.info("Running keyword search...")
    keyword_matches = keyword_search(sources, keywords)
    logger.info(f"Found {len(keyword_matches)} sources via keyword search.")

    matched_links = {source.link for source in keyword_matches}

    # --- Pass 2: Semantic Search (on remaining sources with summaries) ---
    # Identify candidates for semantic search
    semantic_candidates = [
        source for source in sources
        if source.link not in matched_links
        and source.summary  # Ensure there is a summary to search on
    ]

    logger.info(f"Running semantic search on {len(semantic_candidates)} remaining sources with summaries...")
    semantic_matches = semantic_search(
        semantic_candidates, keywords, threshold=SEMANTIC_SIMILARITY_THRESHOLD
    )

    # Combine results
    return keyword_matches + semantic_matches


def enrich_sources_with_summaries(sources: List[SourceSchema]) -> List[SourceSchema]:
    """
    Generates summaries for sources that are missing them, using a cache to
    avoid re-processing.

    Args:
        sources: A list of SourceSchema objects.

    Returns:
        The list of sources, with missing summaries filled in where possible.
    """
    logger.info("--- Enriching sources with missing summaries ---")

    for source in sources:
        if not source.summary:
            cached_summary = db_manager.get_summary(str(source.link))
            if cached_summary:
                source.summary = cached_summary
                logger.info(f"Found cached summary for: {source.title}")
            else:
                new_summary = generate_summary_from_link(source.source_link)
                if new_summary is None:
                    logger.warning(f"2nd attempt to generate summary from link for: {source.link}")
                    new_summary = generate_summary_from_link(source.link)
                if new_summary:
                    source.summary = new_summary
                    db_manager.add_summary(str(source.link), new_summary)
                    logger.info(f"Added new summary for: {source.title}")

    return sources


