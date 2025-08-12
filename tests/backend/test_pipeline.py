import unittest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime

from src.backend.pipeline import process_content_pipeline
from src.backend.schema import SourceSchema

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

    @patch('src.backend.pipeline.scrape_huggingface_trending_papers')
    @patch('src.backend.pipeline.scrape_hacker_news')
    @patch('src.backend.database.db_manager.get_summary')
    @patch('src.backend.database.db_manager.add_summary')
    @patch('src.backend.pipeline.generate_summary_from_link')
    @patch('src.backend.pipeline._apply_balanced_filtering')
    def test_process_content_pipeline_full_flow(self, mock_filter, mock_generate_summary, mock_add_summary, mock_get_summary, mock_scrape_hn, mock_scrape_hf):
        # --- Setup Mocks ---
        mock_scrape_hf.return_value = [mock_hf_paper]
        mock_scrape_hn.return_value = [mock_hn_story]
        
        # Mock cache: return None for the paper that needs a summary
        mock_get_summary.return_value = None
        # Mock summary generation
        mock_generate_summary.return_value = "A newly generated summary."
        
        # Mock the advanced filter to return one of each
        mock_filter.return_value = [mock_hf_paper, mock_hn_story]

        # --- Run Pipeline ---
        pipeline_generator = process_content_pipeline(
            topics=["test"],
            max_results=2,
            research_ratio=0.5
        )
        
        events = list(pipeline_generator)

        # --- Assertions ---
        # Check for key events in the pipeline flow
        self.assertIn('status', [e['type'] for e in events])
        self.assertIn('start', [e['type'] for e in events])
        self.assertIn('progress', [e['type'] for e in events])
        self.assertIn('complete', [e['type'] for e in events])
        
        # Check that summary generation was attempted
        mock_get_summary.assert_any_call('http://hf.co/paper/1')
        self.assertTrue(mock_generate_summary.called)
        mock_add_summary.assert_any_call('http://hf.co/paper/1', "A newly generated summary.")

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

if __name__ == '__main__':
    unittest.main()
