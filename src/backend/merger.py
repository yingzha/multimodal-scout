from typing import List

from .db_cache import add_summary_to_db as add_summary_to_cache, get_summary_from_db as get_summary_from_cache
from .constants import INTERESTED_KEYWORDS
from .logger import logger
from .utils import generate_summary_from_link
from .scraper import scrape_hacker_news, scrape_huggingface_trending_papers
from .schema import SourceSchema
from .search import keyword_search, semantic_search, semantic_search_with_scores

SEMANTIC_SIMILARITY_THRESHOLD = 0.6 # Default threshold (0.0 to 1.0)
RESEARCH_THRESHOLD = 0.65  # Higher threshold for research papers to be more selective
INDUSTRY_THRESHOLD = 0.55  # Lower threshold for industry content to include more variety


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


def filter_sources_advanced(
    sources: List[SourceSchema], 
    keywords: List[str], 
    max_results: int = 10,
    research_ratio: float = 0.5
) -> List[SourceSchema]:
    """
    Advanced filtering with balanced results and proper ordering.
    
    Order priority:
    1. Keyword matches (research first, then industry)
    2. Semantic matches by descending similarity score (research and industry balanced)
    
    Args:
        sources: A list of SourceSchema objects to filter.
        keywords: A list of strings to search for.
        max_results: Maximum number of results to return.
        research_ratio: Ratio of research vs industry papers (0.5 = 50/50).
    
    Returns:
        A balanced and ordered list of SourceSchema objects.
    """
    # --- Pass 1: Keyword Search ---
    logger.info("Running keyword search...")
    keyword_matches = keyword_search(sources, keywords)
    logger.info(f"Found {len(keyword_matches)} sources via keyword search.")
    
    # Separate keyword matches by tag
    keyword_research = []
    keyword_industry = []
    
    for source in keyword_matches:
        if hasattr(source, 'tags') and source.tags and 'research' in source.tags:
            keyword_research.append(source)
        else:
            keyword_industry.append(source)
    
    matched_links = {source.link for source in keyword_matches}
    
    # --- Pass 2: Semantic Search with Different Thresholds ---
    semantic_candidates = [
        source for source in sources
        if source.link not in matched_links
        and source.summary  # Ensure there is a summary to search on
    ]
    
    # Separate candidates by tag for different thresholds
    research_candidates = []
    industry_candidates = []
    
    for source in semantic_candidates:
        if hasattr(source, 'tags') and source.tags and 'research' in source.tags:
            research_candidates.append(source)
        else:
            industry_candidates.append(source)
    
    logger.info(f"Running semantic search on {len(research_candidates)} research and {len(industry_candidates)} industry sources...")
    
    # Semantic search with scores for proper ordering
    research_matches = semantic_search_with_scores(
        research_candidates, keywords, threshold=RESEARCH_THRESHOLD
    )
    industry_matches = semantic_search_with_scores(
        industry_candidates, keywords, threshold=INDUSTRY_THRESHOLD
    )
    
    # Extract sources from tuples for further processing
    semantic_research = [source for source, score in research_matches]
    semantic_industry = [source for source, score in industry_matches]
    
    logger.info(f"Found {len(semantic_research)} research and {len(semantic_industry)} industry semantic matches")
    
    # --- Pass 3: Balanced Selection ---
    target_research = int(max_results * research_ratio)
    target_industry = max_results - target_research
    
    # Priority order: keyword first, then semantic by similarity
    final_research = keyword_research[:target_research]
    remaining_research_slots = target_research - len(final_research)
    if remaining_research_slots > 0:
        final_research.extend(semantic_research[:remaining_research_slots])
    
    final_industry = keyword_industry[:target_industry]
    remaining_industry_slots = target_industry - len(final_industry)
    if remaining_industry_slots > 0:
        final_industry.extend(semantic_industry[:remaining_industry_slots])
    
    # If one category doesn't fill its quota, let the other category use the extra slots
    total_selected = len(final_research) + len(final_industry)
    remaining_slots = max_results - total_selected
    
    if remaining_slots > 0:
        # Add remaining research sources if available
        research_overflow = semantic_research[remaining_research_slots:remaining_research_slots + remaining_slots]
        if len(research_overflow) < remaining_slots:
            # Add remaining industry sources to fill the gap
            industry_overflow = semantic_industry[remaining_industry_slots:remaining_industry_slots + (remaining_slots - len(research_overflow))]
            final_industry.extend(industry_overflow)
        final_research.extend(research_overflow)
    
    # Combine results in priority order
    result = []
    
    # Add keyword matches first (research, then industry)
    result.extend(keyword_research[:len(final_research) if len(keyword_research) > 0 else 0])
    result.extend(keyword_industry[:len(final_industry) if len(keyword_industry) > 0 else 0])
    
    # Add semantic matches (maintaining order by similarity)
    semantic_research_to_add = [s for s in final_research if s not in keyword_research]
    semantic_industry_to_add = [s for s in final_industry if s not in keyword_industry]
    
    # Interleave semantic results to maintain balance while preserving similarity ordering
    max_sem_len = max(len(semantic_research_to_add), len(semantic_industry_to_add))
    for i in range(max_sem_len):
        if i < len(semantic_research_to_add):
            result.append(semantic_research_to_add[i])
        if i < len(semantic_industry_to_add):
            result.append(semantic_industry_to_add[i])
    
    logger.info(f"Final balanced results: {len([r for r in result if hasattr(r, 'tags') and 'research' in r.tags])} research, {len([r for r in result if not (hasattr(r, 'tags') and 'research' in r.tags)])} industry")
    
    return result[:max_results]


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
