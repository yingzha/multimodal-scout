import time
from concurrent import futures
from typing import List

from .schema import SourceSchema
from .logger import logger
from .utils import (
    generate_summary_from_link,
    fetch_hackernews_comments,
    generate_comment_insights,
    is_comment_insight_recently_processed,
    mark_comment_insight_as_processed,
)

from .constants import MIN_COMMENTS_FOR_INSIGHTS
from .database import db_manager, Source
from .search import _get_embedding


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

    # Note: Sources are saved by the caller using add_summaries for better efficiency
    logger.info(
        f"Generated summaries for {len(newly_generated)} out of {len(sources_needing_summaries)} sources that needed them"
    )

    logger.info(
        f"✅ Summary enrichment complete: {len(sources)} total sources ({len(sources_with_summaries)} already had summaries, {len(newly_generated)} newly generated)"
    )
    return sources


def enrich_hackernews_comments(sources: List[SourceSchema]) -> None:
    """
    Enrich HN sources with comment insights. Only updates if there are enough new comments.
    Uses simple caching like summaries to avoid reprocessing.
    Modifies the database directly, doesn't change the source objects.
    Optimized with parallel processing and batching.
    """
    hn_sources = [s for s in sources if "news.ycombinator.com" in str(s.link).lower()]

    if not hn_sources:
        return

    logger.info(f"Processing {len(hn_sources)} HN sources for comment insights")

    # Filter out recently processed sources using 10-minute TTL cache
    sources_to_process = []
    cache_hits = 0

    for source in hn_sources:
        link_str = str(source.link)
        if not is_comment_insight_recently_processed(link_str):
            sources_to_process.append(source)
        else:
            cache_hits += 1

    if cache_hits > 0:
        logger.info(
            f"Cache optimization: Skipped {cache_hits} recently processed comment insights"
        )

    if not sources_to_process:
        logger.info("All HN sources were recently processed, skipping")
        return

    hn_links = [str(s.link) for s in sources_to_process]

    # Get existing insights from database
    try:
        existing_insights_map = db_manager.get_comment_insights(hn_links)
    except Exception as e:
        logger.warning(f"Failed to fetch existing insights: {e}")
        existing_insights_map = {}

    def process_hn_source(source):
        """Process a single HN source for comment insights"""
        try:
            link_str = str(source.link)
            existing_insights = existing_insights_map.get(link_str)

            # Fetch current comments
            comment_data = fetch_hackernews_comments(link_str)
            current_count = comment_data.get("comment_count", 0)

            # Skip if not enough comments
            if current_count < MIN_COMMENTS_FOR_INSIGHTS:
                logger.info(f"⏭️  Skipping {source.title[:50]}...: {current_count} total comments < {MIN_COMMENTS_FOR_INSIGHTS} minimum")
                return None

            # Skip if not enough new comments since last update
            if existing_insights:
                existing_count = (
                    int(existing_insights.comment_count)
                    if existing_insights.comment_count
                    else 0
                )
                new_comments = current_count - existing_count
                if new_comments < MIN_COMMENTS_FOR_INSIGHTS:
                    logger.info(f"⏭️  Skipping {source.title[:50]}...: Only {new_comments} new comments since last update (existing: {existing_count}, current: {current_count})")
                    return None
                else:
                    logger.info(f"🔄 Processing {source.title[:50]}...: {new_comments} new comments since last update (existing: {existing_count}, current: {current_count})")
            else:
                logger.info(f"🆕 Processing new HN item {source.title[:50]}...: {current_count} total comments")

            # Generate insights
            comments = comment_data.get("comments", [])
            if not comments:
                logger.warning(f"❌ No comments retrieved for {source.title[:50]}... despite API showing {current_count} total")
                return None

            logger.info(f"📝 Generating insights for {source.title[:50]}... with {len(comments)} fetched comments")
            insights = generate_comment_insights(comments, source.title)
            if not insights:
                logger.warning(f"❌ Failed to generate insights for {source.title[:50]}... despite having {len(comments)} comments")
                return None
            
            logger.info(f"✅ Generated insights for {source.title[:50]}... ({len(insights)} chars)")
            return {
                "source": source,
                "link_str": link_str,
                "current_count": current_count,
                "insights": insights,
            }

        except Exception as e:
            logger.error(f"Error processing HN comments for {source.title[:50]}: {e}")
            return None

    # Optimization 3: Parallel processing with controlled concurrency
    results_to_save = []
    max_workers = min(
        5, len(sources_to_process)
    )  # Limit concurrent requests to be respectful to HN

    with futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_source = {
            executor.submit(process_hn_source, source): source
            for source in sources_to_process
        }

        for future in futures.as_completed(future_to_source):
            result = future.result()
            if result:
                results_to_save.append(result)

    # Optimization 4: Batch save results to reduce DB transactions
    if results_to_save:
        logger.info(f"Saving {len(results_to_save)} comment insights to database...")

        # Collect all insights data for batch processing
        insights_to_save = []

        with db_manager.get_session() as session:
            for result in results_to_save:
                try:
                    # Find source in DB
                    db_source = (
                        session.query(Source)
                        .filter(Source.link == result["link_str"])
                        .first()
                    )

                    if db_source:
                        insights_to_save.append(
                            {
                                "source_id": str(db_source.id),
                                "link": result["link_str"],
                                "title": result["source"].title,
                                "comment_count": result["current_count"],
                                "insights": result["insights"],
                            }
                        )

                except Exception as e:
                    logger.error(
                        f"Error preparing insights for {result['source'].title[:50]}: {e}"
                    )

        # Batch save all insights
        if insights_to_save:
            try:
                saved_count = db_manager.save_comment_insights(insights_to_save)
                logger.info(f"Updated {saved_count} HN comment insights in batch")
            except Exception as e:
                logger.error(f"Error batch saving comment insights: {e}")

    # Mark all processed sources as cached with 5-minute TTL
    for source in sources_to_process:
        mark_comment_insight_as_processed(str(source.link))

    logger.info(
        f"✅ HN comment insights processing complete: {len(results_to_save)} insights updated"
    )


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

    # Generate embeddings for the text that will be searched
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
