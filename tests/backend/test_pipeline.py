import unittest
import unittest.mock
import asyncio
from unittest.mock import patch, MagicMock
from datetime import datetime

import os
import threading
import time

from src.backend.merger import enrich_sources_with_summaries
from src.backend.pipeline import process_content_pipeline, _apply_balanced_filtering
from src.backend.schema import SourceSchema

# Mock SourceSchema objects
mock_hf_paper = SourceSchema(
    title="Hugging Face Paper",
    authors=["Author A"],
    link="http://fake-test.example/paper/1",
    source_link="http://fake-test.example/paper/1",
    summary=None,  # Summary will be generated
    tags=["research"],
    date=datetime.now()
)

mock_hn_story = SourceSchema(
    title="Hacker News Story",
    authors=["Author B"],
    link="http://fake-hn.example/item/1",
    source_link="http://fake-test.example/story",
    summary="An existing summary",
    tags=["industry"],
    date=datetime.now()
)

class TestPipeline(unittest.TestCase):

    @patch('src.backend.search.embed_text', return_value=[0.1, 0.2, 0.3])  # Mock the embedding model
    @patch('requests.get')  # Mock all HTTP requests
    @patch('src.backend.pipeline.scrape_all_sources_concurrent')  # Mock scraping (external API calls)
    @patch('src.backend.database.db_manager.get_session')  # Mock database sessions
    def test_process_content_pipeline_full_flow(self, mock_get_session, mock_scrape_all, mock_requests, mock_embed_text):
        """Test pipeline flow by running the async test method."""
        asyncio.run(self._async_test_process_content_pipeline_full_flow(
            mock_get_session, mock_scrape_all, mock_requests
        ))

    async def _async_test_process_content_pipeline_full_flow(self, mock_get_session, mock_scrape_all, mock_requests):
        # --- Setup Mocks ---
        # Mock HTTP requests to prevent actual network calls
        mock_response = unittest.mock.Mock()
        mock_response.status_code = 200
        mock_response.text = "<html><body><p>Mock article content for testing</p></body></html>"
        mock_requests.return_value = mock_response
        
        # Mock the concurrent scraping function to return test sources
        async def mock_scraping():
            return ([mock_hf_paper], [mock_hn_story])
        mock_scrape_all.side_effect = mock_scraping
        
        # Mock database operations with minimal setup
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session
        
        # Mock database query to return empty results (testing fresh pipeline)
        mock_session.query.return_value.filter.return_value.order_by.return_value.all.return_value = []

        # --- Run Pipeline ---
        pipeline_generator = process_content_pipeline(
            topics=["test"],
            max_results=2,
            research_ratio=0.5
        )
        
        events = []
        async for event in pipeline_generator:
            events.append(event)

        # --- Assertions ---
        # Test that pipeline generates the expected event types
        event_types = [e['type'] for e in events]
        self.assertIn('status', event_types, "Pipeline should generate status events")
        self.assertIn('start', event_types, "Pipeline should generate start event")
        self.assertIn('progress', event_types, "Pipeline should generate progress events")
        
        # Test that scraping was called (external dependency)
        self.assertTrue(mock_scrape_all.called, "Pipeline should call scraping function")
        
        # Test that HTTP requests were made (for summary generation)
        self.assertTrue(mock_requests.called, "Pipeline should make HTTP requests for content")
        
        # Test that database session was used
        self.assertTrue(mock_get_session.called, "Pipeline should use database session")
        
        # Test that pipeline completes with results
        self.assertTrue(len(events) > 0, "Pipeline should generate events")
        
        # Check for completion or result event
        final_events = [e['type'] for e in events[-3:]]  # Check last few events
        self.assertTrue(any(event_type in final_events for event_type in ['complete', 'result']),
                       "Pipeline should complete with result or complete event")

    @patch('src.backend.search.keyword_search')
    @patch('src.backend.search.semantic_search_with_scores')
    def test_discovery_mode_uses_ai_keyword(self, mock_semantic_search_with_scores, mock_keyword_search):
        """Test that discovery mode replaces with empty topics."""
        asyncio.run(self._async_test_discovery_mode_uses_ai_keyword(
            mock_semantic_search_with_scores, mock_keyword_search
        ))
    
    async def _async_test_discovery_mode_uses_ai_keyword(self, mock_semantic_search_with_scores, mock_keyword_search):
        """Async implementation of discovery mode test."""
        # Create a simple test source
        test_source = SourceSchema(
            title="Test Article",
            authors=["Author"],
            link="http://example.com/test",
            source_link="http://example.com/test",
            summary="Test summary",
            tags=["research"],
            date=datetime.now()
        )
        
        mock_keyword_search.return_value = []
        mock_semantic_search_with_scores.return_value = []
        
        # Call with discovery mode
        result = await _apply_balanced_filtering(
            sources=[test_source],
            keywords=["original", "topics"],  # Should be ignored
            discovery_mode=True
        )
        
        mock_keyword_search.assert_not_called()
        mock_semantic_search_with_scores.assert_not_called()
        
        # Result is a tuple (filtered_sources, matched_keywords_map)
        filtered_sources, matched_keywords_map = result
        self.assertEqual(len(filtered_sources), 1)

    def test_summary_generation_is_capped(self):
        """Test that no more than LLM_MAX_CONCURRENCY summaries are generated at once."""
        sources = [
            SourceSchema(
                title=f"Article {i}",
                authors=["Author"],
                link=f"http://fake-test.example/article/{i}",
                source_link=f"http://fake-test.example/article/{i}",
                summary=None,
                tags=["industry"],
                date=datetime.now()
            )
            for i in range(6)
        ]

        lock = threading.Lock()
        in_flight = 0
        max_in_flight = 0

        def slow_summary(link, title=None):
            nonlocal in_flight, max_in_flight
            with lock:
                in_flight += 1
                max_in_flight = max(max_in_flight, in_flight)
            time.sleep(0.05)
            with lock:
                in_flight -= 1
            return f"Summary of {title}"

        with patch.dict(os.environ, {"LLM_MAX_CONCURRENCY": "2"}), \
                patch('src.backend.merger.generate_summary_from_link', side_effect=slow_summary):
            enriched = asyncio.run(enrich_sources_with_summaries(sources))

        self.assertEqual(max_in_flight, 2)
        self.assertTrue(all(source.summary for source in enriched))

if __name__ == '__main__':
    unittest.main()
