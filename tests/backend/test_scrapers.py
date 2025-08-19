import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

from feedparser.util import FeedParserDict

from src.backend.scraper import (
    scrape_rss_sources,
    scrape_huggingface_trending_papers
)
from src.backend.schema import SourceSchema

# Mock data for Hugging Face - a simplified HTML structure
MOCK_HF_HTML = '''
<html><body>
    <div class="SVELTE_HYDRATER contents" data-props='{ 
        "dailyPapers": [
            {
                "paper": {
                    "id": "1234.5678",
                    "title": "Mock Paper Title",
                    "authors": [{"name": "Dr. Mock"}],
                    "publishedAt": "2023-10-27T10:00:00.000Z",
                    "ai_summary": "This is a mock summary.",
                    "ai_keywords": ["mock", "testing"]
                }
            },
            {
                "paper": {
                    "id": "9999.9999",
                    "title": "Invalid Paper Missing Date"
                }
            }
        ]
    }'></div>
</body></html>
'''

# Mock data for Hacker News (simulating feedparser's parsed output)
MOCK_HN_FEED = FeedParserDict({
    'bozo': 0,
    'entries': [
        FeedParserDict({
            'title': 'Mock HN Story',
            'author': 'testuser',
            'link': 'https://example.com/story',
            'comments': 'https://news.ycombinator.com/item?id=12345',
            'published': 'Mon, 28 Oct 2023 15:00:00 +0000'
        }),
        FeedParserDict({
            'title': 'Another Story No Comments',
            'author': 'anotheruser',
            'link': 'https://example.com/another',
            'published': 'Mon, 28 Oct 2023 16:00:00 +0000'
        }),
        FeedParserDict({
            'title': 'A Research Paper [pdf]',
            'author': 'scientist',
            'link': 'https://arxiv.org/abs/1234.5678',
            'comments': 'https://news.ycombinator.com/item?id=54321',
            'published': 'Mon, 28 Oct 2023 17:00:00 +0000'
        })
    ]
})


class TestScrapers(unittest.TestCase):

    @patch('src.backend.scraper.requests.get')
    def test_scrape_huggingface_trending_papers(self, mock_get):
        # Setup the mock response for requests.get
        mock_response = MagicMock()
        mock_response.text = MOCK_HF_HTML
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        results = scrape_huggingface_trending_papers()

        # Asserts that only the valid paper was parsed
        self.assertEqual(len(results), 1)
        self.assertIsInstance(results[0], SourceSchema)
        paper = results[0]
        self.assertEqual(paper.title, "Mock Paper Title")
        self.assertEqual(paper.authors, ["Dr. Mock"])
        self.assertEqual(str(paper.link), "https://huggingface.co/papers/1234.5678")
        self.assertEqual(paper.summary, "This is a mock summary.")
        self.assertEqual(paper.keywords, ["mock", "testing"])
        self.assertEqual(paper.tags, ["research"])
        self.assertIsInstance(paper.date, datetime)

    @patch('src.backend.scraper.feedparser.parse')
    def test_scrape_rss_sources(self, mock_parse):
        # Setup the mock response for feedparser.parse
        # Since scrape_rss_sources now processes multiple RSS feeds,
        # mock_parse will be called multiple times, returning the same mock feed each time
        mock_parse.return_value = MOCK_HN_FEED

        results = scrape_rss_sources()

        # Since we now scrape 2 RSS sources and each returns the same 3 entries,
        # we expect 6 total results (3 entries × 2 sources)
        self.assertEqual(len(results), 6)

        # Verify all results are SourceSchema instances with required attributes
        for result in results:
            self.assertIsInstance(result, SourceSchema)
            self.assertTrue(hasattr(result, 'title'))
            self.assertTrue(hasattr(result, 'link'))
            self.assertTrue(hasattr(result, 'tags'))
            self.assertIn(result.tags[0], ['industry', 'research'])
            self.assertIsInstance(result.date, datetime)