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


def _filter_sources_advanced(
    sources: List[SourceSchema], 
    keywords: List[str], 
    max_results: int = 10,
    research_ratio: float = 0.5
) -> List[SourceSchema]:
    """
    Advanced filtering with balanced results and proper ordering.
    (Moved from merger.py)
    """
    logger.info("Running keyword search...")
    keyword_matches = keyword_search(sources, keywords)
    logger.info(f"Found {len(keyword_matches)} sources via keyword search.")
    
    keyword_research = []
    keyword_industry = []
    
    for source in keyword_matches:
        if hasattr(source, 'tags') and source.tags and 'research' in source.tags:
            keyword_research.append(source)
        else:
            keyword_industry.append(source)
    
    matched_links = {source.link for source in keyword_matches}
    
    semantic_candidates = [
        source for source in sources
        if source.link not in matched_links
        and source.summary
    ]
    
    research_candidates = []
    industry_candidates = []
    
    for source in semantic_candidates:
        if hasattr(source, 'tags') and source.tags and 'research' in source.tags:
            research_candidates.append(source)
        else:
            industry_candidates.append(source)
    
    logger.info(f"Running semantic search on {len(research_candidates)} research and {len(industry_candidates)} industry sources...")
    
    research_matches = semantic_search_with_scores(
        research_candidates, keywords, threshold=RESEARCH_THRESHOLD
    )
    industry_matches = semantic_search_with_scores(
        industry_candidates, keywords, threshold=INDUSTRY_THRESHOLD
    )
    
    semantic_research = [source for source, score in research_matches]
    semantic_industry = [source for source, score in industry_matches]
    
    logger.info(f"Found {len(semantic_research)} research and {len(semantic_industry)} industry semantic matches")
    
    target_research = int(max_results * research_ratio)
    target_industry = max_results - target_research
    
    final_research = keyword_research[:target_research]
    remaining_research_slots = target_research - len(final_research)
    if remaining_research_slots > 0:
        final_research.extend(semantic_research[:remaining_research_slots])
    
    final_industry = keyword_industry[:target_industry]
    remaining_industry_slots = target_industry - len(final_industry)
    if remaining_industry_slots > 0:
        final_industry.extend(semantic_industry[:remaining_industry_slots])
    
    total_selected = len(final_research) + len(final_industry)
    remaining_slots = max_results - total_selected
    
    if remaining_slots > 0:
        research_overflow = [s for s in semantic_research if s not in final_research]
        industry_overflow = [s for s in semantic_industry if s not in final_industry]
        
        fill_from_research = research_overflow[:remaining_slots]
        final_research.extend(fill_from_research)
        remaining_slots -= len(fill_from_research)

        if remaining_slots > 0:
            fill_from_industry = industry_overflow[:remaining_slots]
            final_industry.extend(fill_from_industry)

    all_results = final_research + final_industry
    
    # Remove duplicates based on link (since SourceSchema is not hashable)
    seen_links = set()
    unique_results = []
    for source in all_results:
        if source.link not in seen_links:
            seen_links.add(source.link)
            unique_results.append(source)

    logger.info(f"Final balanced results: {len([r for r in unique_results if 'research' in r.tags])} research, {len([r for r in unique_results if 'research' not in r.tags])} industry")

    return unique_results[:max_results]


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
        
        if total_to_summarize > 0:
            yield {'type': 'status', 'message': f'Starting summary generation for {total_to_summarize} sources...'}
            processed_summaries = 0
            for source in sources_needing_summaries:
                processed_summaries += 1
                phase_progress = (processed_summaries / total_to_summarize) * summary_weight
                unified_progress = current_progress + phase_progress
                progress_percent = int((unified_progress / total_weight) * 100)

                cached_summary = db_manager.get_summary(str(source.link))
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

        filtered_sources = _filter_sources_advanced(all_sources, topics, max_results, research_ratio)
        
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
