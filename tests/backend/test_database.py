import unittest
from unittest.mock import patch
from datetime import datetime, timedelta
import hashlib

from src.backend.database import DatabaseManager, Source, Base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

class TestDatabaseManager(unittest.TestCase):

    def setUp(self):
        # Use an in-memory SQLite database for testing
        self.engine = create_engine('sqlite:///:memory:')
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
        # Patch db_manager to use our test engine
        self.db_manager_patch = patch('src.backend.database.db_manager', new=DatabaseManager(database_url='sqlite:///:memory:'))
        self.mock_db_manager = self.db_manager_patch.start()
        self.mock_db_manager.engine = self.engine # Ensure the patched manager uses our test engine
        self.mock_db_manager.SessionLocal = self.SessionLocal

    def tearDown(self):
        Base.metadata.drop_all(self.engine)
        self.db_manager_patch.stop()

    def test_get_text_hash(self):
        text = "test string"
        expected_hash = hashlib.sha256(text.encode('utf-8')).hexdigest()
        self.assertEqual(self.mock_db_manager._get_text_hash(text), expected_hash)

    @patch('src.backend.database.DatabaseManager.get_embedding_from_cache')
    def test_get_embedding_for_text(self, mock_get_embedding_from_cache):
        mock_get_embedding_from_cache.return_value = [0.1, 0.2, 0.3]
        text = "sample text"
        embedding = self.mock_db_manager.get_embedding_for_text(text)
        self.assertEqual(embedding, [0.1, 0.2, 0.3])
        mock_get_embedding_from_cache.assert_called_once_with(self.mock_db_manager._get_text_hash(text))

    @patch('src.backend.database.DatabaseManager.add_embedding_to_cache')
    def test_add_embedding_for_text(self, mock_add_embedding_to_cache):
        text = "another sample"
        embedding = [0.4, 0.5, 0.6]
        model_name = "test-model"
        self.mock_db_manager.add_embedding_for_text(text, embedding, model_name)
        mock_add_embedding_to_cache.assert_called_once_with(text, self.mock_db_manager._get_text_hash(text), embedding, model_name)

    def test_add_and_get_summary(self):
        url = "http://example.com/test"
        summary = "This is a test summary."
        
        # First, create a source in the database (required for consolidated approach)
        with self.mock_db_manager.get_session() as session:
            source = Source(
                title="Test Article",
                authors=["Test Author"],
                link=url,
                source_link=url,
                summary=None,  # Initially no summary
                keywords=["test"],
                tags=["test"],
                date=datetime.utcnow()
            )
            session.add(source)
            session.commit()
        
        # Now add the summary
        self.mock_db_manager.add_summaries({url: summary})
        
        # Verify summary was added by querying the source directly
        with self.mock_db_manager.get_session() as session:
            updated_source = session.query(Source).filter(Source.link == url).first()
            self.assertEqual(updated_source.summary, summary)

    def test_cleanup_summaries(self):
        # Add an old source with summary that should be cleaned up
        old_summary_url = "http://old.com"
        old_summary_content = "Old content."
        with self.mock_db_manager.get_session() as session:
            old_source = Source(
                title="Old Article",
                authors=["Old Author"],
                link=old_summary_url,
                source_link=old_summary_url,
                summary=old_summary_content,
                keywords=["old"],
                tags=["test"],
                date=datetime.utcnow(),
                created_at=datetime.utcnow() - timedelta(days=60)
            )
            session.add(old_source)
            session.commit()
        
        # Add a new source with summary that should not be cleaned up
        new_summary_url = "http://new.com"
        new_summary_content = "New content."
        with self.mock_db_manager.get_session() as session:
            new_source = Source(
                title="New Article",
                authors=["New Author"],
                link=new_summary_url,
                source_link=new_summary_url,
                summary=None,  # Initially no summary
                keywords=["new"],
                tags=["test"],
                date=datetime.utcnow()
            )
            session.add(new_source)
            session.commit()
        
        self.mock_db_manager.add_summaries({new_summary_url: new_summary_content})

        # Test cleanup using the current method
        result = self.mock_db_manager.cleanup_summaries_and_embeddings(days_to_keep=30)
        self.assertEqual(result["summaries_cleaned"], 1)

    def test_cleanup_summaries_and_embeddings(self):
        # Add an old source with summary that should be cleaned up
        old_summary_url = "http://old.com"
        old_summary_content = "Old content for embedding test."
        with self.mock_db_manager.get_session() as session:
            old_source = Source(
                title="Old Article",
                authors=["Old Author"], 
                link=old_summary_url,
                source_link=old_summary_url,
                summary=old_summary_content,
                keywords=["old"],
                tags=["test"],
                date=datetime.utcnow(),
                created_at=datetime.utcnow() - timedelta(days=60)
            )
            session.add(old_source)
            session.commit()
        
        # Add corresponding embedding
        self.mock_db_manager.add_embedding_for_text(old_summary_content, [0.1, 0.2, 0.3], "test-model")
        
        # Add a new source with summary that should not be cleaned up
        new_summary_url = "http://new.com"
        new_summary_content = "New content for embedding test."
        with self.mock_db_manager.get_session() as session:
            new_source = Source(
                title="New Article",
                authors=["New Author"],
                link=new_summary_url,
                source_link=new_summary_url,
                summary=new_summary_content,
                keywords=["new"],
                tags=["test"],
                date=datetime.utcnow(),
                created_at=datetime.utcnow() - timedelta(days=5)  # Recent
            )
            session.add(new_source)
            session.commit()
        self.mock_db_manager.add_embedding_for_text(new_summary_content, [0.4, 0.5, 0.6], "test-model")

        # Test new unified cleanup function
        result = self.mock_db_manager.cleanup_summaries_and_embeddings(days_to_keep=30)
        self.assertEqual(result['summaries_cleaned'], 1)
        self.assertEqual(result['embeddings_cleaned'], 1)
        
        # Verify cleanup by checking sources directly
        with self.mock_db_manager.get_session() as session:
            old_source = session.query(Source).filter(Source.link == old_summary_url).first()
            new_source = session.query(Source).filter(Source.link == new_summary_url).first()
            self.assertIsNone(old_source.summary)  # Should be cleaned up
            self.assertEqual(new_source.summary, new_summary_content)  # Should remain

    def test_get_summary_cache_stats(self):
        # Create sources first, then add summaries
        with self.mock_db_manager.get_session() as session:
            source1 = Source(
                title="Article 1",
                authors=["Author 1"],
                link="http://s1.com",
                source_link="http://s1.com",
                summary=None,
                keywords=["test"],
                tags=["test"],
                date=datetime.utcnow()
            )
            source2 = Source(
                title="Article 2",
                authors=["Author 2"],
                link="http://s2.com",
                source_link="http://s2.com",
                summary=None,
                keywords=["test"],
                tags=["test"],
                date=datetime.utcnow()
            )
            session.add_all([source1, source2])
            session.commit()
        
        self.mock_db_manager.add_summaries({
            "http://s1.com": "s1",
            "http://s2.com": "s2"
        })
        
        # Add an old source with summary for recent stats
        with self.mock_db_manager.get_session() as session:
            old_source = Source(
                title="Old Article",
                authors=["Old Author"],
                link="http://old.com",
                source_link="http://old.com",
                summary="old",
                keywords=["old"],
                tags=["test"],
                date=datetime.utcnow(),
                created_at=datetime.utcnow() - timedelta(days=10)
            )
            session.add(old_source)
            session.commit()

        stats = self.mock_db_manager.get_summary_cache_stats()
        self.assertEqual(stats['total_summaries'], 3)
        self.assertEqual(stats['recent_summaries_7_days'], 2) # s1 and s2 are recent

    def test_search_summaries(self):
        # Create sources first, then add summaries
        with self.mock_db_manager.get_session() as session:
            sources = [
                Source(
                    title="AI Article",
                    authors=["AI Author"],
                    link="http://ai.com",
                    source_link="http://ai.com",
                    summary=None,
                    keywords=["ai"],
                    tags=["test"],
                    date=datetime.utcnow()
                ),
                Source(
                    title="ML Article",
                    authors=["ML Author"],
                    link="http://ml.com",
                    source_link="http://ml.com",
                    summary=None,
                    keywords=["ml"],
                    tags=["test"],
                    date=datetime.utcnow()
                ),
                Source(
                    title="Data Article",
                    authors=["Data Author"],
                    link="http://data.com",
                    source_link="http://data.com",
                    summary=None,
                    keywords=["data"],
                    tags=["test"],
                    date=datetime.utcnow()
                )
            ]
            session.add_all(sources)
            session.commit()
        
        self.mock_db_manager.add_summaries({
            "http://ai.com": "Summary about AI.",
            "http://ml.com": "Machine learning is great.",
            "http://data.com": "Data science is cool."
        })

        results = self.mock_db_manager.search_summaries("AI")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['url'], "http://ai.com")

        results = self.mock_db_manager.search_summaries("learning")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['url'], "http://ml.com")

        results = self.mock_db_manager.search_summaries("science")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['url'], "http://data.com")


if __name__ == '__main__':
    unittest.main()
