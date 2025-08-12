from typing import List

from .schema import SourceSchema
from .logger import logger
from .database import db_manager
from .utils import generate_summary_from_link


def _pregenerate_embeddings_for_source(source: SourceSchema) -> None:
    """Pre-generate embeddings for a source's searchable text."""
    try:
        # Import here to avoid circular imports
        from .search import _get_embedding
        
        # Generate embeddings for the text that will be searched
        search_text = f"{source.title} {source.summary or ''}"
        if search_text.strip():
            embedding = _get_embedding(search_text.strip())
            if len(embedding) > 0:
                logger.info(f"Pre-generated embedding for: {source.title}")
            else:
                logger.warning(f"Failed to generate embedding for: {source.title}")
    except Exception as e:
        logger.error(f"Error pre-generating embedding for {source.title}: {e}")


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


def enrich_sources_with_summaries_and_embeddings(sources: List[SourceSchema]) -> List[SourceSchema]:
    """
    Generates summaries and pre-generates embeddings for sources.
    This should be used in cron jobs to pre-compute everything needed for search.

    Args:
        sources: A list of SourceSchema objects.

    Returns:
        The list of sources, with missing summaries filled in and embeddings pre-generated.
    """
    logger.info("--- Enriching sources with summaries and pre-generating embeddings ---")
    
    # First, generate summaries (existing logic)
    enriched_sources = enrich_sources_with_summaries(sources)
    
    # Then, pre-generate embeddings for all sources
    for source in enriched_sources:
        _pregenerate_embeddings_for_source(source)
    
    logger.info(f"✅ Completed enrichment for {len(enriched_sources)} sources")
    return enriched_sources


