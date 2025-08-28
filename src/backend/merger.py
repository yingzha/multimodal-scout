import time
from typing import List

from .schema import SourceSchema
from .logger import logger
from .utils import generate_summary_from_link


def enrich_sources_with_summaries(sources: List[SourceSchema]) -> List[SourceSchema]:
    """
    Generates summaries for sources using batch operations to avoid N+1 query problems.
    Only generates summaries for sources that don't already have them (e.g., from scraping).

    Args:
        sources: A list of SourceSchema objects.

    Returns:
        The list of sources, with missing summaries filled in where possible.
    """
    logger.info("--- Enriching sources with summaries (batch optimized) ---")

    if not sources:
        return sources

    # Filter to only sources that need summary generation
    sources_needing_summaries = [source for source in sources if not source.summary]
    sources_with_summaries = [source for source in sources if source.summary]

    logger.info(
        f"Found {len(sources_with_summaries)} sources with existing summaries, generating for {len(sources_needing_summaries)} remaining sources..."
    )
    newly_generated = []

    for i, source in enumerate(sources_needing_summaries):
        # Add a small delay between API calls to avoid rate limiting (except for first item)
        if i > 0:
            time.sleep(0.5)  # 500ms delay between requests

        new_summary = generate_summary_from_link(source.source_link, source.title)
        if new_summary is None and str(source.source_link) != str(source.link):
            logger.warning(
                f"2nd attempt to generate summary from link for: {source.link}"
            )
            time.sleep(1.0)  # Longer delay before retry
            new_summary = generate_summary_from_link(source.link, source.title)

        if new_summary:
            source.summary = new_summary
            newly_generated.append(source)
            logger.info(f"Generated new summary for: {source.title}")
        else:
            logger.warning(
                f"Failed to generate summary for: {source.title} ({source.link})"
            )

    # Note: Sources are saved by the caller using add_summaries_batch for better efficiency
    logger.info(
        f"Generated summaries for {len(newly_generated)} out of {len(sources_needing_summaries)} sources that needed them"
    )

    logger.info(
        f"✅ Summary enrichment complete: {len(sources)} total sources ({len(sources_with_summaries)} already had summaries, {len(newly_generated)} newly generated)"
    )
    return sources


def enrich_sources_with_summaries_and_embeddings(
    sources: List[SourceSchema],
) -> List[SourceSchema]:
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
                logger.warning(
                    f"Skipping embedding generation for {source.title}: No summary available"
                )
        except Exception as e:
            logger.error(f"Error generating embedding for {source.title}: {e}")

    logger.info(f"✅ Completed enrichment for {len(enriched_sources)} sources")
    return enriched_sources
