"""
FastAPI backend server for Multimodal Scout application.
Provides REST API endpoints for fetching topics and scraping content.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, Response
from typing import List, Dict, Any
import json

from .constants import INTERESTED_KEYWORDS
from .logger import logger
from .database import db_manager
from .pipeline import process_content_pipeline
from .schema import FetchRequest, TopicResponse, ItemResponse, FetchResponse, BookmarkRequest, BookmarkResponse, UploadLinkRequest, UploadLinkResponse
from .utils import generate_summary_from_link, extract_title_from_url, categorize_content, _fetch_article_text


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
            research_ratio=request.researchRatio,
            selected_days=request.selectedDays
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
                research_ratio=request.researchRatio,
                selected_days=request.selectedDays
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
            # Handle both old and new schema gracefully
            summary_edited = getattr(bookmark, 'summary_edited', None)
            display_summary = summary_edited or bookmark.summary or "No summary available"
            is_edited = bool(summary_edited)
            
            bookmark_items.append(ItemResponse(
                title=bookmark.title,
                link=bookmark.link,
                summary=display_summary,
                source=bookmark.source_tag,
                created_at=bookmark.bookmarked_at.isoformat(),
                summary_edited=is_edited
            ))
        return FetchResponse(
            items=bookmark_items,
            total_count=len(bookmark_items),
            sources=["Bookmarks"]
        )
    except Exception as e:
        logger.error(f"Failed to get bookmarks: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get bookmarks: {str(e)}")

@app.put("/api/bookmarks/summary")
async def update_bookmark_summary(link: str, summary: str):
    """Update a bookmark's summary"""
    try:
        logger.info(f"Updating summary for bookmark: {link}")
        success = db_manager.update_bookmark_summary(link, summary)
        if success:
            return BookmarkResponse(
                success=True,
                message="Bookmark summary updated successfully"
            )
        else:
            raise HTTPException(status_code=404, detail="Bookmark not found")
    except Exception as e:
        logger.error(f"Failed to update bookmark summary: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update bookmark summary: {str(e)}")

@app.post("/api/upload-link", response_model=UploadLinkResponse)
async def upload_link(request: UploadLinkRequest):
    """Process and bookmark a user-uploaded link"""
    try:
        url = str(request.url)
        logger.info(f"Processing uploaded link: {url}")
        
        # Check if already bookmarked
        if db_manager.is_bookmarked(url):
            return UploadLinkResponse(
                success=False,
                message="This link is already bookmarked"
            )
        
        # Extract title
        title = extract_title_from_url(request.url)
        if not title:
            title = f"Article from {request.url.host}"
        
        # Extract content for categorization
        article_text = _fetch_article_text(request.url)
        if not article_text:
            article_text = ""
        
        # Generate summary
        summary = generate_summary_from_link(request.url)
        if not summary:
            summary = "No summary available"
        
        # Categorize content
        source_tag = categorize_content(title, article_text, url)
        
        # Add to bookmarks
        bookmark_id = db_manager.add_bookmark(
            title=title,
            link=url,
            source_tag=source_tag,
            summary=summary
        )
        
        # Also cache the summary for future reference
        db_manager.add_summary(url, summary)
        
        logger.info(f"Successfully processed and bookmarked: {title} (Category: {source_tag})")
        
        return UploadLinkResponse(
            success=True,
            message=f"Link processed and added to bookmarks as '{source_tag}' content",
            bookmark_id=bookmark_id,
            title=title,
            summary=summary,
            source_tag=source_tag
        )
        
    except Exception as e:
        logger.error(f"Failed to process uploaded link: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to process link: {str(e)}")

@app.get("/api/bookmarks/export")
async def export_bookmarks():
    """Export all bookmarks to Excel file"""
    try:
        import openpyxl
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill
        from io import BytesIO
        from datetime import datetime
        
        logger.info("Starting bookmark export to Excel")
        
        # Get all bookmarks
        bookmarks = db_manager.get_bookmarks()
        
        # Create workbook and worksheet
        wb = Workbook()
        ws = wb.active
        ws.title = "Bookmarks"
        
        # Define headers
        headers = ["Title", "Summary", "Source URL", "Source Date"]
        
        # Add headers with styling
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
        
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
        
        # Add bookmark data
        for row, bookmark in enumerate(bookmarks, 2):
            # Handle both edited and original summaries
            summary_edited = getattr(bookmark, 'summary_edited', None)
            display_summary = summary_edited or bookmark.summary or "No summary available"
            
            # Format date
            source_date = bookmark.bookmarked_at.strftime("%Y-%m-%d %H:%M:%S") if bookmark.bookmarked_at else "Unknown"
            
            ws.cell(row=row, column=1, value=bookmark.title)
            ws.cell(row=row, column=2, value=display_summary)
            ws.cell(row=row, column=3, value=bookmark.link)
            ws.cell(row=row, column=4, value=source_date)
        
        # Adjust column widths
        ws.column_dimensions['A'].width = 50  # Title
        ws.column_dimensions['B'].width = 80  # Summary
        ws.column_dimensions['C'].width = 60  # URL
        ws.column_dimensions['D'].width = 20  # Date
        
        # Save to BytesIO
        excel_buffer = BytesIO()
        wb.save(excel_buffer)
        excel_buffer.seek(0)
        
        # Generate filename with current timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"multimodal_scout_bookmarks_{timestamp}.xlsx"
        
        logger.info(f"Successfully exported {len(bookmarks)} bookmarks to Excel")
        
        # Return Excel file as response
        return Response(
            content=excel_buffer.getvalue(),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to export bookmarks: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to export bookmarks: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")