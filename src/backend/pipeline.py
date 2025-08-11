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
from datetime import datetime

from .scraper import scrape_huggingface_trending_papers, scrape_hacker_news
from .logger import logger
from .schema import SourceSchema
from .database import db_manager
from .utils import generate_summary_from_link
from .search import keyword_search, semantic_search_with_scores
from .constants import SEMANTIC_SIMILARITY_THRESHOLD


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
    
    # Pass 2: Semantic Search - for remaining sources with summaries
    semantic_candidates = [
        source for source in sources
        if source.link not in matched_links and source.summary
    ]
    
    if semantic_candidates:
        logger.info(f"Running semantic search on {len(semantic_candidates)} remaining sources...")
        semantic_results = semantic_search_with_scores(
            semantic_candidates, keywords, threshold=SEMANTIC_SIMILARITY_THRESHOLD
        )
        sources_with_scores.extend(semantic_results)
    
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
    research_ratio: float
) -> Generator[Dict[str, Any], None, None]:
    """
    The main processing pipeline.
    Yields progress updates and finally the results.
    """
    all_sources = []
    source_names = []

    yield {'type': 'status', 'message': 'Fetching sources from Hugging Face and Hacker News...'}
    
    try:
        hf_papers = scrape_huggingface_trending_papers()
        if hf_papers:
            all_sources.extend(hf_papers)
            source_names.append("Hugging Face")
            yield {'type': 'status', 'message': f'Found {len(hf_papers)} Hugging Face papers'}
    except Exception as e:
        logger.error(f"Failed to fetch Hugging Face papers: {e}")
        yield {'type': 'error', 'message': f'Failed to fetch Hugging Face papers: {str(e)}'}

    try:
        hn_items = scrape_hacker_news()
        if hn_items:
            all_sources.extend(hn_items)
            source_names.append("Hacker News")
            yield {'type': 'status', 'message': f'Found {len(hn_items)} Hacker News items'}
    except Exception as e:
        logger.error(f"Failed to fetch Hacker News items: {e}")
        yield {'type': 'error', 'message': f'Failed to fetch Hacker News items: {str(e)}'}

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
