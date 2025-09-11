"""
Core processing pipeline for Multimodal Scout.

This module orchestrates the entire content processing workflow, including:
1.  Scraping from multiple sources.
2.  Enriching content with AI-generated summaries (with caching).
3.  Filtering and balancing results based on keywords and semantic similarity.

The main entry point is `process_content_pipeline`, a generator function that
yields real-time progress updates and the final processed results, making it
suitable for streaming APIs.
"""

from typing import List, Dict, Any, AsyncGenerator
from datetime import datetime, timedelta
import random
import asyncio

from .scraper import scrape_all_sources_concurrent
from .logger import logger
from .schema import SourceSchema
from .utils import get_hn_comment_insights_with_summaries
from .database import db_manager, Source
from .search import keyword_search, semantic_search_with_scores
from .constants import RESEARCH_THRESHOLD, INDUSTRY_THRESHOLD
from .merger import (
    enrich_sources_with_summaries_and_embeddings,
    enrich_hackernews_comments,
)


async def _apply_balanced_filtering(
    sources: List[SourceSchema],
    keywords: List[str],
    max_results: int = 10,
    research_ratio: float = 0.5,
    discovery_mode: bool = False,
) -> tuple[List[SourceSchema], Dict[str, List[str]]]:
    """
    Apply balanced filtering with relevance scoring and proper sorting.
    When discovery_mode is True, ignores keywords and randomly samples from all sources.
    Returns filtered sources and a map of matched keywords for each source.
    """
    # Override keywords in discovery mode - use empty keywords for random sampling
    if discovery_mode:
        keywords = []
        logger.info(
            f"Applying discovery mode filtering to {len(sources)} sources with random sampling (no keyword filtering)"
        )
    else:
        logger.info(f"Applying balanced filtering to {len(sources)} sources...")

    # Pass 1: Keyword Search - skip if in discovery mode (empty keywords)
    matched_keywords_map = {}  # Map source links to their matched keywords
    if keywords:
        keyword_matches = keyword_search(sources, keywords)
        logger.info(f"Found {len(keyword_matches)} sources via keyword search.")
        # Create list with scores for keyword matches and store matched keywords
        sources_with_scores = []
        matched_links = set()
        for source, matched_kws in keyword_matches:
            sources_with_scores.append((source, 1.0))
            matched_links.add(source.link)
            matched_keywords_map[str(source.link)] = matched_kws
    else:
        # Discovery mode: no keyword filtering, use all sources
        logger.info(
            "Discovery mode: skipping keyword search, using all sources for random sampling"
        )
        sources_with_scores = [
            (source, random.random()) for source in sources if source.summary
        ]
        matched_links = set()

    # Pass 2: Semantic Search - skip if in discovery mode, otherwise use remaining sources
    semantic_candidates = [
        source
        for source in sources
        if source.link not in matched_links and source.summary
    ]

    if semantic_candidates and not discovery_mode:
        logger.info(
            f"Running semantic search on {len(semantic_candidates)} remaining sources..."
        )
        # Separate candidates by content type for different thresholds
        research_candidates = []
        industry_candidates = []
        for source in semantic_candidates:
            source_tag = "General"
            if hasattr(source, "tags") and source.tags:
                source_tag = (
                    source.tags[0].capitalize() if source.tags[0] else "General"
                )
            if source_tag.lower() == "research":
                research_candidates.append(source)
            else:
                industry_candidates.append(source)

        # Choose thresholds based on discovery mode
        # In discovery mode, we skip semantic search entirely, so thresholds are irrelevant
        research_threshold = 0.0 if discovery_mode else RESEARCH_THRESHOLD
        industry_threshold = 0.0 if discovery_mode else INDUSTRY_THRESHOLD

        # Run semantic searches in parallel for better performance
        search_tasks = []

        if research_candidates:
            logger.info(
                f"Running semantic search on {len(research_candidates)} research sources with threshold {research_threshold}"
            )
            search_tasks.append(
                semantic_search_with_scores(
                    research_candidates, keywords, threshold=research_threshold
                )
            )

        if industry_candidates:
            logger.info(
                f"Running semantic search on {len(industry_candidates)} industry sources with threshold {industry_threshold}"
            )
            search_tasks.append(
                semantic_search_with_scores(
                    industry_candidates, keywords, threshold=industry_threshold
                )
            )

        # Execute searches in parallel
        if search_tasks:
            results = await asyncio.gather(*search_tasks)

            # Process results
            for search_results in results:
                for source, score, matched_kws in search_results:
                    sources_with_scores.append((source, score))
                    matched_keywords_map[str(source.link)] = matched_kws

    # Sort by relevance score (descending), then by date (most recent first)
    sorted_sources = sorted(
        sources_with_scores, key=lambda x: (x[1], x[0].date), reverse=True
    )

    # Apply research/industry balancing
    research_count = int(max_results * research_ratio)
    industry_count = max_results - research_count

    logger.info(
        f"Balancing results: {research_count} research, {industry_count} industry"
    )

    # Separate by source type
    research_sources = []
    industry_sources = []

    for source, score in sorted_sources:
        source_tag = "General"
        if hasattr(source, "tags") and source.tags:
            source_tag = source.tags[0].capitalize() if source.tags[0] else "General"

        if source_tag.lower() == "research":
            research_sources.append((source, score))
        else:
            industry_sources.append((source, score))

    # Take balanced amounts from each category
    selected_research = research_sources[:research_count]
    selected_industry = industry_sources[:industry_count]

    # If we don't have enough of one type, fill with the other (only if both ratios > 0)
    total_selected = len(selected_research) + len(selected_industry)
    if total_selected < max_results:
        remaining_slots = max_results - total_selected
        if len(selected_research) < research_count and industry_count > 0:
            # Need more research, take from industry (only if industry is allowed)
            additional_industry = industry_sources[
                len(selected_industry) : len(selected_industry) + remaining_slots
            ]
            selected_industry.extend(additional_industry)
        elif len(selected_industry) < industry_count and research_count > 0:
            # Need more industry, take from research (only if research is allowed)
            additional_research = research_sources[
                len(selected_research) : len(selected_research) + remaining_slots
            ]
            selected_research.extend(additional_research)

    # Combine and handle sorting based on mode
    balanced_sources = selected_research + selected_industry

    balanced_sources.sort(key=lambda x: (x[1], x[0].date), reverse=True)
    limited_results = [source for source, score in balanced_sources]

    logger.info(
        f"Balanced filtering complete: {len([s for s in limited_results if hasattr(s, 'tags') and s.tags and s.tags[0].lower() == 'research'])} research, {len([s for s in limited_results if not hasattr(s, 'tags') or not s.tags or s.tags[0].lower() != 'research'])} industry/other"
    )
    return limited_results, matched_keywords_map


async def process_content_pipeline(
    topics: List[str],
    max_results: int,
    research_ratio: float,
    selected_days: int = 7,
    session_id: str = None,
    discovery_mode: bool = False,
    user_id: str = None,
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    The main processing pipeline.
    1. Always scrape fresh content first
    2. Save new content to database
    3. Query database for sources within date range
    Yields progress updates and finally the results.
    """
    # Step 1: Always scrape fresh content to get latest trending items
    yield {
        "type": "status",
        "message": "Scraping fresh content from Hugging Face and Hacker News...",
    }

    fresh_sources = []
    source_names = []

    total_weight = 100
    scraping_weight = 10
    summary_weight = 70
    filtering_weight = 20

    current_progress = scraping_weight
    yield {
        "type": "start",
        "message": "Starting unified processing pipeline...",
        "total": 100,
        "processed": int((current_progress / total_weight) * 100),
    }

    try:
        # Use concurrent scraping for better performance
        hf_papers, rss_items = await scrape_all_sources_concurrent()

        if hf_papers:
            fresh_sources.extend(hf_papers)
            source_names.append("Hugging Face")

        if rss_items:
            fresh_sources.extend(rss_items)
            source_names.append("RSS Sources")

        yield {
            "type": "status",
            "message": f"Concurrent scraping complete: {len(hf_papers)} HF papers, {len(rss_items)} RSS items",
        }

    except Exception as e:
        logger.error(f"Failed to fetch sources concurrently: {e}")
        yield {
            "type": "error",
            "message": f"Failed to fetch sources concurrently: {str(e)}",
        }

    # Step 2: Save fresh content to database first (without summaries)
    # This tells us which sources are truly new and need summary generation
    try:
        save_result = db_manager.save_sources(fresh_sources)
        new_sources = save_result["new_sources"]
        updated_sources = save_result["updated_sources"]
        skipped_sources = save_result["skipped_sources"]

        total_operated = len(new_sources) + len(updated_sources)
        total_input = save_result["total_processed"] + skipped_sources
        logger.info(
            f"Processed {total_input} sources: {len(new_sources)} new, {len(updated_sources)} updated, {skipped_sources} skipped (recent cache), {save_result['total_processed'] - total_operated} unchanged"
        )

        # Step 2b: Generate summaries for sources that don't have them (both new and updated)
        all_processed_sources = new_sources + updated_sources
        if all_processed_sources:
            # Check which sources actually need summaries
            sources_needing_summaries = [
                source
                for source in fresh_sources
                if source.link in all_processed_sources
            ]

            if sources_needing_summaries:
                logger.info(
                    f"Generating summaries and embeddings for {len(sources_needing_summaries)} new sources..."
                )

                # Show initial progress
                initial_progress = current_progress + (summary_weight * 0.1)
                yield {
                    "type": "progress",
                    "message": f"Starting GenAI processing...",
                    "processed": int((initial_progress / total_weight) * 100),
                    "total": 100,
                }

                # Show mid-progress for summaries
                summary_progress = current_progress + (summary_weight * 0.5)
                yield {
                    "type": "progress",
                    "message": "Generating summaries...",
                    "processed": int((summary_progress / total_weight) * 100),
                    "total": 100,
                }

                # Enrich new sources with summaries and embeddings
                enriched_new_sources = enrich_sources_with_summaries_and_embeddings(
                    sources_needing_summaries
                )

                # Show final progress for this step
                final_progress = current_progress + (summary_weight * 0.9)
                yield {
                    "type": "progress",
                    "message": "GenAI processing complete...",
                    "processed": int((final_progress / total_weight) * 100),
                    "total": 100,
                }

                # Update the database with the new summaries using batch method
                url_summary_pairs = {
                    str(source.link): source.summary
                    for source in enriched_new_sources
                    if source.summary
                }
                if url_summary_pairs:
                    update_results = db_manager.add_summaries(url_summary_pairs)
                    successful_updates = sum(
                        1 for success in update_results.values() if success
                    )
                    logger.info(
                        f"Updated {successful_updates} sources with summaries via batch operation"
                    )
                    yield {
                        "type": "status",
                        "message": f"Updated with GenAI summaries...",
                    }
            else:
                logger.info("All new sources already have summaries")
        else:
            logger.info("No new sources found - all were existing or skipped")

        # Always run comment insights enrichment on HN sources (both new and existing)
        # since HN comments can grow over time
        if fresh_sources:
            logger.info("Running comment insights enrichment on all HN sources...")
            enrich_hackernews_comments(fresh_sources)

    except Exception as e:
        logger.error(f"Failed to save sources to database: {e}")
        yield {
            "type": "warning",
            "message": f"Database save failed, proceeding with fresh content: {str(e)}",
        }

    current_progress += summary_weight
    yield {
        "type": "progress",
        "message": "Summary generation complete...",
        "processed": int((current_progress / total_weight) * 100),
        "total": 100,
    }

    # Step 3: Query database for sources within the specified date range
    cutoff_date = datetime.now() - timedelta(days=selected_days)
    yield {
        "type": "status",
        "message": f"Fetching sources from database added in last {selected_days} days...",
    }

    with db_manager.get_session() as session:
        db_sources = (
            session.query(Source)
            .filter(Source.created_at >= cutoff_date)
            .order_by(Source.created_at.desc())
            .all()
        )

    if db_sources:
        logger.info(
            f"Found {len(db_sources)} sources in database from last {selected_days} days"
        )
        yield {
            "type": "status",
            "message": f"Found {len(db_sources)} sources from last {selected_days} days",
        }

        # Convert database records back to SourceSchema objects
        all_sources = []
        db_source_names = set()

        for db_source in db_sources:
            try:
                # Determine source name from tags
                source_tag = "General"
                if db_source.tags and len(db_source.tags) > 0:
                    source_tag = db_source.tags[0].capitalize()
                    if source_tag.lower() == "research":
                        db_source_names.add("Research Papers")
                    elif source_tag.lower() == "industry":
                        db_source_names.add("Industry News")

                # Create SourceSchema object from database record
                source_schema = SourceSchema(
                    title=db_source.title,
                    authors=db_source.authors or [],
                    link=db_source.link,
                    source_link=db_source.source_link,
                    summary=db_source.summary,
                    keywords=db_source.keywords,
                    tags=db_source.tags or [],
                    date=db_source.date,
                )
                all_sources.append(source_schema)

            except Exception as e:
                logger.warning(f"Failed to convert database record to schema: {e}")
                continue

        # Use database source names for final output
        source_names = list(db_source_names)
        logger.info(f"Converted {len(all_sources)} database records to source schemas")

    else:
        # Fallback to fresh content if no database records in date range
        logger.warning(
            f"No database records found for last {selected_days} days, using fresh scraped content"
        )
        yield {
            "type": "warning",
            "message": f"No database records for {selected_days} days, using fresh content",
        }
        all_sources = fresh_sources

    if all_sources:
        # Get all edited summaries once at the beginning for efficiency
        edited_summaries_map = {}
        if user_id:
            bookmarks = db_manager.get_bookmarks(user_id)
            for bookmark in bookmarks:
                edited_summary = getattr(bookmark, "summary_edited", None)
                if edited_summary:
                    edited_summaries_map[bookmark.link] = edited_summary
            logger.info(
                f"Found {len(edited_summaries_map)} edited summaries in bookmarks"
            )
        else:
            logger.info("No user_id provided, skipping bookmark summary lookup")

        # Apply edited summaries to ALL sources first
        for source in all_sources:
            source_link = str(source.link)
            if source_link in edited_summaries_map:
                source.summary = edited_summaries_map[source_link]
                logger.info(f"Applied edited summary for: {source.title[:50]}")

    filtered_sources = []
    if topics and all_sources:
        yield {
            "type": "status",
            "message": f"Applying smart balanced filtering for {len(all_sources)} items...",
        }

        progress_50 = current_progress + (filtering_weight * 0.5)
        yield {
            "type": "progress",
            "message": "Applying semantic search & balancing...",
            "processed": int((progress_50 / total_weight) * 100),
            "total": 100,
        }

        filtered_sources, source_keywords_map = await _apply_balanced_filtering(
            all_sources, topics, max_results, research_ratio, discovery_mode
        )

        complete_progress = current_progress + filtering_weight
        yield {
            "type": "progress",
            "message": f"Smart filtering complete! Found {len(filtered_sources)} balanced results.",
            "processed": int((complete_progress / total_weight) * 100),
            "total": 100,
        }

    else:
        filtered_sources = all_sources[:max_results]
        source_keywords_map = {}  # No keywords matched if no filtering
        complete_progress = current_progress + filtering_weight
        yield {
            "type": "progress",
            "message": f"No topic filtering requested - using first {max_results} items",
            "processed": int((complete_progress / total_weight) * 100),
            "total": 100,
        }

    # Determine which cards are new for this session
    new_links = []
    if session_id:
        all_links = [str(source.link) for source in filtered_sources]
        new_links = db_manager.get_new_cards(session_id, all_links)

        # Mark all cards as seen now that they're being shown
        db_manager.mark_cards_seen(session_id, all_links)

    # Prepare batch processing for HN comment insights
    all_links = [str(source.link) for source in filtered_sources]
    original_summaries = {
        str(source.link): source.summary or "No summary available"
        for source in filtered_sources
    }

    # Batch process all HN comment insights at once
    insights_results = await get_hn_comment_insights_with_summaries(
        all_links, original_summaries, user_id
    )

    # Build items with new status
    all_items = []
    for source in filtered_sources:
        source_tag = "General"
        if hasattr(source, "tags") and source.tags:
            source_tag = source.tags[0].capitalize() if source.tags[0] else "General"

        link_str = str(source.link)
        is_new = link_str in new_links if session_id else False

        matched_keywords = source_keywords_map.get(link_str, [])

        # Get processed summary and insights from batch results
        display_summary, comment_insights, comment_count = insights_results[link_str]

        all_items.append(
            {
                "title": source.title,
                "link": link_str,
                "summary": display_summary,
                "source": source_tag,
                "created_at": (
                    source.date.isoformat()
                    if hasattr(source, "date") and source.date
                    else datetime.now().isoformat()
                ),
                "is_new": is_new,
                "matched_keywords": matched_keywords,
                "comment_insights": comment_insights,
                "comment_count": comment_count,
            }
        )

    # Sort items: new cards first, then rest in original order
    new_items = [item for item in all_items if item["is_new"]]
    existing_items = [item for item in all_items if not item["is_new"]]
    final_items = new_items + existing_items

    yield {
        "type": "complete",
        "message": f"Processing complete! Found {len(final_items)} relevant items.",
    }

    yield {
        "type": "result",
        "data": {
            "items": final_items,
            "total_count": len(final_items),
            "sources": list(set(source_names)),
        },
    }
