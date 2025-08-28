import unittest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime

from src.backend.pipeline import process_content_pipeline, _apply_balanced_filtering
from src.backend.schema import SourceSchema
from src.backend.constants import DISCOVERY_THRESHOLD

# Mock SourceSchema objects
mock_hf_paper = SourceSchema(
    title="Hugging Face Paper",
    authors=["Author A"],
    link="http://hf.co/paper/1",
    source_link="http://hf.co/paper/1",
    summary=None,  # Summary will be generated
    tags=["research"],
    date=datetime.now()
)

mock_hn_story = SourceSchema(
    title="Hacker News Story",
    authors=["Author B"],
    link="http://news.ycombinator.com/item/1",
    source_link="http://example.com/story",
    summary="An existing summary",
    tags=["industry"],
    date=datetime.now()
)

class TestPipeline(unittest.TestCase):

    @patch('src.backend.pipeline.scrape_all_sources_concurrent')
    @patch('src.backend.database.db_manager.get_session')
    @patch('src.backend.database.db_manager.save_sources')
    @patch('src.backend.database.db_manager.add_summaries_batch')
    @patch('src.backend.database.db_manager.get_bookmarks')
    @patch('src.backend.merger.enrich_sources_with_summaries_and_embeddings')
    @patch('src.backend.pipeline._apply_balanced_filtering')
    def test_process_content_pipeline_full_flow(self, mock_filter, mock_enrich, mock_get_bookmarks, mock_add_summaries_batch, mock_save_sources, mock_get_session, mock_scrape_all):
        """Test pipeline flow by running the async test method."""
        asyncio.run(self._async_test_process_content_pipeline_full_flow(
            mock_filter, mock_enrich, mock_get_bookmarks, mock_add_summaries_batch, 
            mock_save_sources, mock_get_session, mock_scrape_all
        ))

    async def _async_test_process_content_pipeline_full_flow(self, mock_filter, mock_enrich, mock_get_bookmarks, mock_add_summaries_batch, mock_save_sources, mock_get_session, mock_scrape_all):
        # --- Setup Mocks ---
        # Mock the concurrent scraping function to return both HF papers and RSS items
        # Make sure to set this as an async mock that returns a coroutine
        async def mock_scraping():
            return ([mock_hf_paper], [mock_hn_story])
        mock_scrape_all.side_effect = mock_scraping
        
        # Mock save_sources to return new sources that need summaries
        mock_save_sources.return_value = {
            'new_sources': [mock_hf_paper.link],  # HF paper needs summary generation
            'updated_sources': [],
            'skipped_sources': 0,
            'total_processed': 2
        }
        
        # Mock enrichment to return sources with summaries
        enriched_hf_paper = SourceSchema(
            title=mock_hf_paper.title,
            authors=mock_hf_paper.authors,
            link=mock_hf_paper.link,
            source_link=mock_hf_paper.source_link,
            summary="A newly generated summary.",
            tags=mock_hf_paper.tags,
            date=mock_hf_paper.date
        )
        mock_enrich.return_value = [enriched_hf_paper]
        
        # Mock batch summary addition
        mock_add_summaries_batch.return_value = {'http://hf.co/paper/1': True}
        
        # Mock database query to return some sources
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session
        
        # Create mock database sources
        mock_db_source1 = MagicMock()
        mock_db_source1.title = "HF Paper"
        mock_db_source1.authors = ["Author A"]
        mock_db_source1.link = "http://hf.co/paper/1"
        mock_db_source1.source_link = "http://hf.co/paper/1"
        mock_db_source1.summary = None  # This source needs a summary
        mock_db_source1.keywords = None
        mock_db_source1.tags = ["research"]
        mock_db_source1.date = datetime.now()
        
        mock_db_source2 = MagicMock()
        mock_db_source2.title = "HN Story"
        mock_db_source2.authors = ["Author B"]
        mock_db_source2.link = "http://news.ycombinator.com/item/1"
        mock_db_source2.source_link = "http://example.com/story"
        mock_db_source2.summary = "An existing summary"
        mock_db_source2.keywords = None
        mock_db_source2.tags = ["industry"]
        mock_db_source2.date = datetime.now()
        
        mock_session.query.return_value.filter.return_value.order_by.return_value.all.return_value = [mock_db_source1, mock_db_source2]
        
        # Mock bookmarks (no edited summaries)
        mock_get_bookmarks.return_value = []
        
        # Mock the advanced filter to return one of each (returns tuple of list and dict)
        mock_filter.return_value = ([mock_hf_paper, mock_hn_story], {})

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
        # Check for key events in the pipeline flow
        self.assertIn('status', [e['type'] for e in events])
        self.assertIn('start', [e['type'] for e in events])
        self.assertIn('progress', [e['type'] for e in events])
        self.assertIn('complete', [e['type'] for e in events])
        
        # Check that the new pipeline flow was followed
        self.assertTrue(mock_save_sources.called)
        self.assertTrue(mock_enrich.called)
        mock_add_summaries_batch.assert_called_with({'http://hf.co/paper/1': 'A newly generated summary.'})

        # Check that filtering was called
        self.assertTrue(mock_filter.called)
        call_args, _ = mock_filter.call_args
        self.assertGreaterEqual(len(call_args[0]), 2) # Called with at least 2 sources

        # Check the final result event
        result_event = events[-1]
        self.assertEqual(result_event['type'], 'result')
        self.assertGreaterEqual(result_event['data']['total_count'], 2)
        self.assertEqual(len(result_event['data']['items']), 2)
        # New pipeline returns database-based source categories
        sources = result_event['data']['sources']
        self.assertTrue(any(source in sources for source in ["Research Papers", "Industry News"]))

    @patch('src.backend.search.keyword_search')
    @patch('src.backend.search.semantic_search_with_scores')
    def test_discovery_mode_uses_ai_keyword(self, mock_semantic_search_with_scores, mock_keyword_search):
        """Test that discovery mode replaces with empty topics."""
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
        result = _apply_balanced_filtering(
            sources=[test_source],
            keywords=["original", "topics"],  # Should be ignored
            discovery_mode=True
        )
        
        mock_keyword_search.assert_not_called()
        mock_semantic_search_with_scores.assert_not_called()
        
        # Result is a tuple (filtered_sources, matched_keywords_map)
        filtered_sources, matched_keywords_map = result
        self.assertEqual(len(filtered_sources), 1)

if __name__ == '__main__':
    unittest.main()
