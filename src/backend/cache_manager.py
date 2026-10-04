#!/usr/bin/env python3
"""
Cache Management Utility

This script provides management functionality for the summary cache database.
"""

import argparse
import asyncio
import sys
from datetime import datetime, timedelta

import numpy as np

from .config import config
from .constants import INTERESTED_KEYWORDS
from .database import db_manager, Source
from .search import _get_embedding, semantic_search_with_scores


def _local_user_id() -> str:
    """Id of the local user that owns the bookmarks."""
    return db_manager.get_or_create_local_user(config.local_user_email)


def print_cache_stats(cache_type: str = "all"):
    """Print cache statistics."""
    try:
        if cache_type in ["all", "summary"]:
            stats = db_manager.get_summary_cache_stats()
            print("=== Summary Cache Statistics ===")
            print(f"Total summaries: {stats['total_summaries']}")
            print(f"Recent summaries (7 days): {stats['recent_summaries_7_days']}")

            if stats["total_summaries"] > 0:
                avg_per_day = stats["recent_summaries_7_days"] / 7
                print(f"Average per day: {avg_per_day:.1f}")

        if cache_type in ["all", "embedding"]:
            embedding_stats = db_manager.get_embedding_cache_stats()
            print("\n=== Embedding Cache Statistics ===")
            print(f"Total embeddings: {embedding_stats['total_embeddings']}")
            print(
                f"Recent embeddings (7 days): {embedding_stats['recent_embeddings_7_days']}"
            )
            print(f"Models used: {', '.join(embedding_stats['models_used'])}")

            if embedding_stats["total_embeddings"] > 0:
                avg_per_day = embedding_stats["recent_embeddings_7_days"] / 7
                print(f"Average per day: {avg_per_day:.1f}")

        if cache_type in ["all", "bookmark"]:
            bookmark_stats = db_manager.get_bookmark_cache_stats(_local_user_id())
            print("\n=== Bookmark Cache Statistics ===")
            print(f"Total bookmarks: {bookmark_stats['total_bookmarks']}")
            print(
                f"Recent bookmarks (7 days): {bookmark_stats['recent_bookmarks_7_days']}"
            )

            if bookmark_stats["total_bookmarks"] > 0:
                avg_per_day = bookmark_stats["recent_bookmarks_7_days"] / 7
                print(f"Average per day: {avg_per_day:.1f}")

    except Exception as e:
        print(f"Error getting stats: {e}")


def print_recent_entries(cache_type: str, days: int = 7):
    """Print recent cache entries."""
    try:
        start_date = datetime.now() - timedelta(days=days)

        if cache_type == "summary":
            entries = db_manager.get_summaries_by_date(start_date)
            print(f"=== Recent Summaries (Last {days} days) ===")
            for entry in entries:
                print(f"\nDate: {entry['created_at']}")
                print(f"URL: {entry['url']}")
                print(f"Summary: {entry['summary'][:100]}...")

        elif cache_type == "embedding":
            entries = db_manager.get_embeddings_by_date(start_date)
            print(f"=== Recent Embeddings (Last {days} days) ===")
            for entry in entries:
                print(f"\nDate: {entry['created_at']}")
                print(f"Model: {entry['model_name']}")
                print(f"Text: {entry['text']}")
                print(f"Hash: {entry['text_hash'][:16]}...")

        elif cache_type == "bookmark":
            entries = db_manager.get_bookmarks_by_date(_local_user_id(), start_date)
            print(f"=== Recent Bookmarks (Last {days} days) ===")
            for entry in entries:
                print(f"\nDate: {entry['bookmarked_at']}")
                print(f"Title: {entry['title']}")
                print(f"Link: {entry['link']}")
                print(f"Source: {entry['source_tag']}")
                if entry["summary"]:
                    print(f"Summary: {entry['summary'][:100]}...")

    except Exception as e:
        print(f"Error getting recent {cache_type} entries: {e}")


def search_cache(cache_type: str, query: str, limit: int = 5):
    """Search cache entries containing query."""
    try:
        if cache_type == "summary":
            results = db_manager.search_summaries(query, limit)
            print(f"=== Summary Search Results for '{query}' ===")
            if not results:
                print("No results found.")
                return
            for result in results:
                print(f"\nURL: {result['url']}")
                print(f"Date: {result['created_at']}")
                print(f"Summary: {result['summary']}")
                print("-" * 80)

        elif cache_type == "embedding":
            results = db_manager.search_embeddings(query, limit)
            print(f"=== Embedding Search Results for '{query}' ===")
            if not results:
                print("No results found.")
                return
            for result in results:
                print(f"\nDate: {result['created_at']}")
                print(f"Model: {result['model_name']}")
                print(f"Text: {result['text']}")
                print(f"Hash: {result['text_hash'][:16]}...")
                print("-" * 80)

        elif cache_type == "bookmark":
            results = db_manager.search_bookmarks(_local_user_id(), query, limit)
            print(f"=== Bookmark Search Results for '{query}' ===")
            if not results:
                print("No results found.")
                return
            for result in results:
                print(f"\nTitle: {result['title']}")
                print(f"Link: {result['link']}")
                print(f"Date: {result['bookmarked_at']}")
                print(f"Source: {result['source_tag']}")
                if result["summary"]:
                    print(f"Summary: {result['summary'][:100]}...")
                print("-" * 80)

    except Exception as e:
        print(f"Error searching {cache_type} cache: {e}")


def cleanup_cache(cache_type: str, days: int = 30):
    """Clean up old cache entries. Bookmarks are only removed when asked for by name."""
    try:
        if cache_type == "summary":
            result = db_manager.cleanup_summaries_and_embeddings(days)
            print(
                f"Cleaned up {result['summaries_cleaned']} summaries and {result['embeddings_cleaned']} corresponding embeddings older than {days} days"
            )

        elif cache_type == "embedding":
            deleted_count = db_manager.cleanup_embeddings(days)
            print(f"Cleaned up {deleted_count} embeddings older than {days} days")

        elif cache_type == "bookmark":
            days = max(days, 90)  # Default minimum 90 days for bookmarks
            deleted_count = db_manager.cleanup_bookmarks(days)
            print(f"Cleaned up {deleted_count} bookmarks older than {days} days")

        elif cache_type == "all":
            summary_result = db_manager.cleanup_summaries_and_embeddings(days)
            remaining_embedding_count = db_manager.cleanup_embeddings(days)
            total_embeddings = (
                summary_result["embeddings_cleaned"] + remaining_embedding_count
            )
            print(
                f"Cleaned up {summary_result['summaries_cleaned']} summaries, {total_embeddings} embeddings ({summary_result['embeddings_cleaned']} linked to summaries + {remaining_embedding_count} others)"
            )

    except Exception as e:
        print(f"Error cleaning up {cache_type} cache: {e}")


def reembed_summaries(days: int = 7):
    """Embed recent summaries with the current embedding model."""
    start_date = datetime.now() - timedelta(days=days)
    entries = db_manager.get_summaries_by_date(start_date)
    print(
        f"=== Embedding {len(entries)} summaries (last {days} days) with {config.llm_embedding_model} ==="
    )

    async def embed_all() -> int:
        embedded = 0
        for entry in entries:
            embedding = await _get_embedding(entry["summary"])
            if len(embedding) > 0:
                embedded += 1
        return embedded

    embedded = asyncio.run(embed_all())
    print(f"Embedded {embedded} of {len(entries)} summaries")
    if embedded < len(entries):
        sys.exit(1)


def calibrate_thresholds(days: int = 7):
    """Print how similar recent sources are to the default topics, to choose thresholds."""
    from .pipeline import _convert_db_to_schemas

    cutoff_date = datetime.now() - timedelta(days=days)
    with db_manager.get_session() as session:
        db_sources = (
            session.query(Source).filter(Source.created_at >= cutoff_date).all()
        )
        sources, _ = _convert_db_to_schemas(db_sources)

    groups = {"research": [], "industry": []}
    for source in sources:
        is_research = bool(source.tags) and (source.tags[0] or "").lower() == "research"
        groups["research" if is_research else "industry"].append(source)

    thresholds = {
        "research": config.research_threshold,
        "industry": config.industry_threshold,
    }
    print(
        f"=== Similarity to {INTERESTED_KEYWORDS} with {config.llm_embedding_model} (last {days} days) ==="
    )
    for name, group in groups.items():
        matches = asyncio.run(
            semantic_search_with_scores(group, INTERESTED_KEYWORDS, threshold=None)
        )
        scores = [score for _, score, _ in matches]
        print(
            f"\n--- {name}: {len(scores)} sources scored, current threshold {thresholds[name]} ---"
        )
        if not scores:
            continue

        print(
            "Percentiles: "
            + ", ".join(
                f"p{p}={np.percentile(scores, p):.3f}" for p in (50, 75, 90, 95, 99)
            )
        )
        for cutoff in np.arange(0.30, 0.75, 0.05):
            above = sum(score > cutoff for score in scores)
            print(f"  above {cutoff:.2f}: {above} sources")
        # Titles ranked around the cutoff show where results stop being on topic
        threshold = thresholds[name]
        threshold_shown = False
        print("Ranked titles:")
        for source, score, _ in matches:
            if score < threshold - 0.05:
                break
            if not threshold_shown and score <= threshold:
                print(f"  ----- current threshold {threshold} -----")
                threshold_shown = True
            print(f"  {score:.3f}  {' '.join(source.title.split())[:80]}")


def main():
    parser = argparse.ArgumentParser(description="Cache Management Utility")
    parser.add_argument(
        "command",
        choices=[
            "stats",
            "recent",
            "search",
            "cleanup",
            "init",
            "reembed",
            "calibrate",
        ],
        help="Command to execute",
    )

    parser.add_argument(
        "--cache-type",
        choices=["summary", "embedding", "bookmark", "all"],
        default="all",
        help="Cache type to operate on (cleanup with 'all' leaves bookmarks alone)",
    )

    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="Number of days (for recent/cleanup/reembed/calibrate commands)",
    )
    parser.add_argument("--query", type=str, help="Search query (for search command)")
    parser.add_argument(
        "--limit", type=int, default=5, help="Limit results (for search command)"
    )

    args = parser.parse_args()

    if args.command == "init":
        try:
            db_manager.create_tables()
            print("Database initialized successfully")
        except Exception as e:
            print(f"Database initialization failed: {e}")
            sys.exit(1)
    else:
        # All other commands require the database to be initialized.
        # This is implicitly handled by the db_manager instance, but an explicit check
        # could be added here if necessary.
        pass

    if args.command == "stats":
        print_cache_stats(args.cache_type)

    elif args.command == "recent":
        if args.cache_type == "all":
            print(
                "Error: --cache-type must be specific (summary, embedding, or bookmark) for recent command"
            )
            sys.exit(1)
        print_recent_entries(args.cache_type, args.days)

    elif args.command == "search":
        if not args.query:
            print("Error: --query is required for search command")
            sys.exit(1)
        if args.cache_type == "all":
            print(
                "Error: --cache-type must be specific (summary, embedding, or bookmark) for search command"
            )
            sys.exit(1)
        search_cache(args.cache_type, args.query, args.limit)

    elif args.command == "cleanup":
        cleanup_cache(args.cache_type, args.days)

    elif args.command == "reembed":
        reembed_summaries(args.days)

    elif args.command == "calibrate":
        calibrate_thresholds(args.days)


if __name__ == "__main__":
    main()
