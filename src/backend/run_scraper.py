#!/usr/bin/env python3
"""
Standalone script to run a scraper, generate summaries, and save to the database.
Designed to be called by cron jobs.
"""

import sys
import os
import importlib

# Add the src directory to Python path
sys.path.insert(0, '/app/src')

from backend.logger import logger
from backend.database import db_manager
from backend.merger import enrich_sources_with_summaries

def main():
    """Run a scraper, generate summaries, and save to database."""
    if len(sys.argv) != 2:
        logger.error("Usage: python -m src.backend.run_scraper <scraper_function_name>")
        sys.exit(1)

    scraper_function_name = sys.argv[1]
    
    try:
        module_name, function_name = scraper_function_name.rsplit('.', 1)
        scraper_module = importlib.import_module(module_name)
        scraper_function = getattr(scraper_module, function_name)
    except (ImportError, AttributeError, ValueError) as e:
        logger.error(f"Could not find scraper function: {scraper_function_name}")
        logger.error(e)
        sys.exit(1)

    try:
        logger.info(f"Starting scheduled scraping job for {scraper_function_name}")
        
        # Scrape items
        results = scraper_function()
        logger.info(f"Scraped {len(results)} items")
        
        if results:
            # Generate summaries for items that don't have them
            logger.info("Generating summaries for items without summaries...")
            enriched_results = enrich_sources_with_summaries(results)
            
            # Save to database
            logger.info("Saving items to database...")
            db_manager.save_sources(enriched_results)
            logger.info(f"Successfully saved {len(enriched_results)} items to database")
        else:
            logger.info("No items to process")
        
        logger.info(f"Scraping job for {scraper_function_name} completed successfully")
        
    except Exception as e:
        logger.error(f"Scraping job for {scraper_function_name} failed: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
