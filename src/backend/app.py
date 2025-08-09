"""
FastAPI backend server for Multimodal Scout application.
Provides REST API endpoints for fetching topics and scraping content.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from typing import List, Dict, Any, Generator
from pydantic import BaseModel
import asyncio
import json
from datetime import datetime, timedelta

from .constants import INTERESTED_KEYWORDS
from .scraper import scrape_huggingface_trending_papers, scrape_hacker_news
from .logger import logger
from .merger import filter_sources, enrich_sources_with_summaries
from .search import keyword_search, semantic_search
from .schema import SourceSchema
from .database import db_manager
from .cache import get_summary_from_cache, add_summary_to_cache
from .utils import generate_summary_from_link

app = FastAPI(
    title="Multimodal Scout API",
    description="API for fetching AI/ML content from various sources",
    version="1.0.0"
)

# Add CORS middleware to allow frontend connections
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def enrich_sources_with_progress(sources: List[SourceSchema], phase_start: int, phase_weight: int, total_weight: int):
    """
    Generates summaries for sources that are missing them, yielding progress updates.
    Uses unified progress tracking across phases.
    """
    sources_needing_summaries = [source for source in sources if not source.summary]
    total_sources = len(sources_needing_summaries)
    
    if total_sources == 0:
        yield f"data: {json.dumps({'type': 'info', 'message': 'All sources already have summaries'})}\n\n"
        return
    
    yield f"data: {json.dumps({'type': 'status', 'message': f'Starting summary generation for {total_sources} sources...'})}\n\n"
    
    processed = 0
    for source in sources_needing_summaries:
        processed += 1
        
        # Calculate unified progress
        phase_progress = (processed / total_sources) * phase_weight
        unified_progress = phase_start + phase_progress
        progress_percent = int((unified_progress / total_weight) * 100)
        
        # Check cache first
        cached_summary = get_summary_from_cache(str(source.link))
        if cached_summary:
            source.summary = cached_summary
            yield f"data: {json.dumps({'type': 'progress', 'message': f'Found cached summary for: {source.title[:50]}...', 'processed': progress_percent, 'total': 100})}\n\n"
            continue
        
        # Generate new summary
        yield f"data: {json.dumps({'type': 'progress', 'message': f'Generating summary for: {source.title[:50]}...', 'processed': progress_percent, 'total': 100})}\n\n"
        
        new_summary = generate_summary_from_link(source.source_link)
        if new_summary is None:
            new_summary = generate_summary_from_link(source.link)
            
        if new_summary:
            source.summary = new_summary
            add_summary_to_cache(str(source.link), new_summary)
            yield f"data: {json.dumps({'type': 'progress', 'message': f'✓ Generated summary for: {source.title[:50]}...', 'processed': progress_percent, 'total': 100})}\n\n"
        else:
            yield f"data: {json.dumps({'type': 'warning', 'message': f'⚠ Could not generate summary for: {source.title[:50]}...', 'processed': progress_percent, 'total': 100})}\n\n"

def filter_sources_with_progress(sources: List[SourceSchema], keywords: List[str], phase_start: int, phase_weight: int, total_weight: int):
    """
    Filters sources using keyword and semantic search with progress updates.
    Uses unified progress tracking across phases.
    """
    from .merger import SEMANTIC_SIMILARITY_THRESHOLD
    
    # --- Pass 1: Keyword Search (fast) ---
    yield f"data: {json.dumps({'type': 'status', 'message': 'Running keyword search...'})}\n\n"
    keyword_matches = keyword_search(sources, keywords)
    
    # Update progress for keyword search completion (takes 10% of this phase)
    keyword_progress = phase_start + (phase_weight * 0.1)
    progress_percent = int((keyword_progress / total_weight) * 100)
    yield f"data: {json.dumps({'type': 'progress', 'message': f'Found {len(keyword_matches)} sources via keyword search', 'processed': progress_percent, 'total': 100})}\n\n"

    matched_links = {source.link for source in keyword_matches}

    # --- Pass 2: Semantic Search (slow, embedding generation) ---
    semantic_candidates = [
        source for source in sources
        if source.link not in matched_links
        and source.summary  # Ensure there is a summary to search on
    ]
    
    if semantic_candidates:
        yield f"data: {json.dumps({'type': 'status', 'message': f'Running semantic search on {len(semantic_candidates)} sources with summaries...'})}\n\n"
        
        # Semantic search takes 90% of this phase
        semantic_start = phase_start + (phase_weight * 0.1)
        semantic_weight = phase_weight * 0.9
        
        # Start semantic search
        semantic_progress = semantic_start
        progress_percent = int((semantic_progress / total_weight) * 100)
        yield f"data: {json.dumps({'type': 'progress', 'message': 'Generating embeddings for semantic search...', 'processed': progress_percent, 'total': 100})}\n\n"
        
        # Process semantic search
        semantic_matches = semantic_search(semantic_candidates, keywords, threshold=SEMANTIC_SIMILARITY_THRESHOLD)
        
        # Complete semantic search
        semantic_complete = phase_start + phase_weight
        progress_percent = int((semantic_complete / total_weight) * 100)
        yield f"data: {json.dumps({'type': 'progress', 'message': f'Semantic search complete! Found {len(semantic_matches)} additional matches.', 'processed': progress_percent, 'total': 100})}\n\n"
    else:
        semantic_matches = []
        # Still advance progress if no semantic search needed
        complete_progress = phase_start + phase_weight
        progress_percent = int((complete_progress / total_weight) * 100)
        yield f"data: {json.dumps({'type': 'progress', 'message': 'No sources available for semantic search (no summaries)', 'processed': progress_percent, 'total': 100})}\n\n"
    
    # Combine results
    filtered_sources = keyword_matches + semantic_matches
    yield f"data: {json.dumps({'type': 'status', 'message': f'Total filtered results: {len(filtered_sources)} sources'})}\n\n"

class FetchRequest(BaseModel):
    """Request model for fetching top items"""
    selectedDays: int
    topics: List[str]

class TopicResponse(BaseModel):
    """Response model for default topics"""
    topics: List[str]

class ItemResponse(BaseModel):
    """Response model for individual items"""
    title: str
    link: str
    summary: str
    source: str
    created_at: str

class FetchResponse(BaseModel):
    """Response model for fetched items"""
    items: List[ItemResponse]
    total_count: int
    sources: List[str]

class BookmarkRequest(BaseModel):
    """Request model for bookmarking"""
    title: str
    link: str
    source: str
    summary: str = ""

class BookmarkResponse(BaseModel):
    """Response model for bookmark operations"""
    success: bool
    message: str
    bookmark_id: str = None

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "Multimodal Scout API is running", "status": "healthy"}

@app.get("/api/topics", response_model=TopicResponse)
async def get_default_topics():
    """
    Get default interested topics from constants.
    These topics are read-only and cannot be modified by users.
    """
    try:
        logger.info("Fetching default topics from constants")
        return TopicResponse(topics=INTERESTED_KEYWORDS)
    except Exception as e:
        logger.error(f"Failed to fetch default topics: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch default topics")

@app.post("/api/fetch", response_model=FetchResponse)
async def fetch_top_items(request: FetchRequest):
    """
    Fetch top items from various sources based on topics and time range.
    
    Args:
        request: Contains selectedDays and topics list
        
    Returns:
        Aggregated items from Hugging Face and Hacker News
    """
    try:
        logger.info(f"Fetching items for {request.selectedDays} days with topics: {request.topics}")
        
        # Combine default topics with custom topics for filtering
        all_topics = request.topics
        
        all_sources = []
        source_names = []
        
        try:
            # Fetch Hugging Face papers
            logger.info("Scraping Hugging Face trending papers...")
            hf_papers = scrape_huggingface_trending_papers()
            if hf_papers:
                all_sources.extend(hf_papers)
                source_names.append("Hugging Face")
                logger.info(f"Found {len(hf_papers)} Hugging Face papers")
        except Exception as e:
            logger.error(f"Failed to fetch Hugging Face papers: {e}")
        
        try:
            # Fetch Hacker News items
            logger.info("Scraping Hacker News...")
            hn_items = scrape_hacker_news()
            if hn_items:
                all_sources.extend(hn_items)
                source_names.append("Hacker News")
                logger.info(f"Found {len(hn_items)} Hacker News items")
        except Exception as e:
            logger.error(f"Failed to fetch Hacker News items: {e}")
        
        # Enrich sources with AI-generated summaries if they are missing
        if all_sources:
            logger.info(f"Enriching {len(all_sources)} sources with summaries...")
            all_sources = enrich_sources_with_summaries(all_sources)
        
        # Filter sources based on topics using the existing merger logic
        if all_topics and all_sources:
            logger.info(f"Filtering {len(all_sources)} items with topics: {all_topics}")
            filtered_sources = filter_sources(all_sources, all_topics)
            logger.info(f"Filtered down to {len(filtered_sources)} relevant items")
        else:
            filtered_sources = all_sources[:20]  # Limit to 20 items if no filtering
        
        # Convert to response format
        items = []
        for source in filtered_sources[:20]:  # Limit to top 20
            # Use tags instead of source, with fallback
            source_tag = "General"
            if hasattr(source, 'tags') and source.tags:
                # Use the first tag, capitalize it
                source_tag = source.tags[0].capitalize() if source.tags[0] else "General"
            
            items.append(ItemResponse(
                title=source.title,
                link=str(source.link),  # Convert HttpUrl to string
                summary=source.summary or "No summary available",
                source=source_tag,
                created_at=source.date.isoformat() if hasattr(source, 'date') and source.date else datetime.now().isoformat()
            ))
        
        logger.info(f"Successfully prepared {len(items)} items for response")
        
        return FetchResponse(
            items=items,
            total_count=len(items),
            sources=list(set(source_names))
        )
        
    except Exception as e:
        logger.error(f"Failed to fetch items: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch items: {str(e)}")

@app.post("/api/fetch-stream")
async def fetch_top_items_stream(request: FetchRequest):
    """
    Fetch top items with streaming progress updates for summary generation.
    Uses Server-Sent Events (SSE) to provide real-time progress.
    """
    def generate_stream():
        try:
            logger.info(f"Starting streaming fetch for {request.selectedDays} days with topics: {request.topics}")
            
            # Combine default topics with custom topics for filtering
            all_topics = request.topics
            
            all_sources = []
            source_names = []
            
            # Initial status update
            yield f"data: {json.dumps({'type': 'status', 'message': 'Fetching sources from Hugging Face and Hacker News...'})}\n\n"
            
            try:
                # Fetch Hugging Face papers
                logger.info("Scraping Hugging Face trending papers...")
                hf_papers = scrape_huggingface_trending_papers()
                if hf_papers:
                    all_sources.extend(hf_papers)
                    source_names.append("Hugging Face")
                    yield f"data: {json.dumps({'type': 'status', 'message': f'Found {len(hf_papers)} Hugging Face papers'})}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'message': f'Failed to fetch Hugging Face papers: {str(e)}'})}\n\n"
            
            try:
                # Fetch Hacker News items
                logger.info("Scraping Hacker News...")
                hn_items = scrape_hacker_news()
                if hn_items:
                    all_sources.extend(hn_items)
                    source_names.append("Hacker News")
                    yield f"data: {json.dumps({'type': 'status', 'message': f'Found {len(hn_items)} Hacker News items'})}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'message': f'Failed to fetch Hacker News items: {str(e)}'})}\n\n"
            
            # Define phase weights for unified progress
            # Phase 1: Scraping (already completed) - 10%
            # Phase 2: Summary generation - 70% (most time-consuming)  
            # Phase 3: Filtering (keyword + semantic search) - 20%
            total_weight = 100
            scraping_weight = 10  # Already done
            summary_weight = 70
            filtering_weight = 20
            
            current_progress = scraping_weight  # Start after scraping
            
            # Enrich sources with progress updates
            if all_sources:
                yield f"data: {json.dumps({'type': 'status', 'message': f'Processing {len(all_sources)} sources for summary enrichment...'})}\n\n"
                yield f"data: {json.dumps({'type': 'start', 'message': 'Starting unified processing pipeline...', 'total': 100})}\n\n"
                
                # Phase 2: Summary generation (70% of total progress)
                for progress_update in enrich_sources_with_progress(all_sources, current_progress, summary_weight, total_weight):
                    yield progress_update
                
                current_progress += summary_weight  # Now at 80%
            
            # Filter sources based on topics with progress updates
            if all_topics and all_sources:
                yield f"data: {json.dumps({'type': 'status', 'message': f'Starting topic filtering for {len(all_sources)} items...'})}\n\n"
                
                # Phase 3: Filtering (20% of total progress)
                for progress_update in filter_sources_with_progress(all_sources, all_topics, current_progress, filtering_weight, total_weight):
                    yield progress_update
                
                # Get the actual filtered sources using the original function
                filtered_sources = filter_sources(all_sources, all_topics)
                current_progress = total_weight  # Now at 100%
            else:
                filtered_sources = all_sources[:20]  # Limit to 20 items if no filtering
                # Still advance to 100% even if no filtering
                yield f"data: {json.dumps({'type': 'progress', 'message': 'No topic filtering requested - using first 20 items', 'processed': 100, 'total': 100})}\n\n"
            
            # Convert to response format
            items = []
            for source in filtered_sources[:20]:  # Limit to top 20
                # Use tags instead of source, with fallback
                source_tag = "General"
                if hasattr(source, 'tags') and source.tags:
                    # Use the first tag, capitalize it
                    source_tag = source.tags[0].capitalize() if source.tags[0] else "General"
                
                items.append({
                    'title': source.title,
                    'link': str(source.link),  # Convert HttpUrl to string
                    'summary': source.summary or "No summary available",
                    'source': source_tag,
                    'created_at': source.date.isoformat() if hasattr(source, 'date') and source.date else datetime.now().isoformat()
                })
            
            # Final completion message
            yield f"data: {json.dumps({'type': 'complete', 'message': f'Processing complete! Found {len(items)} relevant items.', 'processed': 100, 'total': 100})}\n\n"
            
            # Final result
            result = {
                'type': 'result',
                'data': {
                    'items': items,
                    'total_count': len(items),
                    'sources': list(set(source_names))
                }
            }
            yield f"data: {json.dumps(result)}\n\n"
            yield "data: [DONE]\n\n"
            
        except Exception as e:
            logger.error(f"Failed to fetch items in stream: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': f'Failed to fetch items: {str(e)}'})}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "*",
        }
    )

@app.post("/api/bookmarks", response_model=BookmarkResponse)
async def add_bookmark(request: BookmarkRequest):
    """Add a bookmark"""
    try:
        logger.info(f"Adding bookmark for: {request.title}")
        bookmark_id = db_manager.add_bookmark(
            title=request.title,
            link=request.link,
            source_tag=request.source,
            summary=request.summary
        )
        return BookmarkResponse(
            success=True,
            message="Bookmark added successfully",
            bookmark_id=bookmark_id
        )
    except Exception as e:
        logger.error(f"Failed to add bookmark: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to add bookmark: {str(e)}")

@app.delete("/api/bookmarks")
async def remove_bookmark(link: str):
    """Remove a bookmark by link"""
    try:
        logger.info(f"Removing bookmark for link: {link}")
        success = db_manager.remove_bookmark(link)
        if success:
            return BookmarkResponse(
                success=True,
                message="Bookmark removed successfully"
            )
        else:
            return BookmarkResponse(
                success=False,
                message="Bookmark not found"
            )
    except Exception as e:
        logger.error(f"Failed to remove bookmark: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to remove bookmark: {str(e)}")

@app.get("/api/bookmarks/check")
async def check_bookmark(link: str):
    """Check if a link is bookmarked"""
    try:
        is_bookmarked = db_manager.is_bookmarked(link)
        return {"is_bookmarked": is_bookmarked}
    except Exception as e:
        logger.error(f"Failed to check bookmark: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to check bookmark: {str(e)}")

@app.get("/api/bookmarks")
async def get_bookmarks():
    """Get all bookmarks"""
    try:
        bookmarks = db_manager.get_bookmarks()
        bookmark_items = []
        for bookmark in bookmarks:
            bookmark_items.append(ItemResponse(
                title=bookmark.title,
                link=bookmark.link,
                summary=bookmark.summary or "No summary available",
                source=bookmark.source_tag,
                created_at=bookmark.bookmarked_at.isoformat()
            ))
        return FetchResponse(
            items=bookmark_items,
            total_count=len(bookmark_items),
            sources=["Bookmarks"]
        )
    except Exception as e:
        logger.error(f"Failed to get bookmarks: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get bookmarks: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")