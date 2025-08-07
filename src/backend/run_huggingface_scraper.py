#!/usr/bin/env python3
"""
Standalone script to run Hugging Face scraper.
Designed to be called by cron jobs.
"""

import sys
import os

# Add the src directory to Python path
sys.path.insert(0, '/app/src')

from backend.scraper import scrape_huggingface_trending_papers
from backend.logger import logger
from backend.database import db_manager
from backend.merger import enrich_sources_with_summaries

def main():
    """Run the Hugging Face scraper, generate summaries, and save to database."""
    try:
        logger.info("Starting scheduled Hugging Face scraping job")
        
        # Scrape papers
        results = scrape_huggingface_trending_papers()
        logger.info(f"Scraped {len(results)} Hugging Face papers")
        
        if results:
            # Generate summaries for papers that don't have them
            logger.info("Generating summaries for papers without summaries...")
            enriched_results = enrich_sources_with_summaries(results)
            
            # Save to database
            logger.info("Saving papers to database...")
            db_manager.save_sources(enriched_results)
            logger.info(f"Successfully saved {len(enriched_results)} papers to database")
        else:
            logger.info("No papers to process")
        
        logger.info("Hugging Face scraping job completed successfully")
        
    except Exception as e:
        logger.error(f"Hugging Face scraping job failed: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()