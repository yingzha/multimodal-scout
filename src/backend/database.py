import os
import hashlib
from datetime import datetime, timedelta
from typing import Optional, List, Dict

from sqlalchemy import create_engine, Column, String, DateTime, Text, Float, desc
from sqlalchemy.types import JSON
import json
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.dialects.postgresql import UUID
import uuid

from .logger import logger

Base = declarative_base()

class SummaryCache(Base):
    __tablename__ = "summary_cache"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    url = Column(String, unique=True, nullable=False, index=True)
    summary = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

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
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

class EmbeddingCache(Base):
    __tablename__ = "embedding_cache"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    text = Column(Text, nullable=False, index=True)
    text_hash = Column(String(64), unique=True, nullable=False, index=True)
    embedding = Column(Text, nullable=False)
    model_name = Column(String, nullable=False, default="gemini-embedding-001")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

class Bookmark(Base):
    __tablename__ = "bookmarks"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String, nullable=False)
    link = Column(String, nullable=False, index=True)
    source_tag = Column(String, nullable=False)
    summary = Column(Text, nullable=True)
    bookmarked_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

class DatabaseManager:
    def __init__(self, database_url: Optional[str] = None):
        if database_url is None:
            database_url = os.getenv('DATABASE_URL', 'postgresql://localhost/multimodal_scout')
        
        self.engine = create_engine(database_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
    
    def get_session(self) -> Session:
        return self.SessionLocal()

    def create_tables(self):
        Base.metadata.create_all(bind=self.engine)

    # --- Summary Cache Methods (from db_cache.py) ---

    def get_summary(self, url: str) -> Optional[str]:
        with self.get_session() as session:
            cache_entry = session.query(SummaryCache).filter(SummaryCache.url == url).first()
            return cache_entry.summary if cache_entry else None

    def add_summary(self, url: str, summary: str) -> None:
        with self.get_session() as session:
            existing_entry = session.query(SummaryCache).filter(SummaryCache.url == url).first()
            if existing_entry:
                existing_entry.summary = summary
                existing_entry.updated_at = datetime.utcnow()
                logger.info(f"Updated existing summary for URL: {url}")
            else:
                new_entry = SummaryCache(url=url, summary=summary, created_at=datetime.utcnow(), updated_at=datetime.utcnow())
                session.add(new_entry)
                logger.info(f"Added new summary for URL: {url}")
            session.commit()

    def get_summaries_by_date(self, start_date: datetime, end_date: Optional[datetime] = None) -> List[Dict[str, str]]:
        with self.get_session() as session:
            query = session.query(SummaryCache).filter(SummaryCache.created_at >= start_date)
            if end_date:
                query = query.filter(SummaryCache.created_at <= end_date)
            results = query.order_by(desc(SummaryCache.created_at)).all()
            return [{"url": e.url, "summary": e.summary, "created_at": e.created_at.isoformat(), "updated_at": e.updated_at.isoformat()} for e in results]

    def cleanup_summaries(self, days_to_keep: int = 30) -> int:
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
        with self.get_session() as session:
            deleted_count = session.query(SummaryCache).filter(SummaryCache.created_at < cutoff_date).delete()
            session.commit()
            logger.info(f"Cleaned up {deleted_count} old summaries (older than {days_to_keep} days)")
            return deleted_count

    def get_summary_cache_stats(self) -> Dict[str, int]:
        with self.get_session() as session:
            total_count = session.query(SummaryCache).count()
            week_ago = datetime.utcnow() - timedelta(days=7)
            recent_count = session.query(SummaryCache).filter(SummaryCache.created_at >= week_ago).count()
            return {"total_summaries": total_count, "recent_summaries_7_days": recent_count}

    def search_summaries(self, query: str, limit: int = 10) -> List[Dict[str, str]]:
        with self.get_session() as session:
            results = session.query(SummaryCache).filter(SummaryCache.summary.ilike(f"%{query}%")).order_by(desc(SummaryCache.created_at)).limit(limit).all()
            return [{"url": e.url, "summary": e.summary, "created_at": e.created_at.isoformat(), "updated_at": e.updated_at.isoformat()} for e in results]

    def get_all_summaries(self) -> Dict[str, str]:
        with self.get_session() as session:
            results = session.query(SummaryCache).all()
            return {entry.url: entry.summary for entry in results}

    def remove_summary(self, url: str) -> bool:
        with self.get_session() as session:
            entry = session.query(SummaryCache).filter(SummaryCache.url == url).first()
            if entry:
                session.delete(entry)
                session.commit()
                logger.info(f"Removed cached summary for URL: {url}")
                return True
            return False

    # --- Source Methods ---

    def save_sources(self, sources: List['SourceSchema']) -> None:
        from .schema import SourceSchema
        with self.get_session() as session:
            for source_schema in sources:
                existing = session.query(Source).filter(Source.link == str(source_schema.link)).first()
                if existing:
                    existing.title = source_schema.title
                    existing.authors = source_schema.authors
                    # ... (update other fields)
                else:
                    new_source = Source(**source_schema.dict())
                    session.add(new_source)
            session.commit()

    # --- Bookmark Methods ---

    def add_bookmark(self, title: str, link: str, source_tag: str, summary: str = None) -> str:
        with self.get_session() as session:
            existing = session.query(Bookmark).filter(Bookmark.link == link).first()
            if existing:
                return str(existing.id)
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

    def is_bookmarked(self, link: str) -> bool:
        with self.get_session() as session:
            return session.query(Bookmark).filter(Bookmark.link == link).first() is not None

    def get_bookmarks(self, limit: int = 100) -> List[Bookmark]:
        with self.get_session() as session:
            return session.query(Bookmark).order_by(Bookmark.bookmarked_at.desc()).limit(limit).all()

    # --- Embedding Cache Methods ---

    def get_embedding_from_cache(self, text_hash: str) -> Optional[List[float]]:
        with self.get_session() as session:
            cached = session.query(EmbeddingCache).filter(EmbeddingCache.text_hash == text_hash).first()
            if cached:
                return json.loads(cached.embedding)

    def add_embedding_to_cache(self, text: str, text_hash: str, embedding: List[float], model_name: str) -> None:
        with self.get_session() as session:
            existing = session.query(EmbeddingCache).filter(EmbeddingCache.text_hash == text_hash).first()
            if not existing:
                new_cache = EmbeddingCache(text=text, text_hash=text_hash, embedding=json.dumps(embedding), model_name=model_name)
                session.add(new_cache)
                session.commit()

    def get_embedding_cache_stats(self) -> dict:
        with self.get_session() as session:
            total_embeddings = session.query(EmbeddingCache).count()
            models_used = session.query(EmbeddingCache.model_name).distinct().all()
            return {'total_embeddings': total_embeddings, 'models_used': [m[0] for m in models_used]}

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
        return self.remove_summary(url)

    def invalidate_embedding_cache(self, text_hash: str) -> bool:
        with self.get_session() as session:
            embedding = session.query(EmbeddingCache).filter(EmbeddingCache.text_hash == text_hash).first()
            if embedding:
                session.delete(embedding)
                session.commit()
                return True
            return False

    def invalidate_non_english_summaries(self) -> int:
        from .utils import _is_non_english_summary
        
        cached_summaries = self.get_all_summaries()
        removed_count = 0
        for url, summary in cached_summaries.items():
            if _is_non_english_summary(summary):
                if self.invalidate_summary_cache(url):
                    removed_count += 1
                    logger.info(f"Removed non-English summary for: {url}")
                    text_hash = self._get_text_hash(summary)
                    if self.invalidate_embedding_cache(text_hash):
                        logger.info(f"Removed associated embedding for: {url}")
        return removed_count

    def close(self):
        self.engine.dispose()

# Global database manager instance
db_manager = DatabaseManager()
