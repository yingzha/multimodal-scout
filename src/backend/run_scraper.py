#!/usr/bin/env python3
"""
Standalone script to run a scraper, generate summaries, and save to the database.
Designed to be called by cron jobs.
"""

import sys
import os
import importlib
import time
import asyncio
import inspect
from datetime import datetime

# Add the project root directory to Python path
project_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
sys.path.insert(0, project_root)

from src.backend.logger import logger
from src.backend.database import db_manager
from src.backend.merger import enrich_sources_with_summaries


def main():
    """Run a scraper, generate summaries, and save to database."""
    start_time = time.time()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Enhanced logging header
    logger.info("=" * 80)
    logger.info(f"🤖 CRON JOB STARTED: {timestamp}")
    logger.info("=" * 80)

    if len(sys.argv) != 2:
        logger.error(
            "❌ USAGE ERROR: python -m src.backend.run_scraper <scraper_function_name>"
        )
        sys.exit(1)

    scraper_function_name = sys.argv[1]
    logger.info(f"📋 Target scraper: {scraper_function_name}")

    try:
        module_name, function_name = scraper_function_name.rsplit(".", 1)
        logger.info(f"📦 Loading module: {module_name}")
        logger.info(f"🔧 Loading function: {function_name}")

        scraper_module = importlib.import_module(module_name)
        scraper_function = getattr(scraper_module, function_name)
        logger.info("✅ Scraper function loaded successfully")

    except (ImportError, AttributeError, ValueError) as e:
        logger.error(
            f"❌ MODULE LOAD ERROR: Could not find scraper function: {scraper_function_name}"
        )
        logger.error(f"❌ Error details: {e}")
        sys.exit(1)

    try:
        logger.info(f"🚀 Starting scheduled scraping job for {scraper_function_name}")

        # Scrape items
        scrape_start = time.time()
        if inspect.iscoroutinefunction(scraper_function):
            logger.info("🔄 Running async scraper function")
            results = asyncio.run(scraper_function())
        else:
            logger.info("🔄 Running sync scraper function")
            results = scraper_function()
        scrape_time = time.time() - scrape_start

        logger.info(f"📊 Scraping completed in {scrape_time:.2f}s")
        logger.info(f"📈 Scraped {len(results)} items")

        if results:
            # Generate summaries for items that don't have them
            logger.info("🧠 Generating summaries for items without summaries...")
            summary_start = time.time()
            enriched_results = enrich_sources_with_summaries(results)
            summary_time = time.time() - summary_start

            logger.info(f"🧠 Summary generation completed in {summary_time:.2f}s")

            # Save to database
            logger.info("💾 Saving items to database...")
            db_start = time.time()
            try:
                db_manager.save_sources(enriched_results)
                db_time = time.time() - db_start
                logger.info(f"💾 Database save completed in {db_time:.2f}s")
                logger.info(
                    f"✅ Successfully saved {len(enriched_results)} items to database"
                )
            except Exception as db_error:
                db_time = time.time() - db_start
                logger.error(f"💾 Database save failed in {db_time:.2f}s")
                logger.error(f"❌ Database error: {db_error}")
                logger.info(
                    "⚠️  Continuing with cron job (summaries were cached successfully)"
                )
        else:
            logger.info("📭 No items to process")

        total_time = time.time() - start_time
        end_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        logger.info("=" * 80)
        logger.info(f"✅ SUCCESS: Scraping job completed successfully")
        logger.info(f"⏱️  Total execution time: {total_time:.2f}s")
        logger.info(f"🏁 Job ended: {end_timestamp}")
        logger.info("=" * 80)

    except Exception as e:
        total_time = time.time() - start_time
        end_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        logger.error("=" * 80)
        logger.error(f"❌ FAILURE: Scraping job failed after {total_time:.2f}s")
        logger.error(f"❌ Error: {e}")
        logger.error(f"🏁 Job ended: {end_timestamp}")
        logger.error("=" * 80)
        logger.error("Full error traceback:", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
