from typing import List

from .cache import add_summary_to_cache, get_summary_from_cache, load_cache, save_cache
from .constants import INTERESTED_KEYWORDS
from .logger import logger
from .utils import generate_summary_from_link
from .scraper import scrape_hacker_news, scrape_huggingface_trending_papers
from .schema import SourceSchema
from .search import keyword_search, semantic_search

SEMANTIC_SIMILARITY_THRESHOLD = 0.6 # Adjust able threshold (0.0 to 1.0)


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
            cached_summary = get_summary_from_cache(str(source.link))
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
                    add_summary_to_cache(str(source.link), new_summary)
                    logger.info(f"Added new summary for: {source.title}")

    return sources


def get_all_filtered_sources() -> List[SourceSchema]:
    """
    Scrapes all sources and filters them based on the interested keywords.

    Returns:
        A combined and filtered list of sources from all scrapers.
    """
    logger.info("--- Starting all scrapers ---")
    hf_papers = scrape_huggingface_trending_papers()
    hn_stories = scrape_hacker_news()
    all_sources = hf_papers + hn_stories
    logger.info(f"--- Found a total of {len(all_sources)} items ---")

    # Enrich sources with AI-generated summaries if they are missing
    all_sources = enrich_sources_with_summaries(all_sources)

    logger.info(f"--- Filtering against {len(INTERESTED_KEYWORDS)} keywords ---")
    filtered_sources = filter_sources(all_sources, INTERESTED_KEYWORDS)
    logger.info(f"--- Found {len(filtered_sources)} matching items ---")

    logger.info("--- Sorting sources by date in descending order ---")
    sorted_sources = sorted(filtered_sources, key=lambda s: s.date, reverse=True)

    return sorted_sources


if __name__ == "__main__":
    get_all_filtered_sources()
