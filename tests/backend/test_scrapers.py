import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

from feedparser.util import FeedParserDict

from src.backend.scraper import (
    scrape_hacker_news,
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
    def test_scrape_hacker_news(self, mock_parse):
        # Setup the mock response for feedparser.parse
        mock_parse.return_value = MOCK_HN_FEED

        results = scrape_hacker_news()

        # Asserts that stories with comments links were parsed
        self.assertEqual(len(results), 2)

        # Check the first story (industry)
        story1 = results[0]
        self.assertIsInstance(story1, SourceSchema)
        self.assertEqual(story1.title, "Mock HN Story")
        self.assertEqual(str(story1.link), "https://news.ycombinator.com/item?id=12345")
        self.assertIsNone(story1.summary)
        self.assertIsNone(story1.keywords)
        self.assertEqual(story1.tags, ["industry"])
        self.assertIsInstance(story1.date, datetime)

        # Check the second story (research)
        story2 = results[1]
        self.assertIsInstance(story2, SourceSchema)
        self.assertEqual(story2.title, "A Research Paper [pdf]")
        self.assertEqual(str(story2.link), "https://news.ycombinator.com/item?id=54321")
        self.assertEqual(story2.tags, ["research"])