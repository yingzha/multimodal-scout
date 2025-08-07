#!/usr/bin/env python3
"""
Standalone script to run Hacker News scraper.
Designed to be called by cron jobs.
"""

import sys
import os

# Add the src directory to Python path
sys.path.insert(0, '/app/src')

from backend.scraper import scrape_hacker_news
from backend.logger import logger
from backend.database import db_manager
from backend.merger import enrich_sources_with_summaries

def main():
    """Run the Hacker News scraper, generate summaries, and save to database."""
    try:
        logger.info("Starting scheduled Hacker News scraping job")
        
        # Scrape stories
        results = scrape_hacker_news()
        logger.info(f"Scraped {len(results)} Hacker News stories")
        
        if results:
            # Generate summaries for stories that don't have them
            logger.info("Generating summaries for stories without summaries...")
            enriched_results = enrich_sources_with_summaries(results)
            
            # Save to database
            logger.info("Saving stories to database...")
            db_manager.save_sources(enriched_results)
            logger.info(f"Successfully saved {len(enriched_results)} stories to database")
        else:
            logger.info("No stories to process")
        
        logger.info("Hacker News scraping job completed successfully")
        
    except Exception as e:
        logger.error(f"Hacker News scraping job failed: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()