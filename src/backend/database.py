import os
from datetime import datetime
from typing import Optional, List

from sqlalchemy import create_engine, Column, String, DateTime, Text, Integer, JSON
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
    
    def close(self):
        """Close database connection"""
        self.engine.dispose()

# Global database manager instance
db_manager = DatabaseManager()