#!/usr/bin/env python3
"""
Cache Management Utility

This script provides management functionality for the summary cache database.
"""

import argparse
import sys
from datetime import datetime, timedelta
from typing import Dict, Any

from .db_cache import (
    get_summaries_by_date_range,
    cleanup_old_summaries,
    get_cache_stats,
    search_summaries,
    initialize_database
)
from .database import db_manager
from .logger import logger


def print_cache_stats():
    """Print cache statistics."""
    try:
        stats = get_cache_stats()
        print("=== Summary Cache Statistics ===")
        print(f"Total summaries: {stats['total_summaries']}")
        print(f"Recent summaries (7 days): {stats['recent_summaries_7_days']}")
        
        # Calculate storage info
        if stats['total_summaries'] > 0:
            avg_per_day = stats['recent_summaries_7_days'] / 7
            print(f"Average per day: {avg_per_day:.1f}")
        
        # Embedding cache stats
        embedding_stats = db_manager.get_embedding_cache_stats()
        print("\n=== Embedding Cache Statistics ===")
        print(f"Total embeddings: {embedding_stats['total_embeddings']}")
        print(f"Models used: {', '.join(embedding_stats['models_used'])}")
            
    except Exception as e:
        print(f"Error getting stats: {e}")


def print_recent_summaries(days: int = 7):
    """Print recent summaries."""
    try:
        start_date = datetime.now() - timedelta(days=days)
        summaries = get_summaries_by_date_range(start_date)
        
        print(f"=== Recent Summaries (Last {days} days) ===")
        for summary in summaries:
            print(f"\nDate: {summary['created_at']}")
            print(f"URL: {summary['url']}")
            print(f"Summary: {summary['summary'][:100]}...")
            
    except Exception as e:
        print(f"Error getting recent summaries: {e}")


def search_cache(query: str, limit: int = 5):
    """Search cache for summaries containing query."""
    try:
        results = search_summaries(query, limit)
        
        print(f"=== Search Results for '{query}' ===")
        if not results:
            print("No results found.")
            return
            
        for result in results:
            print(f"\nURL: {result['url']}")
            print(f"Date: {result['created_at']}")
            print(f"Summary: {result['summary']}")
            print("-" * 80)
            
    except Exception as e:
        print(f"Error searching cache: {e}")


def cleanup_cache(days: int = 30):
    """Clean up old cache entries."""
    try:
        deleted_count = cleanup_old_summaries(days)
        print(f"Cleaned up {deleted_count} summaries older than {days} days")
        
    except Exception as e:
        print(f"Error cleaning up cache: {e}")


def main():
    parser = argparse.ArgumentParser(description="Cache Management Utility")
    parser.add_argument('command', choices=[
        'stats', 'recent', 'search', 'cleanup', 'init'
    ], help='Command to execute')
    
    parser.add_argument('--days', type=int, default=7, 
                       help='Number of days (for recent/cleanup commands)')
    parser.add_argument('--query', type=str, 
                       help='Search query (for search command)')
    parser.add_argument('--limit', type=int, default=5,
                       help='Limit results (for search command)')
    
    args = parser.parse_args()
    
    # Initialize database for all commands except init
    if args.command != 'init':
        try:
            initialize_database()
        except Exception as e:
            print(f"Database initialization failed: {e}")
            sys.exit(1)
    
    if args.command == 'init':
        try:
            initialize_database()
            print("Database initialized successfully")
        except Exception as e:
            print(f"Database initialization failed: {e}")
            sys.exit(1)
            
    elif args.command == 'stats':
        print_cache_stats()
        
    elif args.command == 'recent':
        print_recent_summaries(args.days)
        
    elif args.command == 'search':
        if not args.query:
            print("Error: --query is required for search command")
            sys.exit(1)
        search_cache(args.query, args.limit)
        
    elif args.command == 'cleanup':
        cleanup_cache(args.days)


if __name__ == "__main__":
    main()
