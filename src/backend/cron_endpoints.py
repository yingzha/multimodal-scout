"""
Cron job endpoints for Cloud Scheduler integration.
These endpoints replace the Docker cron container when running on Google Cloud.
"""

from fastapi import FastAPI, HTTPException, Header
from typing import Optional
import asyncio

from .scraper import scrape_huggingface_trending_papers, scrape_hacker_news
from .merger import enrich_sources_with_summaries_and_embeddings
from .database import db_manager
from .logger import logger

# Create separate FastAPI app for cron jobs
cron_app = FastAPI(title="Multimodal Scout Cron Jobs")

def verify_scheduler_request(x_cloudscheduler: Optional[str] = Header(None)):
    """Verify request is from Cloud Scheduler."""
    if not x_cloudscheduler:
        raise HTTPException(status_code=401, detail="Unauthorized - not from Cloud Scheduler")

@cron_app.post("/cron/hacker-news")
async def cron_hacker_news(x_cloudscheduler: Optional[str] = Header(None)):
    """Cron job endpoint for Hacker News scraping."""
    verify_scheduler_request(x_cloudscheduler)
    
    try:
        logger.info("🕐 Starting Hacker News cron job...")
        
        # Scrape Hacker News
        sources = scrape_hacker_news()
        if not sources:
            logger.warning("No Hacker News sources found")
            return {"status": "completed", "message": "No sources found", "count": 0}
        
        logger.info(f"📰 Found {len(sources)} Hacker News sources")
        
        # Enrich with summaries and pre-generate embeddings
        enriched_sources = enrich_sources_with_summaries_and_embeddings(sources)
        
        # Save to database
        save_result = db_manager.save_sources(enriched_sources)
        logger.info(f"Save result: {save_result}")
        
        logger.info(f"✅ Hacker News cron job completed: {len(enriched_sources)} sources processed")
        
        return {
            "status": "completed",
            "message": f"Successfully processed {len(enriched_sources)} Hacker News sources",
            "count": len(enriched_sources)
        }
        
    except Exception as e:
        logger.error(f"❌ Hacker News cron job failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Cron job failed: {str(e)}")

@cron_app.post("/cron/hugging-face")
async def cron_hugging_face(x_cloudscheduler: Optional[str] = Header(None)):
    """Cron job endpoint for Hugging Face scraping."""
    verify_scheduler_request(x_cloudscheduler)
    
    try:
        logger.info("🕐 Starting Hugging Face cron job...")
        
        # Scrape Hugging Face
        sources = scrape_huggingface_trending_papers()
        if not sources:
            logger.warning("No Hugging Face sources found")
            return {"status": "completed", "message": "No sources found", "count": 0}
        
        logger.info(f"🤗 Found {len(sources)} Hugging Face sources")
        
        # Enrich with summaries and pre-generate embeddings
        enriched_sources = enrich_sources_with_summaries_and_embeddings(sources)
        
        # Save to database
        save_result = db_manager.save_sources(enriched_sources)
        logger.info(f"Save result: {save_result}")
        
        logger.info(f"✅ Hugging Face cron job completed: {len(enriched_sources)} sources processed")
        
        return {
            "status": "completed", 
            "message": f"Successfully processed {len(enriched_sources)} Hugging Face sources",
            "count": len(enriched_sources)
        }
        
    except Exception as e:
        logger.error(f"❌ Hugging Face cron job failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Cron job failed: {str(e)}")

@cron_app.get("/health")
async def cron_health():
    """Health check endpoint for cron service."""
    return {"status": "healthy", "service": "multimodal-scout-cron"}

if __name__ == "__main__":
    import uvicorn
    from .config import config
    uvicorn.run(cron_app, host="0.0.0.0", port=config.port, log_level="info")