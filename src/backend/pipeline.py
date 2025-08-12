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

import json
from typing import List, Dict, Any, Generator
from datetime import datetime, timedelta

from .scraper import scrape_huggingface_trending_papers, scrape_hacker_news
from .logger import logger
from .schema import SourceSchema
from .database import db_manager
from .utils import generate_summary_from_link
from .search import keyword_search, semantic_search_with_scores
from .constants import SEMANTIC_SIMILARITY_THRESHOLD, RESEARCH_THRESHOLD, INDUSTRY_THRESHOLD


def _apply_balanced_filtering(sources: List[SourceSchema], keywords: List[str], max_results: int = 10, research_ratio: float = 0.5) -> List[SourceSchema]:
    """
    Apply balanced filtering with relevance scoring and proper sorting.
    """
    logger.info(f"Applying balanced filtering to {len(sources)} sources...")
    # Pass 1: Keyword Search - these get highest priority (score = 1.0)
    keyword_matches = keyword_search(sources, keywords)
    logger.info(f"Found {len(keyword_matches)} sources via keyword search.")
    # Create list with scores for keyword matches
    sources_with_scores = [(source, 1.0) for source in keyword_matches]
    matched_links = {source.link for source in keyword_matches}
    # Pass 2: Semantic Search - for remaining sources with summaries, using content-specific thresholds
    semantic_candidates = [
        source for source in sources
        if source.link not in matched_links and source.summary
    ]
    
    if semantic_candidates:
        logger.info(f"Running semantic search on {len(semantic_candidates)} remaining sources...")
        # Separate candidates by content type for different thresholds
        research_candidates = []
        industry_candidates = []
        for source in semantic_candidates:
            source_tag = "General"
            if hasattr(source, 'tags') and source.tags:
                source_tag = source.tags[0].capitalize() if source.tags[0] else "General"
            if source_tag.lower() == "research":
                research_candidates.append(source)
            else:
                industry_candidates.append(source)
        
        # Run semantic search with research threshold (more selective)
        if research_candidates:
            logger.info(f"Running semantic search on {len(research_candidates)} research sources with threshold {RESEARCH_THRESHOLD}")
            research_results = semantic_search_with_scores(
                research_candidates, keywords, threshold=RESEARCH_THRESHOLD
            )
            sources_with_scores.extend(research_results)
        
        # Run semantic search with industry threshold (more inclusive)
        if industry_candidates:
            logger.info(f"Running semantic search on {len(industry_candidates)} industry sources with threshold {INDUSTRY_THRESHOLD}")
            industry_results = semantic_search_with_scores(
                industry_candidates, keywords, threshold=INDUSTRY_THRESHOLD
            )
            sources_with_scores.extend(industry_results)
    
    # Sort by relevance score (descending), then by date (most recent first)
    sorted_sources = sorted(
        sources_with_scores, 
        key=lambda x: (x[1], x[0].date), 
        reverse=True
    )
    
    # Apply research/industry balancing
    research_count = int(max_results * research_ratio)
    industry_count = max_results - research_count
    
    logger.info(f"Balancing results: {research_count} research, {industry_count} industry")
    
    # Separate by source type
    research_sources = []
    industry_sources = []
    
    for source, score in sorted_sources:
        source_tag = "General"
        if hasattr(source, 'tags') and source.tags:
            source_tag = source.tags[0].capitalize() if source.tags[0] else "General"
        
        if source_tag.lower() == "research":
            research_sources.append((source, score))
        else:
            industry_sources.append((source, score))
    
    # Take balanced amounts from each category
    selected_research = research_sources[:research_count]
    selected_industry = industry_sources[:industry_count]
    
    # If we don't have enough of one type, fill with the other
    total_selected = len(selected_research) + len(selected_industry)
    if total_selected < max_results:
        remaining_slots = max_results - total_selected
        if len(selected_research) < research_count:
            # Need more research, take from industry
            additional_industry = industry_sources[len(selected_industry):len(selected_industry) + remaining_slots]
            selected_industry.extend(additional_industry)
        elif len(selected_industry) < industry_count:
            # Need more industry, take from research  
            additional_research = research_sources[len(selected_research):len(selected_research) + remaining_slots]
            selected_research.extend(additional_research)
    
    # Combine and re-sort by score
    balanced_sources = selected_research + selected_industry
    balanced_sources.sort(key=lambda x: (x[1], x[0].date), reverse=True)
    
    # Extract just the sources
    limited_results = [source for source, score in balanced_sources]
    
    logger.info(f"Balanced filtering complete: {len([s for s in limited_results if hasattr(s, 'tags') and s.tags and s.tags[0].lower() == 'research'])} research, {len([s for s in limited_results if not hasattr(s, 'tags') or not s.tags or s.tags[0].lower() != 'research'])} industry/other")
    return limited_results


def process_content_pipeline(
    topics: List[str],
    max_results: int,
    research_ratio: float,
    selected_days: int = 7
) -> Generator[Dict[str, Any], None, None]:
    """
    The main processing pipeline.
    1. Always scrape fresh content first
    2. Save new content to database 
    3. Query database for sources within date range
    Yields progress updates and finally the results.
    """
    # Step 1: Always scrape fresh content to get latest trending items
    yield {'type': 'status', 'message': 'Scraping fresh content from Hugging Face and Hacker News...'}
    
    fresh_sources = []
    source_names = []

    try:
        hf_papers = scrape_huggingface_trending_papers()
        if hf_papers:
            fresh_sources.extend(hf_papers)
            source_names.append("Hugging Face")
    #        yield {'type': 'status', 'message': f'Found {len(hf_papers)} fresh Hugging Face papers'}
    except Exception as e:
        logger.error(f"Failed to fetch Hugging Face papers: {e}")
        yield {'type': 'error', 'message': f'Failed to fetch Hugging Face papers: {str(e)}'}

    try:
        hn_items = scrape_hacker_news()
        if hn_items:
            fresh_sources.extend(hn_items)
            source_names.append("Hacker News")
    #        yield {'type': 'status', 'message': f'Found {len(hn_items)} fresh Hacker News items'}
    except Exception as e:
        logger.error(f"Failed to fetch Hacker News items: {e}")
        yield {'type': 'error', 'message': f'Failed to fetch Hacker News items: {str(e)}'}

    # Step 2: Save fresh content to database first (without summaries)
    # This tells us which sources are truly new and need summary generation
    try:
        save_result = db_manager.save_sources(fresh_sources)
        new_sources = save_result['new_sources']
        updated_sources = save_result['updated_sources']
        skipped_sources = save_result['skipped_sources']
        
        logger.info(f"Saved {save_result['total_processed']} sources: {len(new_sources)} new, {len(updated_sources)} updated, {skipped_sources} skipped")
        yield {'type': 'status', 'message': f'Saved {save_result["total_processed"]} sources ({len(new_sources)} new)'}
        
        # Step 2b: Generate summaries ONLY for new sources that don't have them
        if new_sources:
            sources_needing_summaries = [source for source in new_sources if not source.summary]
            if sources_needing_summaries:
                from .merger import enrich_sources_with_summaries_and_embeddings
                logger.info(f"Generating summaries and embeddings for {len(sources_needing_summaries)} new sources...")
                yield {'type': 'status', 'message': f'Generating summaries for {len(sources_needing_summaries)} new sources...'}
                
                # Enrich new sources with summaries and embeddings
                enriched_new_sources = enrich_sources_with_summaries_and_embeddings(sources_needing_summaries)
                
                # Update the database with the new summaries and embeddings
                update_result = db_manager.save_sources(enriched_new_sources)
                logger.info(f"Updated {len(enriched_new_sources)} sources with summaries and embeddings")
                yield {'type': 'status', 'message': f'Updated {len(enriched_new_sources)} sources with AI summaries'}
            else:
                logger.info("All new sources already have summaries")
        else:
            logger.info("No new sources found - all were existing or skipped")
            
    except Exception as e:
        logger.error(f"Failed to save sources to database: {e}")
        yield {'type': 'warning', 'message': f'Database save failed, proceeding with fresh content: {str(e)}'}

    # Step 3: Query database for sources within the specified date range
    cutoff_date = datetime.now() - timedelta(days=selected_days)
    yield {'type': 'status', 'message': f'Fetching sources from database added in last {selected_days} days...'}
    
    with db_manager.get_session() as session:
        from .database import Source
        db_sources = session.query(Source).filter(
            Source.created_at >= cutoff_date
        ).order_by(Source.created_at.desc()).all()
    
    if db_sources:
        logger.info(f"Found {len(db_sources)} sources in database from last {selected_days} days")
        yield {'type': 'status', 'message': f'Found {len(db_sources)} sources from last {selected_days} days'}
        
        # Convert database records back to SourceSchema objects
        all_sources = []
        db_source_names = set()
        
        for db_source in db_sources:
            try:
                # Determine source name from tags
                source_tag = "General"
                if db_source.tags and len(db_source.tags) > 0:
                    source_tag = db_source.tags[0].capitalize()
                    if source_tag.lower() == 'research':
                        db_source_names.add("Research Papers")
                    elif source_tag.lower() == 'industry':
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
                    date=db_source.date
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
        logger.warning(f"No database records found for last {selected_days} days, using fresh scraped content")
        yield {'type': 'warning', 'message': f'No database records for {selected_days} days, using fresh content'}
        all_sources = fresh_sources

    total_weight = 100
    scraping_weight = 10
    summary_weight = 70
    filtering_weight = 20
    
    current_progress = scraping_weight
    yield {'type': 'start', 'message': 'Starting unified processing pipeline...', 'total': 100, 'processed': int((current_progress/total_weight)*100)}

    if all_sources:
        # Get all edited summaries once at the beginning for efficiency
        bookmarks = db_manager.get_bookmarks()
        edited_summaries_map = {}
        for bookmark in bookmarks:
            edited_summary = getattr(bookmark, 'summary_edited', None)
            if edited_summary:
                edited_summaries_map[bookmark.link] = edited_summary
        logger.info(f"Found {len(edited_summaries_map)} edited summaries in bookmarks")
        
        # Apply edited summaries to ALL sources first
        for source in all_sources:
            source_link = str(source.link)
            if source_link in edited_summaries_map:
                source.summary = edited_summaries_map[source_link]
                logger.info(f"Applied edited summary for: {source.title[:50]}")
        
        # Now find sources that still need summaries (after applying edited ones)
        sources_needing_summaries = [source for source in all_sources if not source.summary]
        total_to_summarize = len(sources_needing_summaries)
        
        if total_to_summarize > 0:
            yield {'type': 'status', 'message': f'Starting summary generation for {total_to_summarize} sources...'}
            processed_summaries = 0
            for source in sources_needing_summaries:
                processed_summaries += 1
                phase_progress = (processed_summaries / total_to_summarize) * summary_weight
                unified_progress = current_progress + phase_progress
                progress_percent = int((unified_progress / total_weight) * 100)

                source_link = str(source.link)
                
                # Check cached summary
                cached_summary = db_manager.get_summary(source_link)
                if cached_summary:
                    source.summary = cached_summary
                    yield {'type': 'progress', 'message': f'Found cached summary for: {source.title[:50]}...', 'processed': progress_percent, 'total': 100}
                    continue

                yield {'type': 'progress', 'message': f'Generating summary for: {source.title[:50]}...', 'processed': progress_percent, 'total': 100}
                new_summary = generate_summary_from_link(source.source_link)
                if new_summary is None:
                    new_summary = generate_summary_from_link(source.link)
                
                if new_summary:
                    source.summary = new_summary
                    db_manager.add_summary(str(source.link), new_summary)
                    yield {'type': 'progress', 'message': f'✓ Generated summary for: {source.title[:50]}...', 'processed': progress_percent, 'total': 100}
                else:
                    yield {'type': 'warning', 'message': f'⚠ Could not generate summary for: {source.title[:50]}...', 'processed': progress_percent, 'total': 100}
    
    current_progress += summary_weight

    filtered_sources = []
    if topics and all_sources:
        yield {'type': 'status', 'message': f'Applying smart balanced filtering for {len(all_sources)} items...'}
        
        progress_50 = current_progress + (filtering_weight * 0.5)
        yield {'type': 'progress', 'message': 'Applying semantic search & balancing...', 'processed': int((progress_50 / total_weight) * 100), 'total': 100}

        filtered_sources = _apply_balanced_filtering(all_sources, topics, max_results, research_ratio)
        
        complete_progress = current_progress + filtering_weight
        yield {'type': 'progress', 'message': f'Smart filtering complete! Found {len(filtered_sources)} balanced results.', 'processed': int((complete_progress / total_weight) * 100), 'total': 100}

    else:
        filtered_sources = all_sources[:max_results]
        complete_progress = current_progress + filtering_weight
        yield {'type': 'progress', 'message': f'No topic filtering requested - using first {max_results} items', 'processed': int((complete_progress / total_weight) * 100), 'total': 100}

    final_items = []
    for source in filtered_sources:
        source_tag = "General"
        if hasattr(source, 'tags') and source.tags:
            source_tag = source.tags[0].capitalize() if source.tags[0] else "General"
        
        final_items.append({
            'title': source.title,
            'link': str(source.link),
            'summary': source.summary or "No summary available",
            'source': source_tag,
            'created_at': source.date.isoformat() if hasattr(source, 'date') and source.date else datetime.now().isoformat()
        })

    yield {'type': 'complete', 'message': f'Processing complete! Found {len(final_items)} relevant items.'}
    
    yield {
        'type': 'result',
        'data': {
            'items': final_items,
            'total_count': len(final_items),
            'sources': list(set(source_names))
        }
    }
