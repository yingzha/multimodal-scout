"""
FastAPI backend server for Multimodal Scout application.
Provides REST API endpoints for fetching topics and scraping content.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from typing import List, Dict, Any
from pydantic import BaseModel
import json
from datetime import datetime
import asyncio

from .constants import INTERESTED_KEYWORDS
from .logger import logger
from .database import db_manager
from .pipeline import process_content_pipeline

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
    maxResults: int = 10  # Default to 10 results
    researchRatio: float = 0.5  # Default to 50/50 research/industry balance

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
    This is the non-streaming version that uses the core pipeline.
    """
    try:
        logger.info(f"Fetching items for {request.selectedDays} days with topics: {request.topics}")
        
        pipeline_generator = process_content_pipeline(
            topics=request.topics,
            max_results=request.maxResults,
            research_ratio=request.researchRatio
        )
        
        final_result = None
        # The pipeline is a generator, so we iterate through it to get the final result.
        # In the non-streaming case, we ignore progress events and just wait for the 'result' event.
        for event in pipeline_generator:
            if event['type'] == 'result':
                final_result = event['data']
                break
        
        if final_result:
            logger.info(f"Successfully prepared {len(final_result['items'])} items for response")
            return FetchResponse(
                items=final_result['items'],
                total_count=final_result['total_count'],
                sources=final_result['sources']
            )
        else:
            logger.error("Pipeline did not return a final result.")
            raise HTTPException(status_code=500, detail="Failed to fetch items: Pipeline finished without result.")

    except Exception as e:
        logger.error(f"Failed to fetch items: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch items: {str(e)}")

@app.post("/api/fetch-stream")
async def fetch_top_items_stream(request: FetchRequest):
    """
    Fetch top items with streaming progress updates using the core pipeline.
    Uses Server-Sent Events (SSE) to provide real-time progress.
    """
    async def generate_stream():
        try:
            logger.info(f"Starting streaming fetch for {request.selectedDays} days with topics: {request.topics}")
            
            pipeline_generator = process_content_pipeline(
                topics=request.topics,
                max_results=request.maxResults,
                research_ratio=request.researchRatio
            )

            for event in pipeline_generator:
                yield f"data: {json.dumps(event)}\n\n"
                # Add a small sleep to allow the client to process the event
                await asyncio.sleep(0.01)

            yield "data: [DONE]\n\n"
            
        except Exception as e:
            logger.error(f"Failed to fetch items in stream: {e}", exc_info=True)
            error_event = {'type': 'error', 'message': f'An unexpected error occurred: {str(e)}'}
            yield f"data: {json.dumps(error_event)}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
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