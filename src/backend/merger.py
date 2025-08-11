from typing import List

from .schema import SourceSchema
from .logger import logger
from .database import db_manager
from .utils import generate_summary_from_link



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


