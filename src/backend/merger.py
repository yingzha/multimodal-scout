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
    Generates summaries for sources that are missing them, using batch operations
    to avoid N+1 query problems.

    Args:
        sources: A list of SourceSchema objects.

    Returns:
        The list of sources, with missing summaries filled in where possible.
    """
    logger.info("--- Enriching sources with missing summaries (batch optimized) ---")

    if not sources:
        return sources

    # Step 1: Find sources without summaries
    sources_needing_summaries = [source for source in sources if not source.summary]
    
    if not sources_needing_summaries:
        logger.info("All sources already have summaries")
        return sources
    
    # Step 2: Batch lookup existing summaries from database
    urls_needing_summaries = [str(source.link) for source in sources_needing_summaries]
    cached_summaries = db_manager.get_summaries_batch(urls_needing_summaries)
    
    logger.info(f"Found {len(cached_summaries)} cached summaries out of {len(sources_needing_summaries)} sources needing summaries")
    
    # Step 3: Apply cached summaries
    sources_still_needing_generation = []
    for source in sources_needing_summaries:
        source_url = str(source.link)
        if source_url in cached_summaries:
            source.summary = cached_summaries[source_url]
            logger.info(f"Applied cached summary for: {source.title}")
        else:
            sources_still_needing_generation.append(source)
    
    # Step 4: Generate summaries for remaining sources
    if sources_still_needing_generation:
        logger.info(f"Generating summaries for {len(sources_still_needing_generation)} sources...")
        newly_generated = []
        
        for source in sources_still_needing_generation:
            new_summary = generate_summary_from_link(source.source_link)
            if new_summary is None:
                logger.warning(f"2nd attempt to generate summary from link for: {source.link}")
                new_summary = generate_summary_from_link(source.link)
            
            if new_summary:
                source.summary = new_summary
                newly_generated.append(source)
                logger.info(f"Generated new summary for: {source.title}")
        
        # Step 5: Batch save newly generated summaries
        if newly_generated:
            # Save all sources with new summaries in one operation
            db_manager.save_sources(newly_generated)
            logger.info(f"Batch saved {len(newly_generated)} sources with new summaries")

    logger.info(f"✅ Summary enrichment complete: {len(cached_summaries)} from cache, {len(sources_still_needing_generation)} generated")
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


