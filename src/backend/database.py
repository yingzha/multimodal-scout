import os
import hashlib
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from sqlalchemy import (
    create_engine,
    Column,
    String,
    DateTime,
    Text,
    Float,
    Boolean,
    desc,
    ForeignKey,
)
from sqlalchemy.types import JSON, TypeDecorator
import json
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.dialects.postgresql import UUID
import uuid
import secrets

from .logger import logger


class EmbeddingArrayType(TypeDecorator):
    """Custom type to handle embedding arrays for both PostgreSQL and SQLite."""

    impl = Text
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(ARRAY(Float))
        else:
            return dialect.type_descriptor(Text())

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if dialect.name == "postgresql":
            return value  # PostgreSQL handles lists directly
        else:
            return json.dumps(value)  # SQLite stores as JSON string

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        if dialect.name == "postgresql":
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
    updated_at = Column(
        DateTime, default=datetime.now, onupdate=datetime.now, nullable=False
    )


class SeenCard(Base):
    __tablename__ = "seen_cards"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(String, nullable=False, index=True)  # Browser session ID
    card_link = Column(String, nullable=False, index=True)  # Link to the card
    seen_at = Column(DateTime, default=datetime.now, nullable=False, index=True)

    __table_args__ = {"schema": None}  # Use default schema


class EmbeddingCache(Base):
    __tablename__ = "embedding_cache"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    text = Column(Text, nullable=False, index=True)
    text_hash = Column(String(64), unique=True, nullable=False, index=True)
    embedding = Column(EmbeddingArrayType(), nullable=False)
    model_name = Column(String, nullable=False, default="gemini-embedding-001")
    created_at = Column(DateTime, default=datetime.now, nullable=False, index=True)


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False, index=True)
    username = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.now, nullable=False, index=True)
    last_login = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)


class UserSession(Base):
    __tablename__ = "user_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    session_token = Column(String, unique=True, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    last_accessed = Column(DateTime, default=datetime.now, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)


class Bookmark(Base):
    __tablename__ = "bookmarks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    title = Column(String, nullable=False)
    link = Column(String, nullable=False, index=True)
    source_tag = Column(String, nullable=False)
    summary = Column(Text, nullable=True)
    summary_edited = Column(String, nullable=True)
    bookmarked_at = Column(DateTime, default=datetime.now, nullable=False, index=True)


class DatabaseManager:
    def __init__(self, database_url: Optional[str] = None):
        if database_url is None:
            database_url = os.getenv(
                "DATABASE_URL", "postgresql://localhost/multimodal_scout"
            )

        self.engine = create_engine(database_url)
        self.SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=self.engine
        )

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
            self._processed_sources_cache = set(cache_list[len(cache_list) // 2 :])
            logger.info(
                f"Cache size reduced from {len(cache_list)} to {len(self._processed_sources_cache)}"
            )

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
                    logger.warning(
                        f"Cannot add summary - source not found for URL: {url}"
                    )

            session.commit()
            logger.info(
                f"Batch updated summaries for {updated_count} sources out of {len(url_summary_pairs)} requested"
            )
            return results

    def get_summaries_by_date(
        self, start_date: datetime, end_date: Optional[datetime] = None
    ) -> List[Dict[str, str]]:
        """Get summaries from sources table by date (consolidated approach)."""
        with self.get_session() as session:
            query = session.query(Source).filter(
                Source.created_at >= start_date,
                Source.summary.isnot(None),  # Only sources with summaries
            )
            if end_date:
                query = query.filter(Source.created_at <= end_date)
            results = query.order_by(desc(Source.created_at)).all()
            return [
                {
                    "url": s.link,
                    "summary": s.summary,
                    "created_at": s.created_at.isoformat(),
                    "updated_at": s.updated_at.isoformat(),
                }
                for s in results
            ]

    def cleanup_summaries_and_embeddings(
        self, days_to_keep: int = 30
    ) -> Dict[str, int]:
        """Clear summaries from old sources and their corresponding embeddings."""
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        with self.get_session() as session:
            # First, get summaries that will be cleaned up to find their embeddings
            sources_to_cleanup = (
                session.query(Source)
                .filter(Source.created_at < cutoff_date, Source.summary.isnot(None))
                .all()
            )

            # Collect text hashes for embeddings to be removed
            embedding_hashes_to_remove = set()
            for source in sources_to_cleanup:
                if source.summary and source.summary.strip():
                    text_hash = self._get_text_hash(source.summary)
                    embedding_hashes_to_remove.add(text_hash)

            # Remove corresponding embeddings first
            embedding_deleted_count = 0
            if embedding_hashes_to_remove:
                embedding_deleted_count = (
                    session.query(EmbeddingCache)
                    .filter(EmbeddingCache.text_hash.in_(embedding_hashes_to_remove))
                    .delete(synchronize_session=False)
                )

            # Set summary to NULL for old sources instead of deleting records
            summary_updated_count = (
                session.query(Source)
                .filter(Source.created_at < cutoff_date, Source.summary.isnot(None))
                .update({Source.summary: None, Source.updated_at: datetime.now()})
            )

            session.commit()

            logger.info(
                f"Cleaned up {summary_updated_count} old summaries and {embedding_deleted_count} corresponding embeddings (older than {days_to_keep} days)"
            )

            return {
                "summaries_cleaned": summary_updated_count,
                "embeddings_cleaned": embedding_deleted_count,
            }

    def cleanup_summaries(self, days_to_keep: int = 30) -> int:
        """Legacy method - use cleanup_summaries_and_embeddings() for better consistency."""
        result = self.cleanup_summaries_and_embeddings(days_to_keep)
        return result["summaries_cleaned"]

    def get_summary_cache_stats(self) -> Dict[str, int]:
        """Get summary statistics from sources table (consolidated approach)."""
        with self.get_session() as session:
            total_count = (
                session.query(Source).filter(Source.summary.isnot(None)).count()
            )
            week_ago = datetime.now() - timedelta(days=7)
            recent_count = (
                session.query(Source)
                .filter(Source.created_at >= week_ago, Source.summary.isnot(None))
                .count()
            )
            return {
                "total_summaries": total_count,
                "recent_summaries_7_days": recent_count,
            }

    def search_summaries(self, query: str, limit: int = 10) -> List[Dict[str, str]]:
        """Search summaries in sources table (consolidated approach)."""
        with self.get_session() as session:
            results = (
                session.query(Source)
                .filter(Source.summary.ilike(f"%{query}%"), Source.summary.isnot(None))
                .order_by(desc(Source.created_at))
                .limit(limit)
                .all()
            )
            return [
                {
                    "url": s.link,
                    "summary": s.summary,
                    "created_at": s.created_at.isoformat(),
                    "updated_at": s.updated_at.isoformat(),
                }
                for s in results
            ]

    # --- Source Methods ---
    def save_sources(self, sources: List["SourceSchema"]) -> Dict[str, Any]:
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
            return {
                "new_sources": [],
                "updated_sources": [],
                "skipped_sources": 0,
                "total_processed": 0,
            }

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
            logger.info(
                f"Cache optimization: Skipped {cache_hits} recently processed sources"
            )

        # Step 2: Deduplicate remaining sources by link within this batch
        seen_links = set()
        deduplicated_sources = []
        for source in fresh_sources:
            link_str = str(source.link)
            if link_str not in seen_links:
                seen_links.add(link_str)
                deduplicated_sources.append(source)

        logger.info(
            f"Processing pipeline: {len(sources)} → {len(fresh_sources)} (after cache) → {len(deduplicated_sources)} (after dedup)"
        )

        if not deduplicated_sources:
            return {
                "new_sources": [],
                "updated_sources": [],
                "skipped_sources": cache_hits,
                "total_processed": 0,
            }

        with self.get_session() as session:
            # Step 2: Single batch query to get all existing sources
            all_links = [str(source.link) for source in deduplicated_sources]
            existing_sources = (
                session.query(Source).filter(Source.link.in_(all_links)).all()
            )
            existing_links_map = {source.link: source for source in existing_sources}

            logger.info(
                f"Found {len(existing_sources)} existing sources out of {len(deduplicated_sources)} to process"
            )

            # Step 3: Separate updates and inserts
            sources_to_update = []
            sources_to_insert = []

            for source_schema in deduplicated_sources:
                link_str = str(source_schema.link)
                if link_str in existing_links_map:
                    sources_to_update.append(
                        (source_schema, existing_links_map[link_str])
                    )
                else:
                    sources_to_insert.append(source_schema)

            # Step 4: Batch update existing sources
            for source_schema, existing in sources_to_update:
                existing.title = source_schema.title
                existing.authors = source_schema.authors
                existing.source_link = str(source_schema.source_link)
                # Preserve existing summary if the new one is None/empty
                if source_schema.summary:
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
                        "id": uuid.uuid4(),
                        "title": str(source_schema.title),
                        "authors": source_schema.authors,
                        "link": str(source_schema.link),
                        "source_link": str(source_schema.source_link),
                        "summary": source_schema.summary,
                        "keywords": source_schema.keywords,
                        "tags": source_schema.tags,
                        "date": source_schema.date,
                        "created_at": datetime.now(),
                        "updated_at": datetime.now(),
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
                if source.summary:
                    self._mark_as_processed(str(source.link))

            logger.info(
                f"✅ Successfully processed {len(deduplicated_sources)} sources ({len(sources_to_insert)} new, {len(sources_to_update)} updated)"
            )

            # Return processing statistics
            return {
                "new_sources": [source.link for source in sources_to_insert],
                "updated_sources": [
                    source_schema.link
                    for source_schema, _ in sources_to_update
                    if source_schema.summary
                ],
                "skipped_sources": cache_hits,
                "total_processed": len(deduplicated_sources),
            }

    # --- User Management Methods ---

    def create_user(self, email: str, password: str, username: str) -> str:
        """Create a new user account"""
        with self.get_session() as session:
            # Check if email already exists
            existing_user = session.query(User).filter(User.email == email).first()
            if existing_user:
                raise ValueError("User with this email already exists")

            # Check if username already exists
            existing_username = (
                session.query(User).filter(User.username == username).first()
            )
            if existing_username:
                raise ValueError("User with this username already exists")

            password_hash = self._hash_password(password)
            new_user = User(email=email, username=username, password_hash=password_hash)
            session.add(new_user)
            session.commit()
            logger.info(f"Created new user: {email} ({username})")
            return str(new_user.id)

    def authenticate_user(self, email: str, password: str) -> Optional[str]:
        """Authenticate user and return user_id if successful"""
        with self.get_session() as session:
            user = (
                session.query(User)
                .filter(User.email == email, User.is_active == True)
                .first()
            )

            if user and self._verify_password(password, user.password_hash):
                user.last_login = datetime.now()
                session.commit()
                logger.info(f"User authenticated: {email}")
                return str(user.id)
            return None

    def create_user_session(self, user_id: str) -> str:
        """Create a new session for the user"""
        with self.get_session() as session:
            session_token = secrets.token_urlsafe(32)
            expires_at = datetime.now() + timedelta(days=30)  # 30 day sessions

            new_session = UserSession(
                user_id=user_id, session_token=session_token, expires_at=expires_at
            )
            session.add(new_session)
            session.commit()
            return session_token

    def validate_session(self, session_token: str) -> Optional[str]:
        """Validate session token and return user_id if valid"""
        with self.get_session() as session:
            user_session = (
                session.query(UserSession)
                .filter(
                    UserSession.session_token == session_token,
                    UserSession.is_active == True,
                    UserSession.expires_at > datetime.now(),
                )
                .first()
            )

            if user_session:
                user_session.last_accessed = datetime.now()
                session.commit()
                return str(user_session.user_id)
            return None

    def logout_user(self, session_token: str) -> bool:
        """Logout user by invalidating session"""
        with self.get_session() as session:
            user_session = (
                session.query(UserSession)
                .filter(UserSession.session_token == session_token)
                .first()
            )

            if user_session:
                user_session.is_active = False
                session.commit()
                return True
            return False

    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        with self.get_session() as session:
            return session.query(User).filter(User.id == user_id).first()

    def _hash_password(self, password: str) -> str:
        """Hash password using hashlib (simple implementation for now)"""
        import hashlib
        import os

        salt = os.urandom(32)
        pwdhash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)
        return salt.hex() + pwdhash.hex()

    def _verify_password(self, password: str, password_hash: str) -> bool:
        """Verify password against hash"""
        import hashlib

        salt = bytes.fromhex(password_hash[:64])
        stored_hash = password_hash[64:]
        pwdhash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)
        return pwdhash.hex() == stored_hash

    # --- Bookmark Methods ---

    def add_bookmark(
        self, user_id: str, title: str, link: str, source_tag: str, summary: str = None
    ) -> str:
        with self.get_session() as session:
            existing = (
                session.query(Bookmark)
                .filter(Bookmark.user_id == user_id, Bookmark.link == link)
                .first()
            )
            if existing:
                return str(existing.id)

            new_bookmark = Bookmark(
                user_id=user_id,
                title=title,
                link=link,
                source_tag=source_tag,
                summary=summary,
                summary_edited=None,
            )
            session.add(new_bookmark)
            session.commit()
            return str(new_bookmark.id)

    def remove_bookmark(self, user_id: str, link: str) -> bool:
        with self.get_session() as session:
            bookmark = (
                session.query(Bookmark)
                .filter(Bookmark.user_id == user_id, Bookmark.link == link)
                .first()
            )
            if bookmark:
                session.delete(bookmark)
                session.commit()
                return True
            return False

    def update_bookmark_summary(self, user_id: str, link: str, summary: str) -> bool:
        with self.get_session() as session:
            bookmark = (
                session.query(Bookmark)
                .filter(Bookmark.user_id == user_id, Bookmark.link == link)
                .first()
            )
            if bookmark:
                bookmark.summary_edited = summary
                session.commit()
                return True
            return False

    def is_bookmarked(self, user_id: str, link: str) -> bool:
        with self.get_session() as session:
            return (
                session.query(Bookmark)
                .filter(Bookmark.user_id == user_id, Bookmark.link == link)
                .first()
                is not None
            )

    def get_bookmarks(
        self, user_id: str, limit: int = 100, days_back: Optional[int] = None
    ) -> List[Bookmark]:
        with self.get_session() as session:
            query = session.query(Bookmark).filter(Bookmark.user_id == user_id)

            # Filter by date if days_back is specified
            if days_back is not None:
                cutoff_date = datetime.now() - timedelta(days=days_back)
                query = query.filter(Bookmark.bookmarked_at >= cutoff_date)

            return query.order_by(Bookmark.bookmarked_at.desc()).limit(limit).all()

    def get_bookmark_by_id(self, user_id: str, bookmark_id: str) -> Optional[Bookmark]:
        """Get a bookmark by its ID."""
        try:
            with self.get_session() as session:
                return (
                    session.query(Bookmark)
                    .filter(Bookmark.user_id == user_id, Bookmark.id == bookmark_id)
                    .first()
                )
        except Exception as e:
            logger.error(f"Failed to get bookmark by ID: {e}")
            return None

    def remove_bookmark_by_id(self, user_id: str, bookmark_id: str) -> bool:
        """Remove a bookmark by its ID."""
        try:
            with self.get_session() as session:
                bookmark = (
                    session.query(Bookmark)
                    .filter(Bookmark.user_id == user_id, Bookmark.id == bookmark_id)
                    .first()
                )
                if bookmark:
                    session.delete(bookmark)
                    session.commit()
                    return True
                return False
        except Exception as e:
            logger.error(f"Failed to remove bookmark by ID: {e}")
            return False

    def update_bookmark_summary_by_id(
        self, user_id: str, bookmark_id: str, summary: str
    ) -> bool:
        """Update a bookmark's summary by its ID."""
        try:
            with self.get_session() as session:
                bookmark = (
                    session.query(Bookmark)
                    .filter(Bookmark.user_id == user_id, Bookmark.id == bookmark_id)
                    .first()
                )
                if bookmark:
                    bookmark.summary_edited = summary
                    logger.info(f"Updated edited summary for bookmark {bookmark_id}")
                    session.commit()
                    return True
                return False
        except Exception as e:
            logger.error(f"Failed to update bookmark summary by ID: {e}")
            return False

    def get_bookmarks_by_date(
        self, start_date: datetime, end_date: Optional[datetime] = None
    ) -> List[Dict[str, str]]:
        with self.get_session() as session:
            query = session.query(Bookmark).filter(Bookmark.bookmarked_at >= start_date)
            if end_date:
                query = query.filter(Bookmark.bookmarked_at <= end_date)
            results = query.order_by(desc(Bookmark.bookmarked_at)).all()
            return [
                {
                    "title": b.title,
                    "link": b.link,
                    "source_tag": b.source_tag,
                    "summary": b.summary or "",
                    "summary_edited": getattr(b, "summary_edited", None),
                    "bookmarked_at": b.bookmarked_at.isoformat(),
                }
                for b in results
            ]

    def cleanup_bookmarks(self, days_to_keep: int = 90) -> int:
        """Clean up old bookmarks."""
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        with self.get_session() as session:
            deleted_count = (
                session.query(Bookmark)
                .filter(Bookmark.bookmarked_at < cutoff_date)
                .delete()
            )
            session.commit()
            logger.info(
                f"Cleaned up {deleted_count} old bookmarks (older than {days_to_keep} days)"
            )
            return deleted_count

    def get_bookmark_cache_stats(self) -> Dict[str, int]:
        with self.get_session() as session:
            total_count = session.query(Bookmark).count()
            week_ago = datetime.now() - timedelta(days=7)
            recent_count = (
                session.query(Bookmark)
                .filter(Bookmark.bookmarked_at >= week_ago)
                .count()
            )
            return {
                "total_bookmarks": total_count,
                "recent_bookmarks_7_days": recent_count,
            }

    def search_bookmarks(self, query: str, limit: int = 10) -> List[Dict[str, str]]:
        with self.get_session() as session:
            results = (
                session.query(Bookmark)
                .filter(
                    Bookmark.title.ilike(f"%{query}%")
                    | Bookmark.summary.ilike(f"%{query}%")
                )
                .order_by(desc(Bookmark.bookmarked_at))
                .limit(limit)
                .all()
            )
            return [
                {
                    "title": b.title,
                    "link": b.link,
                    "source_tag": b.source_tag,
                    "summary": b.summary or "",
                    "summary_edited": getattr(b, "summary_edited", None),
                    "bookmarked_at": b.bookmarked_at.isoformat(),
                }
                for b in results
            ]

    # --- Embedding Cache Methods ---

    def get_embedding_from_cache(self, text_hash: str) -> Optional[List[float]]:
        with self.get_session() as session:
            cached = (
                session.query(EmbeddingCache)
                .filter(EmbeddingCache.text_hash == text_hash)
                .first()
            )
            if cached:
                return (
                    cached.embedding
                )  # EmbeddingArrayType handles conversion automatically

    def add_embedding_to_cache(
        self, text: str, text_hash: str, embedding: List[float], model_name: str
    ) -> None:
        with self.get_session() as session:
            existing = (
                session.query(EmbeddingCache)
                .filter(EmbeddingCache.text_hash == text_hash)
                .first()
            )
            if not existing:
                new_cache = EmbeddingCache(
                    text=text,
                    text_hash=text_hash,
                    embedding=embedding,
                    model_name=model_name,
                )  # EmbeddingArrayType handles conversion
                session.add(new_cache)
                session.commit()

    def get_embedding_cache_stats(self) -> dict:
        with self.get_session() as session:
            total_count = session.query(EmbeddingCache).count()
            week_ago = datetime.now() - timedelta(days=7)
            recent_count = (
                session.query(EmbeddingCache)
                .filter(EmbeddingCache.created_at >= week_ago)
                .count()
            )
            models_used = session.query(EmbeddingCache.model_name).distinct().all()
            return {
                "total_embeddings": total_count,
                "recent_embeddings_7_days": recent_count,
                "models_used": [m[0] for m in models_used],
            }

    def get_embeddings_by_date(
        self, start_date: datetime, end_date: Optional[datetime] = None
    ) -> List[Dict[str, str]]:
        with self.get_session() as session:
            query = session.query(EmbeddingCache).filter(
                EmbeddingCache.created_at >= start_date
            )
            if end_date:
                query = query.filter(EmbeddingCache.created_at <= end_date)
            results = query.order_by(desc(EmbeddingCache.created_at)).all()
            return [
                {
                    "text": e.text[:100] + "..." if len(e.text) > 100 else e.text,
                    "text_hash": e.text_hash,
                    "model_name": e.model_name,
                    "created_at": e.created_at.isoformat(),
                }
                for e in results
            ]

    def cleanup_embeddings(self, days_to_keep: int = 30) -> int:
        """Clean up old embedding cache entries."""
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        with self.get_session() as session:
            deleted_count = (
                session.query(EmbeddingCache)
                .filter(EmbeddingCache.created_at < cutoff_date)
                .delete()
            )
            session.commit()
            logger.info(
                f"Cleaned up {deleted_count} old embeddings (older than {days_to_keep} days)"
            )
            return deleted_count

    def search_embeddings(self, query: str, limit: int = 10) -> List[Dict[str, str]]:
        with self.get_session() as session:
            results = (
                session.query(EmbeddingCache)
                .filter(EmbeddingCache.text.ilike(f"%{query}%"))
                .order_by(desc(EmbeddingCache.created_at))
                .limit(limit)
                .all()
            )
            return [
                {
                    "text": e.text[:100] + "..." if len(e.text) > 100 else e.text,
                    "text_hash": e.text_hash,
                    "model_name": e.model_name,
                    "created_at": e.created_at.isoformat(),
                }
                for e in results
            ]

    def _get_text_hash(self, text: str) -> str:
        """Get SHA256 hash of text for caching."""
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def get_embedding_for_text(self, text: str) -> Optional[List[float]]:
        """Gets an embedding for the given text, using the cache if available."""
        text_hash = self._get_text_hash(text)
        return self.get_embedding_from_cache(text_hash)

    def add_embedding_for_text(
        self, text: str, embedding: List[float], model_name: str
    ) -> None:
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
            embedding = (
                session.query(EmbeddingCache)
                .filter(EmbeddingCache.text_hash == text_hash)
                .first()
            )
            if embedding:
                session.delete(embedding)
                session.commit()
                logger.info(f"Removed cached embedding for text hash: {text_hash}")
                return True
            return False

    # --- Simple Card Tracking Methods ---

    def get_new_cards(self, session_id: str, card_links: List[str]) -> List[str]:
        """Get list of card links that are new for this session."""
        if not card_links or not session_id:
            return card_links

        with self.get_session() as session:
            seen_links = (
                session.query(SeenCard.card_link)
                .filter(
                    SeenCard.session_id == session_id,
                    SeenCard.card_link.in_(card_links),
                )
                .all()
            )

            seen_set = {link[0] for link in seen_links}
            new_links = [link for link in card_links if link not in seen_set]

            return new_links

    def mark_cards_seen(self, session_id: str, card_links: List[str]) -> None:
        """Mark cards as seen for this session."""
        if not card_links or not session_id:
            return

        with self.get_session() as session:
            # Check which cards are already seen
            existing_seen = (
                session.query(SeenCard.card_link)
                .filter(
                    SeenCard.session_id == session_id,
                    SeenCard.card_link.in_(card_links),
                )
                .all()
            )

            existing_set = {link[0] for link in existing_seen}
            new_cards_to_mark = [
                link for link in card_links if link not in existing_set
            ]

            # Add new seen cards
            for card_link in new_cards_to_mark:
                seen_card = SeenCard(session_id=session_id, card_link=card_link)
                session.add(seen_card)

            if new_cards_to_mark:
                session.commit()
                logger.info(
                    f"Marked {len(new_cards_to_mark)} new cards as seen for session {session_id}"
                )


# Global database manager instance
db_manager = DatabaseManager()
