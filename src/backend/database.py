import os
import hashlib
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from sqlalchemy import create_engine, Column, String, DateTime, Text, Float, desc
from sqlalchemy.types import JSON, TypeDecorator
import json
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.dialects.postgresql import UUID
import uuid

from .logger import logger


class EmbeddingArrayType(TypeDecorator):
    """Custom type to handle embedding arrays for both PostgreSQL and SQLite."""
    impl = Text
    cache_ok = True
    
    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(ARRAY(Float))
        else:
            return dialect.type_descriptor(Text())
    
    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if dialect.name == 'postgresql':
            return value  # PostgreSQL handles lists directly
        else:
            return json.dumps(value)  # SQLite stores as JSON string
    
    def process_result_value(self, value, dialect):
        if value is None:
            return value
        if dialect.name == 'postgresql':
            return value  # PostgreSQL returns lists directly
        else:
            return json.loads(value)  # SQLite parses JSON string

Base = declarative_base()


class Source(Base):
    __tablename__ = "sources"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String, nullable=False)
    authors = Column(JSON, nullable=False)
    link = Column(String, nullable=False, index=True)
    source_link = Column(String, nullable=False)
    summary = Column(Text, nullable=True)
    keywords = Column(JSON, nullable=True)
    tags = Column(JSON, nullable=False)
    date = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.now, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)

class EmbeddingCache(Base):
    __tablename__ = "embedding_cache"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    text = Column(Text, nullable=False, index=True)
    text_hash = Column(String(64), unique=True, nullable=False, index=True)
    embedding = Column(EmbeddingArrayType(), nullable=False)
    model_name = Column(String, nullable=False, default="gemini-embedding-001")
    created_at = Column(DateTime, default=datetime.now, nullable=False, index=True)

class Bookmark(Base):
    __tablename__ = "bookmarks"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String, nullable=False)
    link = Column(String, nullable=False, index=True)
    source_tag = Column(String, nullable=False)
    summary = Column(Text, nullable=True)
    summary_edited = Column(String, nullable=True)
    bookmarked_at = Column(DateTime, default=datetime.now, nullable=False, index=True)

class DatabaseManager:
    def __init__(self, database_url: Optional[str] = None):
        if database_url is None:
            database_url = os.getenv('DATABASE_URL', 'postgresql://localhost/multimodal_scout')
        
        self.engine = create_engine(database_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
        # In-memory cache to track recently processed sources (by link)
        # This helps avoid reprocessing the same sources across method calls
        self._processed_sources_cache = set()
        self._cache_max_size = 10000  # Limit cache size to prevent memory issues
    
    def get_session(self) -> Session:
        return self.SessionLocal()

    def create_tables(self):
        Base.metadata.create_all(bind=self.engine)
    
    def _manage_cache_size(self):
        """Keep cache size under control to prevent memory issues."""
        if len(self._processed_sources_cache) > self._cache_max_size:
            # Remove half the cache when it gets too large
            # Convert to list, keep the second half (more recent)
            cache_list = list(self._processed_sources_cache)
            self._processed_sources_cache = set(cache_list[len(cache_list)//2:])
            logger.info(f"Cache size reduced from {len(cache_list)} to {len(self._processed_sources_cache)}")
    
    def _is_recently_processed(self, link: str) -> bool:
        """Check if a source was recently processed."""
        return link in self._processed_sources_cache
    
    def _mark_as_processed(self, link: str):
        """Mark a source as recently processed."""
        self._processed_sources_cache.add(link)
        if len(self._processed_sources_cache) % 1000 == 0:  # Check periodically
            self._manage_cache_size()

    def get_summary(self, url: str) -> Optional[str]:
        """Get summary from sources table (consolidated approach)."""
        with self.get_session() as session:
            source = session.query(Source).filter(Source.link == url).first()
            return source.summary if source else None
    
    def get_summaries_batch(self, urls: List[str]) -> Dict[str, str]:
        """Get summaries for multiple URLs in a single query (batch operation)."""
        if not urls:
            return {}
            
        with self.get_session() as session:
            sources = session.query(Source).filter(Source.link.in_(urls)).all()
            return {source.link: source.summary for source in sources if source.summary}

    def add_summary(self, url: str, summary: str) -> None:
        """Add summary to sources table (consolidated approach)."""
        with self.get_session() as session:
            source = session.query(Source).filter(Source.link == url).first()
            if source:
                source.summary = summary
                source.updated_at = datetime.now()
                session.commit()
                logger.info(f"Updated summary for existing source: {url}")
            else:
                logger.warning(f"Cannot add summary - source not found for URL: {url}")
                # Note: We no longer create orphaned summary entries
                # Summaries should only exist for sources that exist in sources table

    def add_summaries_batch(self, url_summary_pairs: Dict[str, str]) -> Dict[str, bool]:
        """Add summaries for multiple URLs in a single transaction (batch operation)."""
        if not url_summary_pairs:
            return {}
            
        with self.get_session() as session:
            urls = list(url_summary_pairs.keys())
            sources = session.query(Source).filter(Source.link.in_(urls)).all()
            
            # Create a mapping of URL to source for quick lookup
            url_to_source = {source.link: source for source in sources}
            results = {}
            updated_count = 0
            
            for url, summary in url_summary_pairs.items():
                if url in url_to_source:
                    source = url_to_source[url]
                    source.summary = summary
                    source.updated_at = datetime.now()
                    results[url] = True
                    updated_count += 1
                else:
                    results[url] = False
                    logger.warning(f"Cannot add summary - source not found for URL: {url}")
            
            session.commit()
            logger.info(f"Batch updated summaries for {updated_count} sources out of {len(url_summary_pairs)} requested")
            return results

    def get_summaries_by_date(self, start_date: datetime, end_date: Optional[datetime] = None) -> List[Dict[str, str]]:
        """Get summaries from sources table by date (consolidated approach)."""
        with self.get_session() as session:
            query = session.query(Source).filter(
                Source.created_at >= start_date,
                Source.summary.isnot(None)  # Only sources with summaries
            )
            if end_date:
                query = query.filter(Source.created_at <= end_date)
            results = query.order_by(desc(Source.created_at)).all()
            return [{"url": s.link, "summary": s.summary, "created_at": s.created_at.isoformat(), "updated_at": s.updated_at.isoformat()} for s in results]

    def cleanup_summaries(self, days_to_keep: int = 30) -> int:
        """Clear summaries from old sources (consolidated approach).""" 
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        with self.get_session() as session:
            # Set summary to NULL for old sources instead of deleting records
            updated_count = session.query(Source).filter(
                Source.created_at < cutoff_date,
                Source.summary.isnot(None)
            ).update({Source.summary: None, Source.updated_at: datetime.now()})
            session.commit()
            logger.info(f"Cleaned up {updated_count} old summaries (older than {days_to_keep} days)")
            return updated_count

    def get_summary_cache_stats(self) -> Dict[str, int]:
        """Get summary statistics from sources table (consolidated approach)."""
        with self.get_session() as session:
            total_count = session.query(Source).filter(Source.summary.isnot(None)).count()
            week_ago = datetime.now() - timedelta(days=7)
            recent_count = session.query(Source).filter(
                Source.created_at >= week_ago,
                Source.summary.isnot(None)
            ).count()
            return {"total_summaries": total_count, "recent_summaries_7_days": recent_count}

    def search_summaries(self, query: str, limit: int = 10) -> List[Dict[str, str]]:
        """Search summaries in sources table (consolidated approach)."""
        with self.get_session() as session:
            results = session.query(Source).filter(
                Source.summary.ilike(f"%{query}%"),
                Source.summary.isnot(None)
            ).order_by(desc(Source.created_at)).limit(limit).all()
            return [{"url": s.link, "summary": s.summary, "created_at": s.created_at.isoformat(), "updated_at": s.updated_at.isoformat()} for s in results]


    # --- Source Methods ---
    def save_sources(self, sources: List['SourceSchema']) -> Dict[str, Any]:
        """
        Optimized batch save with in-memory deduplication and single DB query.
        Performance improvements:
        - Deduplicates sources by link within the batch
        - Single batch query to check existing sources instead of N queries  
        - Separates updates and inserts for better performance
        
        Returns:
            Dict with processing statistics including new_sources list for further processing
        """
        if not sources:
            return {'new_sources': [], 'updated_sources': [], 'skipped_sources': 0, 'total_processed': 0}
            
        from .schema import SourceSchema
        
        # Step 1: Filter out recently processed sources using in-memory cache
        fresh_sources = []
        cache_hits = 0
        for source in sources:
            link_str = str(source.link)
            if not self._is_recently_processed(link_str):
                fresh_sources.append(source)
            else:
                cache_hits += 1
        
        if cache_hits > 0:
            logger.info(f"Cache optimization: Skipped {cache_hits} recently processed sources")
        
        # Step 2: Deduplicate remaining sources by link within this batch
        seen_links = set()
        deduplicated_sources = []
        for source in fresh_sources:
            link_str = str(source.link)
            if link_str not in seen_links:
                seen_links.add(link_str)
                deduplicated_sources.append(source)
        
        logger.info(f"Processing pipeline: {len(sources)} → {len(fresh_sources)} (after cache) → {len(deduplicated_sources)} (after dedup)")
        
        if not deduplicated_sources:
            return {'new_sources': [], 'updated_sources': [], 'skipped_sources': cache_hits, 'total_processed': 0}
            
        with self.get_session() as session:
            # Step 2: Single batch query to get all existing sources
            all_links = [str(source.link) for source in deduplicated_sources]
            existing_sources = session.query(Source).filter(Source.link.in_(all_links)).all()
            existing_links_map = {source.link: source for source in existing_sources}
            
            logger.info(f"Found {len(existing_sources)} existing sources out of {len(deduplicated_sources)} to process")
            
            # Step 3: Separate updates and inserts
            sources_to_update = []
            sources_to_insert = []
            
            for source_schema in deduplicated_sources:
                link_str = str(source_schema.link)
                if link_str in existing_links_map:
                    sources_to_update.append((source_schema, existing_links_map[link_str]))
                else:
                    sources_to_insert.append(source_schema)
            
            # Step 4: Batch update existing sources
            for source_schema, existing in sources_to_update:
                existing.title = source_schema.title
                existing.authors = source_schema.authors
                existing.source_link = str(source_schema.source_link)
                existing.summary = source_schema.summary
                existing.keywords = source_schema.keywords
                existing.tags = source_schema.tags
                existing.date = source_schema.date
                existing.updated_at = datetime.now()
            
            # Step 5: Batch insert new sources
            if sources_to_insert:
                new_sources = []
                for source_schema in sources_to_insert:
                    source_data = {
                        'id': uuid.uuid4(),
                        'title': str(source_schema.title),
                        'authors': source_schema.authors,
                        'link': str(source_schema.link),
                        'source_link': str(source_schema.source_link),
                        'summary': source_schema.summary,
                        'keywords': source_schema.keywords,
                        'tags': source_schema.tags,
                        'date': source_schema.date,
                        'created_at': datetime.now(),
                        'updated_at': datetime.now()
                    }
                    new_sources.append(Source(**source_data))
                
                session.add_all(new_sources)
                logger.info(f"Batch inserting {len(new_sources)} new sources")
            
            if sources_to_update:
                logger.info(f"Batch updating {len(sources_to_update)} existing sources")
                
            # Single commit for all operations
            session.commit()
            
            # Step 6: Mark all processed sources in cache to avoid reprocessing
            for source in deduplicated_sources:
                if source.summary is not None:
                    self._mark_as_processed(str(source.link))
            
            logger.info(f"✅ Successfully processed {len(deduplicated_sources)} sources ({len(sources_to_insert)} new, {len(sources_to_update)} updated)")
            
            # Return processing statistics
            return {
                'new_sources': sources_to_insert,
                'updated_sources': [source_schema for source_schema, _ in sources_to_update],
                'skipped_sources': cache_hits,
                'total_processed': len(deduplicated_sources)
            }

    # --- Bookmark Methods ---

    def add_bookmark(self, title: str, link: str, source_tag: str, summary: str = None) -> str:
        with self.get_session() as session:
            existing = session.query(Bookmark).filter(Bookmark.link == link).first()
            if existing:
                return str(existing.id)
            
            # Handle both old and new schema
            try:
                new_bookmark = Bookmark(title=title, link=link, source_tag=source_tag, summary=summary, summary_edited=None)
            except TypeError:
                # If summary_edited field doesn't exist, create without it
                new_bookmark = Bookmark(title=title, link=link, source_tag=source_tag, summary=summary)
            
            session.add(new_bookmark)
            session.commit()
            return str(new_bookmark.id)

    def remove_bookmark(self, link: str) -> bool:
        with self.get_session() as session:
            bookmark = session.query(Bookmark).filter(Bookmark.link == link).first()
            if bookmark:
                session.delete(bookmark)
                session.commit()
                return True
            return False

    def update_bookmark_summary(self, link: str, summary: str) -> bool:
        with self.get_session() as session:
            bookmark = session.query(Bookmark).filter(Bookmark.link == link).first()
            if bookmark:
                # Handle case where summary_edited column might not exist yet
                try:
                    bookmark.summary_edited = summary
                    session.commit()
                    return True
                except Exception as e:
                    logger.error(f"Failed to update summary_edited field, trying summary field: {e}")
                    # Fallback to updating the summary field if summary_edited doesn't exist
                    bookmark.summary = summary
                    session.commit()
                    return True
            return False

    def is_bookmarked(self, link: str) -> bool:
        with self.get_session() as session:
            return session.query(Bookmark).filter(Bookmark.link == link).first() is not None

    def get_bookmarks(self, limit: int = 100) -> List[Bookmark]:
        with self.get_session() as session:
            return session.query(Bookmark).order_by(Bookmark.bookmarked_at.desc()).limit(limit).all()

    def get_bookmarks_by_date(self, start_date: datetime, end_date: Optional[datetime] = None) -> List[Dict[str, str]]:
        with self.get_session() as session:
            query = session.query(Bookmark).filter(Bookmark.bookmarked_at >= start_date)
            if end_date:
                query = query.filter(Bookmark.bookmarked_at <= end_date)
            results = query.order_by(desc(Bookmark.bookmarked_at)).all()
            return [{
                "title": b.title,
                "link": b.link,
                "source_tag": b.source_tag,
                "summary": b.summary or "",
                "summary_edited": getattr(b, 'summary_edited', None),
                "bookmarked_at": b.bookmarked_at.isoformat()
            } for b in results]

    def cleanup_bookmarks(self, days_to_keep: int = 90) -> int:
        """Clean up old bookmarks."""
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        with self.get_session() as session:
            deleted_count = session.query(Bookmark).filter(Bookmark.bookmarked_at < cutoff_date).delete()
            session.commit()
            logger.info(f"Cleaned up {deleted_count} old bookmarks (older than {days_to_keep} days)")
            return deleted_count

    def get_bookmark_cache_stats(self) -> Dict[str, int]:
        with self.get_session() as session:
            total_count = session.query(Bookmark).count()
            week_ago = datetime.now() - timedelta(days=7)
            recent_count = session.query(Bookmark).filter(Bookmark.bookmarked_at >= week_ago).count()
            return {"total_bookmarks": total_count, "recent_bookmarks_7_days": recent_count}

    def search_bookmarks(self, query: str, limit: int = 10) -> List[Dict[str, str]]:
        with self.get_session() as session:
            results = session.query(Bookmark).filter(
                Bookmark.title.ilike(f"%{query}%") | 
                Bookmark.summary.ilike(f"%{query}%")
            ).order_by(desc(Bookmark.bookmarked_at)).limit(limit).all()
            return [{
                "title": b.title,
                "link": b.link,
                "source_tag": b.source_tag,
                "summary": b.summary or "",
                "summary_edited": getattr(b, 'summary_edited', None),
                "bookmarked_at": b.bookmarked_at.isoformat()
            } for b in results]

    # --- Embedding Cache Methods ---

    def get_embedding_from_cache(self, text_hash: str) -> Optional[List[float]]:
        with self.get_session() as session:
            cached = session.query(EmbeddingCache).filter(EmbeddingCache.text_hash == text_hash).first()
            if cached:
                return cached.embedding  # EmbeddingArrayType handles conversion automatically

    def add_embedding_to_cache(self, text: str, text_hash: str, embedding: List[float], model_name: str) -> None:
        with self.get_session() as session:
            existing = session.query(EmbeddingCache).filter(EmbeddingCache.text_hash == text_hash).first()
            if not existing:
                new_cache = EmbeddingCache(text=text, text_hash=text_hash, embedding=embedding, model_name=model_name)  # EmbeddingArrayType handles conversion
                session.add(new_cache)
                session.commit()

    def get_embedding_cache_stats(self) -> dict:
        with self.get_session() as session:
            total_count = session.query(EmbeddingCache).count()
            week_ago = datetime.now() - timedelta(days=7)
            recent_count = session.query(EmbeddingCache).filter(EmbeddingCache.created_at >= week_ago).count()
            models_used = session.query(EmbeddingCache.model_name).distinct().all()
            return {
                'total_embeddings': total_count, 
                'recent_embeddings_7_days': recent_count,
                'models_used': [m[0] for m in models_used]
            }

    def get_embeddings_by_date(self, start_date: datetime, end_date: Optional[datetime] = None) -> List[Dict[str, str]]:
        with self.get_session() as session:
            query = session.query(EmbeddingCache).filter(EmbeddingCache.created_at >= start_date)
            if end_date:
                query = query.filter(EmbeddingCache.created_at <= end_date)
            results = query.order_by(desc(EmbeddingCache.created_at)).all()
            return [{
                "text": e.text[:100] + "..." if len(e.text) > 100 else e.text,
                "text_hash": e.text_hash,
                "model_name": e.model_name,
                "created_at": e.created_at.isoformat()
            } for e in results]

    def cleanup_embeddings(self, days_to_keep: int = 30) -> int:
        """Clean up old embedding cache entries."""
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        with self.get_session() as session:
            deleted_count = session.query(EmbeddingCache).filter(EmbeddingCache.created_at < cutoff_date).delete()
            session.commit()
            logger.info(f"Cleaned up {deleted_count} old embeddings (older than {days_to_keep} days)")
            return deleted_count

    def search_embeddings(self, query: str, limit: int = 10) -> List[Dict[str, str]]:
        with self.get_session() as session:
            results = session.query(EmbeddingCache).filter(
                EmbeddingCache.text.ilike(f"%{query}%")
            ).order_by(desc(EmbeddingCache.created_at)).limit(limit).all()
            return [{
                "text": e.text[:100] + "..." if len(e.text) > 100 else e.text,
                "text_hash": e.text_hash,
                "model_name": e.model_name,
                "created_at": e.created_at.isoformat()
            } for e in results]

    def _get_text_hash(self, text: str) -> str:
        """Get SHA256 hash of text for caching."""
        return hashlib.sha256(text.encode('utf-8')).hexdigest()

    def get_embedding_for_text(self, text: str) -> Optional[List[float]]:
        """Gets an embedding for the given text, using the cache if available."""
        text_hash = self._get_text_hash(text)
        return self.get_embedding_from_cache(text_hash)

    def add_embedding_for_text(self, text: str, embedding: List[float], model_name: str) -> None:
        """Adds a new text-embedding pair to the cache."""
        text_hash = self._get_text_hash(text)
        self.add_embedding_to_cache(text, text_hash, embedding, model_name)

    # --- Invalidation Methods ---

    def invalidate_summary_cache(self, url: str) -> bool:
        """Clear summary from sources table (consolidated approach)."""
        with self.get_session() as session:
            source = session.query(Source).filter(Source.link == url).first()
            if source and source.summary:
                source.summary = None
                source.updated_at = datetime.now()
                session.commit()
                logger.info(f"Cleared summary for URL: {url}")
                return True
            return False

    def invalidate_embedding_cache(self, text_hash: str) -> bool:
        with self.get_session() as session:
            embedding = session.query(EmbeddingCache).filter(EmbeddingCache.text_hash == text_hash).first()
            if embedding:
                session.delete(embedding)
                session.commit()
                logger.info(f"Removed cached embedding for text hash: {text_hash}")
                return True
            return False


# Global database manager instance
db_manager = DatabaseManager()
