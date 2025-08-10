import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
import hashlib

from src.backend.database import DatabaseManager, SummaryCache, EmbeddingCache, Base
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
        self.mock_db_manager.add_summary(url, summary)
        retrieved_summary = self.mock_db_manager.get_summary(url)
        self.assertEqual(retrieved_summary, summary)

    def test_cleanup_summaries(self):
        # Add a summary that should be cleaned up
        old_summary_url = "http://old.com"
        old_summary_content = "Old content."
        with self.mock_db_manager.get_session() as session:
            session.add(SummaryCache(url=old_summary_url, summary=old_summary_content, created_at=datetime.utcnow() - timedelta(days=60)))
            session.commit()
        
        # Add a summary that should not be cleaned up
        new_summary_url = "http://new.com"
        new_summary_content = "New content."
        self.mock_db_manager.add_summary(new_summary_url, new_summary_content)

        deleted_count = self.mock_db_manager.cleanup_summaries(days_to_keep=30)
        self.assertEqual(deleted_count, 1)
        self.assertIsNone(self.mock_db_manager.get_summary(old_summary_url))
        self.assertEqual(self.mock_db_manager.get_summary(new_summary_url), new_summary_content)

    def test_get_summary_cache_stats(self):
        self.mock_db_manager.add_summary("http://s1.com", "s1")
        self.mock_db_manager.add_summary("http://s2.com", "s2")
        
        # Add an old summary for recent stats
        with self.mock_db_manager.get_session() as session:
            session.add(SummaryCache(url="http://old.com", summary="old", created_at=datetime.utcnow() - timedelta(days=10)))
            session.commit()

        stats = self.mock_db_manager.get_summary_cache_stats()
        self.assertEqual(stats['total_summaries'], 3)
        self.assertEqual(stats['recent_summaries_7_days'], 2) # s1 and s2 are recent

    def test_search_summaries(self):
        self.mock_db_manager.add_summary("http://ai.com", "Summary about AI.")
        self.mock_db_manager.add_summary("http://ml.com", "Machine learning is great.")
        self.mock_db_manager.add_summary("http://data.com", "Data science is cool.")

        results = self.mock_db_manager.search_summaries("AI")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['url'], "http://ai.com")

        results = self.mock_db_manager.search_summaries("learning")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['url'], "http://ml.com")

        results = self.mock_db_manager.search_summaries("science")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['url'], "http://data.com")

    def test_remove_summary(self):
        url = "http://remove.com"
        self.mock_db_manager.add_summary(url, "To be removed.")
        self.assertEqual(self.mock_db_manager.get_summary(url), "To be removed.")
        removed = self.mock_db_manager.remove_summary(url)
        self.assertTrue(removed)
        self.assertIsNone(self.mock_db_manager.get_summary(url))

        removed = self.mock_db_manager.remove_summary("http://nonexistent.com")
        self.assertFalse(removed)

    @patch('src.backend.database.DatabaseManager.get_all_summaries')
    @patch('src.backend.utils._is_non_english_summary')
    @patch('src.backend.database.DatabaseManager.invalidate_summary_cache')
    @patch('src.backend.database.DatabaseManager.invalidate_embedding_cache')
    def test_invalidate_non_english_summaries(self, mock_invalidate_embedding, mock_invalidate_summary, mock_is_non_english, mock_get_all_summaries):
        mock_get_all_summaries.return_value = {
            "http://eng.com": "This is an English summary.",
            "http://non-eng.com": "Ceci est un résumé français."
        }
        mock_is_non_english.side_effect = lambda x: x == "Ceci est un résumé français."
        mock_invalidate_summary.return_value = True
        mock_invalidate_embedding.return_value = True

        removed_count = self.mock_db_manager.invalidate_non_english_summaries()
        self.assertEqual(removed_count, 1)
        mock_invalidate_summary.assert_called_once_with("http://non-eng.com")
        mock_invalidate_embedding.assert_called_once()

if __name__ == '__main__':
    unittest.main()
