from datetime import datetime, timedelta
from typing import Dict, Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_

from database import db_manager, SummaryCache
from logger import logger


def get_db_session() -> Session:
    """Get database session"""
    return db_manager.get_session()


def get_summary_from_db(url: str) -> Optional[str]:
    """Retrieve a summary for a given URL from the database."""
    with get_db_session() as session:
        cache_entry = session.query(SummaryCache).filter(SummaryCache.url == url).first()
        return cache_entry.summary if cache_entry else None


def add_summary_to_db(url: str, summary: str) -> None:
    """Add or update a summary in the database."""
    with get_db_session() as session:
        existing_entry = session.query(SummaryCache).filter(SummaryCache.url == url).first()
        
        if existing_entry:
            existing_entry.summary = summary
            existing_entry.updated_at = datetime.utcnow()
            logger.info(f"Updated existing summary for URL: {url}")
        else:
            new_entry = SummaryCache(
                url=url,
                summary=summary,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            session.add(new_entry)
            logger.info(f"Added new summary for URL: {url}")
        
        session.commit()


def get_summaries_by_date_range(
    start_date: datetime, 
    end_date: Optional[datetime] = None
) -> List[Dict[str, str]]:
    """Get summaries created within a date range."""
    with get_db_session() as session:
        query = session.query(SummaryCache).filter(SummaryCache.created_at >= start_date)
        
        if end_date:
            query = query.filter(SummaryCache.created_at <= end_date)
        
        results = query.order_by(desc(SummaryCache.created_at)).all()
        
        return [
            {
                "url": entry.url,
                "summary": entry.summary,
                "created_at": entry.created_at.isoformat(),
                "updated_at": entry.updated_at.isoformat()
            }
            for entry in results
        ]


def cleanup_old_summaries(days_to_keep: int = 30) -> int:
    """Remove summaries older than specified days. Returns count of deleted records."""
    cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
    
    with get_db_session() as session:
        deleted_count = session.query(SummaryCache).filter(
            SummaryCache.created_at < cutoff_date
        ).delete()
        
        session.commit()
        logger.info(f"Cleaned up {deleted_count} old summaries (older than {days_to_keep} days)")
        
        return deleted_count


def get_cache_stats() -> Dict[str, int]:
    """Get cache statistics."""
    with get_db_session() as session:
        total_count = session.query(SummaryCache).count()
        
        week_ago = datetime.utcnow() - timedelta(days=7)
        recent_count = session.query(SummaryCache).filter(
            SummaryCache.created_at >= week_ago
        ).count()
        
        return {
            "total_summaries": total_count,
            "recent_summaries_7_days": recent_count
        }


def search_summaries(query: str, limit: int = 10) -> List[Dict[str, str]]:
    """Search summaries by content. Basic text search."""
    with get_db_session() as session:
        results = session.query(SummaryCache).filter(
            SummaryCache.summary.ilike(f"%{query}%")
        ).order_by(desc(SummaryCache.created_at)).limit(limit).all()
        
        return [
            {
                "url": entry.url,
                "summary": entry.summary,
                "created_at": entry.created_at.isoformat(),
                "updated_at": entry.updated_at.isoformat()
            }
            for entry in results
        ]


def initialize_database():
    """Create database tables if they don't exist."""
    try:
        db_manager.create_tables()
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        raise