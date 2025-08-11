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
from .search import keyword_search, semantic_search_with_scores
from .database import db_manager
from .utils import generate_summary_from_link
from .constants import RESEARCH_THRESHOLD, INDUSTRY_THRESHOLD
from .merger import filter_sources


def _apply_balanced_filtering(sources: List[SourceSchema], keywords: List[str], max_results: int = 10, research_ratio: float = 0.5) -> List[SourceSchema]:
    """
    Apply balanced filtering using the existing filter_sources function with result limiting.
    """
    logger.info(f"Applying balanced filtering to {len(sources)} sources...")
    
    # Use the existing filter_sources function from merger.py
    filtered_sources = filter_sources(sources, keywords)
    
    # Sort by date (most recent first) and limit results
    sorted_sources = sorted(filtered_sources, key=lambda s: s.date, reverse=True)
    limited_results = sorted_sources[:max_results]
    
    logger.info(f"Filtered and limited to {len(limited_results)} results")
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
        sources_needing_summaries = [source for source in all_sources if not source.summary]
        total_to_summarize = len(sources_needing_summaries)
        
        # Get all edited summaries once at the beginning for efficiency
        bookmarks = db_manager.get_bookmarks()
        edited_summaries_map = {}
        for bookmark in bookmarks:
            edited_summary = getattr(bookmark, 'summary_edited', None)
            if edited_summary:
                edited_summaries_map[bookmark.link] = edited_summary
        logger.info(f"Found {len(edited_summaries_map)} edited summaries in bookmarks")
        
        if total_to_summarize > 0:
            yield {'type': 'status', 'message': f'Starting summary generation for {total_to_summarize} sources...'}
            processed_summaries = 0
            for source in sources_needing_summaries:
                processed_summaries += 1
                phase_progress = (processed_summaries / total_to_summarize) * summary_weight
                unified_progress = current_progress + phase_progress
                progress_percent = int((unified_progress / total_weight) * 100)

                source_link = str(source.link)
                
                # Check for edited summary from bookmarks first (fast lookup)
                if source_link in edited_summaries_map:
                    source.summary = edited_summaries_map[source_link]
                    yield {'type': 'progress', 'message': f'Found edited summary for: {source.title[:50]}...', 'processed': progress_percent, 'total': 100}
                    logger.info(f"Using edited summary for: {source.title[:50]}")
                    continue
                
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
