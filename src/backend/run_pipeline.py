#!/usr/bin/env python3
"""
Standalone script to run the full content processing pipeline.
Designed to be called by cron jobs for complete content processing.
"""

import sys
import os
import asyncio
import time
from datetime import datetime

# Add the project root directory to Python path
project_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
sys.path.insert(0, project_root)

from src.backend.logger import logger
from src.backend.pipeline import process_content_pipeline


async def main():
    """Run the full content processing pipeline."""
    start_time = time.time()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Enhanced logging header
    logger.info("=" * 80)
    logger.info(f"🤖 PIPELINE CRON JOB STARTED: {timestamp}")
    logger.info("=" * 80)

    try:
        logger.info("🚀 Starting full content processing pipeline...")

        # Run the full pipeline with reasonable defaults for cron job
        # - topics: empty list means no topic filtering (process all content)
        # - max_results: 100 items should be plenty for regular updates
        # - research_ratio: 0.5 for balanced content
        # - selected_days: 1 day to process recent content
        pipeline_generator = process_content_pipeline(
            topics=[],  # No topic filtering for cron jobs
            max_results=100,
            research_ratio=0.5,
            selected_days=1,  # Process content from last day
        )

        # Process all pipeline events and log key milestones
        event_count = 0
        final_result = None

        async for event in pipeline_generator:
            event_count += 1
            event_type = event.get("type", "unknown")
            message = event.get("message", "")

            # Log important events
            if event_type in ["status", "start", "complete", "error"]:
                logger.info(f"📋 {event_type.upper()}: {message}")
            elif event_type == "progress":
                processed = event.get("processed", 0)
                total = event.get("total", 100)
                logger.info(f"⏳ PROGRESS: {processed}% - {message}")
            elif event_type == "result":
                final_result = event.get("data", {})
                logger.info("🎯 RESULT: Pipeline completed with final results")

            # Safety break to prevent infinite loops
            if event_count > 50:
                logger.warning(
                    "⚠️  Pipeline generated more than 50 events, stopping for safety"
                )
                break

        # Log final results
        if final_result:
            total_items = final_result.get("total_count", 0)
            sources = final_result.get("sources", [])
            logger.info(f"📊 FINAL RESULTS: {total_items} items processed")
            logger.info(f"📊 SOURCES: {', '.join(sources) if sources else 'None'}")
        else:
            logger.warning("⚠️  No final result received from pipeline")

        total_time = time.time() - start_time
        end_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        logger.info("=" * 80)
        logger.info(f"✅ SUCCESS: Pipeline cron job completed successfully")
        logger.info(f"⏱️  Total execution time: {total_time:.2f}s")
        logger.info(f"🏁 Job ended: {end_timestamp}")
        logger.info("=" * 80)

    except Exception as e:
        total_time = time.time() - start_time
        end_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        logger.error("=" * 80)
        logger.error(f"❌ FAILURE: Pipeline cron job failed after {total_time:.2f}s")
        logger.error(f"❌ Error: {e}")
        logger.error(f"🏁 Job ended: {end_timestamp}")
        logger.error("=" * 80)
        logger.error("Full error traceback:", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
