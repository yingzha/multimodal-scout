from typing import List

from .schema import SourceSchema
from .logger import logger
from .database import db_manager
from .utils import generate_summary_from_link


def enrich_sources_with_summaries(sources: List[SourceSchema]) -> List[SourceSchema]:
    """
    Generates summaries for sources using batch operations to avoid N+1 query problems.

    Args:
        sources: A list of SourceSchema objects.

    Returns:
        The list of sources, with missing summaries filled in where possible.
    """
    logger.info("--- Enriching sources with summaries (batch optimized) ---")

    if not sources:
        return sources

    logger.info(f"Generating summaries for {len(sources)} sources...")
    newly_generated = []
    
    for source in sources:
        new_summary = generate_summary_from_link(source.source_link)
        if new_summary is None and str(source.source_link) != str(source.link):
            logger.warning(f"2nd attempt to generate summary from link for: {source.link}")
            new_summary = generate_summary_from_link(source.link)
        
        if new_summary:
            source.summary = new_summary
            newly_generated.append(source)
            logger.info(f"Generated new summary for: {source.title}")
        else:
            logger.warning(f"Failed to generate summary for: {source.title} ({source.link})")
    
    if newly_generated:
        # Save all sources with new summaries in one operation
        db_manager.save_sources(newly_generated)
        logger.info(f"Batch saved {len(newly_generated)} sources with new summaries")

    logger.info(f"✅ Summary enrichment complete: {len(sources)} generated")
    return sources


def enrich_sources_with_summaries_and_embeddings(sources: List[SourceSchema]) -> List[SourceSchema]:
    """
    Generates summaries and embeddings for sources.
    This should be used in cron jobs to pre-compute everything needed for search.

    Args:
        sources: A list of SourceSchema objects.

    Returns:
        The list of sources, with missing summaries filled in and embeddings pre-generated.
    """
    logger.info("--- Enriching sources with summaries and embeddings ---")
    
    # First, generate summaries
    enriched_sources = enrich_sources_with_summaries(sources)
    
    # Import here to avoid circular imports
    from .search import _get_embedding
    # Then Generate embeddings for the text that will be searched
    for source in enriched_sources:
        try:
            if source.summary:  # Only generate embeddings for sources with summaries
                embedding = _get_embedding(source.summary)
                if len(embedding) > 0:
                    logger.info(f"Generated embedding for: {source.title}")
                else:
                    logger.warning(f"Failed to generate embedding for: {source.title}")
            else:
                logger.warning(f"Skipping embedding generation for {source.title}: No summary available")
        except Exception as e:
            logger.error(f"Error generating embedding for {source.title}: {e}")  
   
    
    logger.info(f"✅ Completed enrichment for {len(enriched_sources)} sources")
    return enriched_sources


