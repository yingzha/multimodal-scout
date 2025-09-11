import unittest
from unittest.mock import patch
from datetime import datetime, timedelta
import hashlib
import os

from src.backend.database import DatabaseManager, Source, Base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

class TestDatabaseManager(unittest.TestCase):

    def setUp(self):
        # Use the same PostgreSQL database as production but in test mode
        test_db_url = os.getenv('DATABASE_URL', 'postgresql://scout_user:scout_password@postgres:5432/multimodal_scout')
        self.engine = create_engine(test_db_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
        # Patch db_manager to use our test engine
        self.db_manager_patch = patch('src.backend.database.db_manager', new=DatabaseManager(database_url=test_db_url))
        self.mock_db_manager = self.db_manager_patch.start()
        self.mock_db_manager.engine = self.engine
        self.mock_db_manager.SessionLocal = self.SessionLocal

    def tearDown(self):
        # Clean up test data after each test
        try:
            with self.SessionLocal() as session:
                # Delete all test sources using a single pattern
                session.query(Source).filter(
                    Source.link.like('http://test%')
                ).delete(synchronize_session=False)
                session.commit()
        except Exception as e:
            # If cleanup fails, log it but don't fail the test
            print(f"Warning: Test cleanup failed: {e}")
        
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
        url = "http://test-summary.example/test"
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
        old_summary_url = "http://test-old-cleanup.example"
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
        new_summary_url = "http://test-new.example"
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
        old_summary_url = "http://test-old.example"
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
        new_summary_url = "http://test-new.example"
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
            # Summary might be truncated, just check it exists and starts correctly
            self.assertIsNotNone(new_source.summary)  # Should remain
            self.assertTrue(new_source.summary.startswith("New content"))  # Should remain

    def test_get_summary_cache_stats(self):
        # Get baseline stats first
        initial_stats = self.mock_db_manager.get_summary_cache_stats()
        initial_total = initial_stats['total_summaries']
        initial_recent = initial_stats['recent_summaries_7_days']
        
        # Create sources first, then add summaries
        with self.mock_db_manager.get_session() as session:
            source1 = Source(
                title="Article 1",
                authors=["Author 1"],
                link="http://test-s1.example",
                source_link="http://test-s1.example",
                summary=None,
                keywords=["test"],
                tags=["test"],
                date=datetime.utcnow()
            )
            source2 = Source(
                title="Article 2",
                authors=["Author 2"],
                link="http://test-s2.example",
                source_link="http://test-s2.example",
                summary=None,
                keywords=["test"],
                tags=["test"],
                date=datetime.utcnow()
            )
            session.add_all([source1, source2])
            session.commit()
        
        self.mock_db_manager.add_summaries({
            "http://test-s1.example": "s1",
            "http://test-s2.example": "s2"
        })
        
        # Add an old source with summary for recent stats
        with self.mock_db_manager.get_session() as session:
            old_source = Source(
                title="Old Article",
                authors=["Old Author"],
                link="http://test-old.example",
                source_link="http://test-old.example",
                summary="old",
                keywords=["old"],
                tags=["test"],
                date=datetime.utcnow(),
                created_at=datetime.utcnow() - timedelta(days=10)
            )
            session.add(old_source)
            session.commit()

        # Check that stats increased by the expected amount
        final_stats = self.mock_db_manager.get_summary_cache_stats()
        # We should have 3 more summaries total (s1, s2, old)
        self.assertGreaterEqual(final_stats['total_summaries'], initial_total + 3)
        # We should have 2 more recent summaries (s1, s2 are recent)
        self.assertGreaterEqual(final_stats['recent_summaries_7_days'], initial_recent + 2)

    def test_search_summaries(self):
        # Create sources first, then add summaries
        with self.mock_db_manager.get_session() as session:
            sources = [
                Source(
                    title="AI Article",
                    authors=["AI Author"],
                    link="http://test-ai.example",
                    source_link="http://test-ai.example",
                    summary=None,
                    keywords=["ai"],
                    tags=["test"],
                    date=datetime.utcnow()
                ),
                Source(
                    title="ML Article",
                    authors=["ML Author"],
                    link="http://test-ml.example",
                    source_link="http://test-ml.example",
                    summary=None,
                    keywords=["ml"],
                    tags=["test"],
                    date=datetime.utcnow()
                ),
                Source(
                    title="Data Article",
                    authors=["Data Author"],
                    link="http://test-data.example",
                    source_link="http://test-data.example",
                    summary=None,
                    keywords=["data"],
                    tags=["test"],
                    date=datetime.utcnow()
                )
            ]
            session.add_all(sources)
            session.commit()
        
        self.mock_db_manager.add_summaries({
            "http://test-ai.example": "Summary about unique_test_term_xyz_ai_search for testing.",
            "http://test-ml.example": "Machine learning is great for research.",
            "http://test-data.example": "Data science is cool with no special terms."
        })

        # Use a very unique search term that won't match production data
        results = self.mock_db_manager.search_summaries("unique_test_term_xyz_ai_search")
        
        # Should find exactly 1 result
        self.assertEqual(len(results), 1)
        self.assertIn("unique_test_term_xyz_ai_search", results[0]['summary'])
        self.assertEqual(results[0]['url'], "http://test-ai.example")

        # Test another unique term
        results = self.mock_db_manager.search_summaries("xyz_ai_search")  
        self.assertEqual(len(results), 1)  # Should find the first one
        
        # Test non-existent unique term
        results = self.mock_db_manager.search_summaries("nonexistent_unique_test_term_12345")
        self.assertEqual(len(results), 0)


if __name__ == '__main__':
    unittest.main()
