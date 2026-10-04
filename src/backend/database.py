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
    Integer,
    desc,
    ForeignKey,
    func,
    Computed,
)
from sqlalchemy.types import JSON
from sqlalchemy.dialects.postgresql import ARRAY, TSVECTOR
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.dialects.postgresql import UUID
import uuid
from .config import config
from .logger import logger
from .cache import source_processing_cache
from .schema import SourceSchema

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
    summary_tsvector = Column(
        TSVECTOR,
        Computed("to_tsvector('english', COALESCE(summary, ''))"),
        nullable=True,
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
    embedding = Column(ARRAY(Float), nullable=False)
    model_name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.now, nullable=False, index=True)


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.now, nullable=False, index=True)
    custom_topics = Column(JSON, nullable=True, default=lambda: [])


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


class CommentInsight(Base):
    __tablename__ = "comment_insights"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id = Column(
        UUID(as_uuid=True), ForeignKey("sources.id"), nullable=False, index=True
    )
    link = Column(
        String, nullable=False, index=True
    )  # Same as sources.link for HN posts
    title = Column(String, nullable=False)
    comment_count = Column(Integer, nullable=False)  # Total number of comments
    insights = Column(Text, nullable=True)  # AI-generated insights in bullet points
    generated_at = Column(DateTime, default=datetime.now, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.now, onupdate=datetime.now, nullable=False
    )


class DatabaseManager:
    def __init__(self, database_url: Optional[str] = None):
        if database_url is None:
            database_url = config.database_url

        self._is_test_environment = bool(os.getenv("PYTEST_CURRENT_TEST"))

        self.engine = create_engine(
            database_url,
            pool_size=5,
            max_overflow=5,
            pool_recycle=1800,
            pool_pre_ping=True,
        )
        self.SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=self.engine
        )

        # Use unified source processing cache
        self._source_cache = source_processing_cache

    def get_session(self) -> Session:
        return self.SessionLocal()

    def create_tables(self):
        Base.metadata.create_all(bind=self.engine)

    def add_summaries(self, url_summary_pairs: Dict[str, str]) -> Dict[str, bool]:
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
            sources_query = session.query(Source).filter(
                Source.created_at < cutoff_date, Source.summary.isnot(None)
            )

            if self._is_test_environment:
                sources_query = sources_query.filter(Source.link.like("http://test%"))

            sources_to_cleanup = sources_query.all()

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
            summary_filters = [
                Source.created_at < cutoff_date,
                Source.summary.isnot(None),
            ]
            if self._is_test_environment:
                summary_filters.append(Source.link.like("http://test%"))

            summary_updated_count = (
                session.query(Source)
                .filter(*summary_filters)
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
        """Search summaries using PostgreSQL full-text search with GIN index."""
        with self.get_session() as session:
            # Sanitize input: only allow alphanumeric, spaces, hyphens, and underscores
            # Remove potential SQL injection characters
            sanitized_query = "".join(
                c for c in query if c.isalnum() or c.isspace() or c in "-_"
            ).strip()

            if not sanitized_query:
                logger.warning(
                    f"Query sanitization resulted in empty string: '{query}'"
                )
                return []

            # Format query for PostgreSQL full-text search
            # Replace spaces with & for AND operation
            formatted_query = " & ".join(
                word.strip() for word in sanitized_query.split() if word.strip()
            )

            if not formatted_query:
                return []

            try:
                # Use parameterized queries to prevent SQL injection
                results = (
                    session.query(Source)
                    .filter(
                        Source.summary.isnot(None),
                        Source.summary_tsvector.op("@@")(
                            func.to_tsquery("english", formatted_query)
                        ),
                    )
                    .order_by(
                        func.ts_rank(
                            Source.summary_tsvector,
                            func.to_tsquery("english", formatted_query),
                        ).desc()
                    )
                    .limit(limit)
                    .all()
                )
            except Exception as e:
                logger.warning(
                    f"Full-text search failed for sanitized query '{sanitized_query}': {e}. Falling back to ILIKE."
                )
                # Fallback with parameterized query to prevent SQL injection
                # SQLAlchemy automatically handles parameterization for .ilike()
                results = (
                    session.query(Source)
                    .filter(
                        Source.summary.ilike(f"%{sanitized_query}%"),
                        Source.summary.isnot(None),
                    )
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

    def _get_source_priority(self, link: str) -> int:
        """Return priority for source (higher = keep). HN sources take priority."""
        if "news.ycombinator.com" in link.lower():
            return 10  # Highest priority (HN has discussion value)
        return 1  # Default priority

    def _get_canonical_url(self, source: "SourceSchema") -> str:
        """Get canonical URL for deduplication (the actual article URL)."""
        return str(source.source_link)

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

        # Step 1: Filter out recently processed sources using in-memory cache
        # Use canonical URL (source_link) for cache to prevent cross-source duplicates
        fresh_sources = []
        cache_hits = 0
        for source in sources:
            canonical_url = self._get_canonical_url(source)
            if not self._source_cache.is_recently_processed(canonical_url):
                fresh_sources.append(source)
            else:
                cache_hits += 1

        if cache_hits > 0:
            logger.info(
                f"Cache optimization: Skipped {cache_hits} recently processed sources"
            )

        # Step 2: Deduplicate by canonical URL, keeping highest priority source
        # This prevents duplicates when same article comes from HN and engineering blogs
        seen_canonical: Dict[str, "SourceSchema"] = {}
        for source in fresh_sources:
            canonical_url = self._get_canonical_url(source)
            if canonical_url not in seen_canonical:
                seen_canonical[canonical_url] = source
            else:
                # Keep higher priority source (HN over engineering blogs)
                existing_priority = self._get_source_priority(
                    str(seen_canonical[canonical_url].link)
                )
                new_priority = self._get_source_priority(str(source.link))
                if new_priority > existing_priority:
                    seen_canonical[canonical_url] = source
        deduplicated_sources = list(seen_canonical.values())

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
            # Step 3: Query existing sources by BOTH link AND source_link (canonical URL)
            # This catches cross-source duplicates (same article from HN and eng blogs)
            all_links = [str(s.link) for s in deduplicated_sources]
            all_canonical = [self._get_canonical_url(s) for s in deduplicated_sources]

            existing_by_link = (
                session.query(Source).filter(Source.link.in_(all_links)).all()
            )
            existing_by_canonical = (
                session.query(Source)
                .filter(Source.source_link.in_(all_canonical))
                .all()
            )

            existing_links_map = {s.link: s for s in existing_by_link}
            existing_canonical_map = {s.source_link: s for s in existing_by_canonical}

            logger.info(
                f"Found {len(existing_by_link)} by link, {len(existing_by_canonical)} by canonical out of {len(deduplicated_sources)} to process"
            )

            # Step 4: Separate updates and inserts with priority logic
            sources_to_update = []
            sources_to_insert = []
            sources_skipped_lower_priority = 0

            for source_schema in deduplicated_sources:
                link_str = str(source_schema.link)
                canonical_str = self._get_canonical_url(source_schema)

                # Check exact link match first (same source type)
                if link_str in existing_links_map:
                    sources_to_update.append(
                        (source_schema, existing_links_map[link_str])
                    )
                    continue

                # Check canonical URL match (cross-source duplicate)
                if canonical_str in existing_canonical_map:
                    existing = existing_canonical_map[canonical_str]
                    new_priority = self._get_source_priority(link_str)
                    existing_priority = self._get_source_priority(existing.link)

                    if new_priority > existing_priority:
                        # New source is higher priority - update existing record
                        sources_to_update.append((source_schema, existing))
                    else:
                        # Skip - existing has higher or equal priority
                        sources_skipped_lower_priority += 1
                    continue

                sources_to_insert.append(source_schema)

            if sources_skipped_lower_priority > 0:
                logger.info(
                    f"Skipped {sources_skipped_lower_priority} lower-priority duplicates"
                )

            # Step 5: Batch update existing sources
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

            # Step 6: Batch insert new sources
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

            # Step 7: Mark all processed sources in cache to avoid reprocessing
            # Use canonical URL for cache to prevent cross-source duplicates
            for source in deduplicated_sources:
                if source.summary:
                    canonical = self._get_canonical_url(source)
                    self._source_cache.mark_as_processed(canonical)

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

    def cleanup_duplicate_sources(self) -> Dict[str, Any]:
        """
        One-time cleanup: Find and remove duplicate sources,
        keeping HN versions (higher priority) over engineering blog versions.

        Returns:
            Dict with cleanup statistics
        """
        with self.get_session() as session:
            all_sources = session.query(Source).all()

            # Group by canonical URL (source_link)
            by_canonical: Dict[str, List[Source]] = {}
            for s in all_sources:
                canonical = s.source_link
                if canonical not in by_canonical:
                    by_canonical[canonical] = []
                by_canonical[canonical].append(s)

            # Find and delete lower-priority duplicates
            duplicates_deleted = 0
            for canonical, sources in by_canonical.items():
                if len(sources) <= 1:
                    continue

                # Sort: highest priority first, then oldest (by created_at)
                sources.sort(
                    key=lambda s: (
                        -self._get_source_priority(s.link),
                        s.created_at,
                    )
                )

                # Keep first (highest priority), delete rest
                keep = sources[0]
                for dup in sources[1:]:
                    logger.info(
                        f"Removing duplicate: {dup.link} "
                        f"(keeping: {keep.link}, canonical: {canonical})"
                    )
                    session.delete(dup)
                    duplicates_deleted += 1

            session.commit()
            logger.info(f"Cleaned up {duplicates_deleted} duplicate sources")

            return {
                "total_sources": len(all_sources),
                "duplicates_deleted": duplicates_deleted,
                "unique_canonical_urls": len(by_canonical),
            }

    # --- User Management Methods ---

    def get_or_create_local_user(self, email: str) -> str:
        """Find the single local user by email, or create it."""
        with self.get_session() as session:
            user = session.query(User).filter(User.email == email).first()
            if user:
                return str(user.id)

            new_user = User(email=email)
            session.add(new_user)
            session.commit()
            logger.info(f"Created local user: {email}")
            return str(new_user.id)

    def get_user_custom_topics(self, user_id: str) -> List[str]:
        """Get custom topics for a user"""
        with self.get_session() as session:
            user = session.query(User).filter(User.id == user_id).first()
            if user and user.custom_topics:
                return user.custom_topics
            return []

    def update_user_custom_topics(self, user_id: str, topics: List[str]) -> bool:
        """Update custom topics for a user"""
        try:
            with self.get_session() as session:
                user = session.query(User).filter(User.id == user_id).first()
                if user:
                    user.custom_topics = topics
                    session.commit()
                    return True
                return False
        except Exception as e:
            logger.error(f"Failed to update custom topics for user {user_id}: {e}")
            return False

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
        self, user_id: str, start_date: datetime, end_date: Optional[datetime] = None
    ) -> List[Dict[str, str]]:
        with self.get_session() as session:
            query = session.query(Bookmark).filter(
                Bookmark.user_id == user_id, Bookmark.bookmarked_at >= start_date
            )
            if end_date:
                query = query.filter(Bookmark.bookmarked_at <= end_date)
            results = query.order_by(desc(Bookmark.bookmarked_at)).all()
            return [
                {
                    "title": b.title,
                    "link": b.link,
                    "source_tag": b.source_tag,
                    "summary": b.summary or "",
                    "summary_edited": b.summary_edited,
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

    def get_bookmark_cache_stats(self, user_id: str) -> Dict[str, int]:
        with self.get_session() as session:
            total_count = (
                session.query(Bookmark).filter(Bookmark.user_id == user_id).count()
            )
            week_ago = datetime.now() - timedelta(days=7)
            recent_count = (
                session.query(Bookmark)
                .filter(Bookmark.user_id == user_id, Bookmark.bookmarked_at >= week_ago)
                .count()
            )
            return {
                "total_bookmarks": total_count,
                "recent_bookmarks_7_days": recent_count,
            }

    def search_bookmarks(
        self, user_id: str, query: str, limit: int = 10
    ) -> List[Dict[str, str]]:
        with self.get_session() as session:
            # Sanitize query input to prevent SQL injection
            sanitized_query = "".join(
                c for c in query if c.isalnum() or c.isspace() or c in "-_"
            ).strip()

            if not sanitized_query:
                logger.warning(
                    f"Bookmark search query sanitization resulted in empty string: '{query}'"
                )
                return []

            # SQLAlchemy automatically parameterizes .ilike() queries
            results = (
                session.query(Bookmark)
                .filter(
                    Bookmark.user_id == user_id,
                    (
                        Bookmark.title.ilike(f"%{sanitized_query}%")
                        | Bookmark.summary.ilike(f"%{sanitized_query}%")
                    ),
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
                    "summary_edited": b.summary_edited,
                    "bookmarked_at": b.bookmarked_at.isoformat(),
                }
                for b in results
            ]

    # --- Embedding Cache Methods ---

    def get_embedding_from_cache(
        self, text_hash, model_name: str
    ) -> Optional[List[float]] | Dict[str, Optional[List[float]]]:
        """Gets embedding(s) from cache for single hash or list of hashes.

        Vectors produced by a different model are treated as cache misses.

        Args:
            text_hash: Either a single string hash or a list of string hashes
            model_name: The embedding model the vectors must come from

        Returns:
            For single hash: Optional[List[float]]
            For list of hashes: Dict[str, Optional[List[float]]]
        """
        # Handle single hash case (backward compatibility)
        if isinstance(text_hash, str):
            with self.get_session() as session:
                cached = (
                    session.query(EmbeddingCache)
                    .filter(
                        EmbeddingCache.text_hash == text_hash,
                        EmbeddingCache.model_name == model_name,
                    )
                    .first()
                )
                if cached:
                    return cached.embedding
                return None

        # Handle batch case
        if not isinstance(text_hash, list) or not text_hash:
            return {} if isinstance(text_hash, list) else None

        with self.get_session() as session:
            cached_embeddings = (
                session.query(EmbeddingCache)
                .filter(
                    EmbeddingCache.text_hash.in_(text_hash),
                    EmbeddingCache.model_name == model_name,
                )
                .all()
            )

            # Build result map
            result = {}
            found_hashes = {cached.text_hash for cached in cached_embeddings}

            for cached in cached_embeddings:
                result[cached.text_hash] = cached.embedding

            # Add None for hashes not found in cache
            for hash_val in text_hash:
                if hash_val not in found_hashes:
                    result[hash_val] = None

            return result

    def add_embedding_to_cache(
        self, text: str, text_hash: str, embedding: List[float], model_name: str
    ) -> None:
        """Stores an embedding, replacing a vector cached for the same text by another model."""
        with self.get_session() as session:
            stmt = pg_insert(EmbeddingCache).values(
                text=text,
                text_hash=text_hash,
                embedding=embedding,
                model_name=model_name,
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=[EmbeddingCache.text_hash],
                set_={
                    "embedding": stmt.excluded.embedding,
                    "model_name": stmt.excluded.model_name,
                    "created_at": stmt.excluded.created_at,
                },
            )
            session.execute(stmt)
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
            # Sanitize query input to prevent SQL injection
            sanitized_query = "".join(
                c for c in query if c.isalnum() or c.isspace() or c in "-_"
            ).strip()

            if not sanitized_query:
                logger.warning(
                    f"Embedding search query sanitization resulted in empty string: '{query}'"
                )
                return []

            # SQLAlchemy automatically parameterizes .ilike() queries
            results = (
                session.query(EmbeddingCache)
                .filter(EmbeddingCache.text.ilike(f"%{sanitized_query}%"))
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

    def _get_text_hash(self, text) -> str | List[str]:
        """Get SHA256 hash of text(s) for caching.

        Args:
            text: Either a single string or a list of strings

        Returns:
            For single string: str
            For list of strings: List[str]
        """
        if isinstance(text, str):
            return hashlib.sha256(text.encode("utf-8")).hexdigest()

        if isinstance(text, list):
            return [hashlib.sha256(t.encode("utf-8")).hexdigest() for t in text]

        raise ValueError("text must be either a string or a list of strings")

    def get_embedding_for_text(
        self, text, model_name: str
    ) -> Optional[List[float]] | Dict[str, Optional[List[float]]]:
        """Gets an embedding for the given text(s), using the cache if available.

        Args:
            text: Either a single string or a list of strings
            model_name: The embedding model the vectors must come from

        Returns:
            For single string: Optional[List[float]]
            For list of strings: Dict[str, Optional[List[float]]]
        """
        text_hash = self._get_text_hash(text)
        return self.get_embedding_from_cache(text_hash, model_name)

    def get_embeddings_for_texts(
        self, texts: List[str], model_name: str
    ) -> List[Optional[List[float]]]:
        """
        Gets cached embeddings for a list of texts in a single database query.

        Returns a list of embeddings aligned with the input order. Items with no
        cached embedding are returned as None to allow callers to decide how to
        handle cache misses.
        """
        if not texts:
            return []

        text_hashes = self._get_text_hash(texts)
        cached = self.get_embedding_from_cache(text_hashes, model_name)

        if not isinstance(cached, dict):
            return [None] * len(texts)

        return [cached.get(hash_val) for hash_val in text_hashes]

    def add_embedding_for_text(
        self, text: str, embedding: List[float], model_name: str
    ) -> None:
        """Adds a new text-embedding pair to the cache."""
        text_hash = self._get_text_hash(text)
        self.add_embedding_to_cache(text, text_hash, embedding, model_name)

    # --- Comment Insight Methods ---

    def save_comment_insights(self, insights_data: List[Dict]) -> int:
        """Save or update comment insights for multiple sources in batch.

        Args:
            insights_data: List of dicts with keys: source_id, link, title, comment_count, insights

        Returns:
            Number of insights saved/updated
        """
        if not insights_data:
            return 0

        saved_count = 0
        with self.get_session() as session:
            for data in insights_data:
                existing = (
                    session.query(CommentInsight)
                    .filter(CommentInsight.source_id == data["source_id"])
                    .first()
                )

                if existing:
                    existing.comment_count = data["comment_count"]
                    existing.insights = data["insights"]
                    existing.updated_at = datetime.now()
                else:
                    existing = CommentInsight(
                        source_id=data["source_id"],
                        link=data["link"],
                        title=data["title"],
                        comment_count=data["comment_count"],
                        insights=data["insights"],
                    )
                    session.add(existing)

                saved_count += 1

            session.commit()

        return saved_count

    def get_comment_insights(self, links: List[str]) -> Dict[str, CommentInsight]:
        """Get comment insights by HN links using batch database query."""
        if not links:
            return {}

        with self.get_session() as session:
            db_results = (
                session.query(CommentInsight)
                .filter(CommentInsight.link.in_(links))
                .all()
            )

            # Convert to dict
            return {insight.link: insight for insight in db_results}

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
