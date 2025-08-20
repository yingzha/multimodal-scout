import unittest
import asyncio
from datetime import datetime
from unittest.mock import MagicMock, patch, AsyncMock

from src.backend.schema import SourceSchema


class TestScrapers(unittest.TestCase):

    def test_scrape_all_sources_concurrent(self):
        """Test that the concurrent scraping function works and returns the expected structure."""
        from src.backend.scraper import scrape_all_sources_concurrent
        
        # Create a simple async test
        async def test_concurrent():
            # Mock the individual scraper functions
            with patch('src.backend.scraper.scrape_huggingface_trending_papers') as mock_hf, \
                 patch('src.backend.scraper.scrape_rss_sources') as mock_rss:
                
                # Mock return values
                mock_hf_paper = SourceSchema(
                    title="Mock HF Paper",
                    authors=["Author"],
                    link="https://huggingface.co/papers/test",
                    source_link="https://huggingface.co/papers/test",
                    summary="Test summary",
                    tags=["research"],
                    date=datetime.now()
                )
                
                mock_rss_item = SourceSchema(
                    title="Mock RSS Item",
                    authors=["Author"],
                    link="https://example.com/test",
                    source_link="https://example.com/test",
                    summary="Test summary",
                    tags=["industry"],
                    date=datetime.now()
                )
                
                mock_hf.return_value = [mock_hf_paper]
                mock_rss.return_value = [mock_rss_item]
                
                # Run the concurrent function
                hf_papers, rss_items = await scrape_all_sources_concurrent()
                
                # Verify results
                self.assertEqual(len(hf_papers), 1)
                self.assertEqual(len(rss_items), 1)
                self.assertEqual(hf_papers[0].title, "Mock HF Paper")
                self.assertEqual(rss_items[0].title, "Mock RSS Item")
                
                return hf_papers, rss_items
        
        # Run the async test
        hf_papers, rss_items = asyncio.run(test_concurrent())
        
        # Additional verification
        self.assertIsInstance(hf_papers[0], SourceSchema)
        self.assertIsInstance(rss_items[0], SourceSchema)

    def test_scraper_functions_are_async(self):
        """Test that the scraper functions are properly async."""
        from src.backend.scraper import scrape_huggingface_trending_papers, scrape_rss_sources
        import inspect
        
        # Verify functions are coroutines
        self.assertTrue(inspect.iscoroutinefunction(scrape_huggingface_trending_papers))
        self.assertTrue(inspect.iscoroutinefunction(scrape_rss_sources))


if __name__ == '__main__':
    unittest.main()