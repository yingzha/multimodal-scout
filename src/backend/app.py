"""
FastAPI backend server for Multimodal Scout application.
Provides REST API endpoints for fetching topics and scraping content.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any
from pydantic import BaseModel
import asyncio
from datetime import datetime, timedelta

from constants import INTERESTED_KEYWORDS
from scraper import scrape_huggingface_trending_papers, scrape_hacker_news
from logger import logger
from merger import filter_sources
from schema import SourceSchema
from database import db_manager

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