import os
from datetime import datetime
from typing import Optional, List

from sqlalchemy import create_engine, Column, String, DateTime, Text, Integer, JSON, Boolean, Float
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.dialects.postgresql import UUID
import uuid

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
    authors = Column(JSON, nullable=False)  # Store list of authors as JSON
    link = Column(String, nullable=False, index=True)
    source_link = Column(String, nullable=False)
    summary = Column(Text, nullable=True)
    keywords = Column(JSON, nullable=True)  # Store list of keywords as JSON
    tags = Column(JSON, nullable=False)  # Store list of tags as JSON
    date = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

class EmbeddingCache(Base):
    __tablename__ = "embedding_cache"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    text = Column(Text, nullable=False, index=True)  # The text that was embedded
    text_hash = Column(String(64), unique=True, nullable=False, index=True)  # SHA256 hash for fast lookup
    embedding = Column(ARRAY(Float), nullable=False)  # Store embedding as array of floats
    model_name = Column(String, nullable=False, default="gemini-embedding-001")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

class Bookmark(Base):
    __tablename__ = "bookmarks"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String, nullable=False)
    link = Column(String, nullable=False, index=True)
    source_tag = Column(String, nullable=False)  # Research/Industry/etc
    summary = Column(Text, nullable=True)
    bookmarked_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    # For future user support, we can add user_id here
    # user_id = Column(UUID, nullable=True, index=True)

class DatabaseManager:
    def __init__(self, database_url: Optional[str] = None):
        if database_url is None:
            database_url = os.getenv('DATABASE_URL', 'postgresql://localhost/multimodal_scout')
        
        self.engine = create_engine(database_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
    
    def create_tables(self):
        """Create all database tables"""
        Base.metadata.create_all(bind=self.engine)
    
    def get_session(self) -> Session:
        """Get a database session"""
        return self.SessionLocal()
    
    def save_sources(self, sources: List['SourceSchema']) -> None:
        """Save a list of SourceSchema objects to the database, avoiding duplicates"""
        from schema import SourceSchema
        
        session = self.get_session()
        try:
            for source_schema in sources:
                # Check if source already exists (by link)
                existing = session.query(Source).filter(Source.link == str(source_schema.link)).first()
                
                if existing:
                    # Update existing source
                    existing.title = source_schema.title
                    existing.authors = source_schema.authors
                    existing.source_link = str(source_schema.source_link)
                    existing.summary = source_schema.summary
                    existing.keywords = source_schema.keywords
                    existing.tags = source_schema.tags
                    existing.date = source_schema.date
                    existing.updated_at = datetime.utcnow()
                else:
                    # Create new source
                    new_source = Source(
                        title=source_schema.title,
                        authors=source_schema.authors,
                        link=str(source_schema.link),
                        source_link=str(source_schema.source_link),
                        summary=source_schema.summary,
                        keywords=source_schema.keywords,
                        tags=source_schema.tags,
                        date=source_schema.date
                    )
                    session.add(new_source)
            
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def add_bookmark(self, title: str, link: str, source_tag: str, summary: str = None) -> str:
        """Add a bookmark and return its ID"""
        session = self.get_session()
        try:
            # Check if bookmark already exists
            existing = session.query(Bookmark).filter(Bookmark.link == link).first()
            if existing:
                return str(existing.id)  # Return existing bookmark ID
            
            # Create new bookmark
            new_bookmark = Bookmark(
                title=title,
                link=link,
                source_tag=source_tag,
                summary=summary
            )
            session.add(new_bookmark)
            session.commit()
            return str(new_bookmark.id)
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def remove_bookmark(self, link: str) -> bool:
        """Remove a bookmark by link, return True if removed"""
        session = self.get_session()
        try:
            bookmark = session.query(Bookmark).filter(Bookmark.link == link).first()
            if bookmark:
                session.delete(bookmark)
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def is_bookmarked(self, link: str) -> bool:
        """Check if a link is bookmarked"""
        session = self.get_session()
        try:
            exists = session.query(Bookmark).filter(Bookmark.link == link).first() is not None
            return exists
        except Exception as e:
            raise e
        finally:
            session.close()
    
    def get_bookmarks(self, limit: int = 100) -> List[Bookmark]:
        """Get all bookmarks, ordered by most recently bookmarked"""
        session = self.get_session()
        try:
            bookmarks = session.query(Bookmark).order_by(Bookmark.bookmarked_at.desc()).limit(limit).all()
            return bookmarks
        except Exception as e:
            raise e
        finally:
            session.close()
    
    def get_embedding_from_cache(self, text_hash: str) -> Optional[List[float]]:
        """Get cached embedding by text hash"""
        session = self.get_session()
        try:
            cached = session.query(EmbeddingCache).filter(EmbeddingCache.text_hash == text_hash).first()
            if cached:
                return cached.embedding
            return None
        except Exception as e:
            raise e
        finally:
            session.close()
    
    def add_embedding_to_cache(self, text: str, text_hash: str, embedding: List[float], model_name: str = "gemini-embedding-001") -> None:
        """Add embedding to cache"""
        session = self.get_session()
        try:
            # Check if already exists
            existing = session.query(EmbeddingCache).filter(EmbeddingCache.text_hash == text_hash).first()
            if existing:
                return  # Already cached
            
            # Create new cache entry
            new_cache = EmbeddingCache(
                text=text,
                text_hash=text_hash,
                embedding=embedding,
                model_name=model_name
            )
            session.add(new_cache)
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def get_embedding_cache_stats(self) -> dict:
        """Get embedding cache statistics"""
        session = self.get_session()
        try:
            total_embeddings = session.query(EmbeddingCache).count()
            models_used = session.query(EmbeddingCache.model_name).distinct().all()
            
            return {
                'total_embeddings': total_embeddings,
                'models_used': [model[0] for model in models_used]
            }
        except Exception as e:
            raise e
        finally:
            session.close()

    def close(self):
        """Close database connection"""
        self.engine.dispose()

# Global database manager instance
db_manager = DatabaseManager()