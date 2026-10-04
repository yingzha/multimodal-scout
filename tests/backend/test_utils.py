import unittest
from unittest.mock import patch

from src.backend.constants import MAX_SUGGESTION_PROMPT_CHARS
from src.backend.utils import (
    categorize_content,
    generate_keyword_suggestions_from_bookmarks,
    generate_summary_from_link,
)


class TestUtils(unittest.TestCase):

    @patch('src.backend.utils.generate_text')
    def test_categorize_accepts_decorated_answer(self, mock_generate_text):
        # Small models often wrap the single word in markdown or punctuation
        mock_generate_text.return_value = "**Industry**."

        category = categorize_content("Some title", "Some content", "http://fake-test.example/x")

        self.assertEqual(category, "Industry")

    @patch('src.backend.utils.generate_text')
    def test_categorize_defaults_to_general(self, mock_generate_text):
        mock_generate_text.return_value = "I am not sure."

        category = categorize_content("Some title", "Some content", "http://fake-test.example/x")

        self.assertEqual(category, "General")

    @patch('src.backend.utils.generate_text')
    def test_keyword_suggestions_parse_lists(self, mock_generate_text):
        mock_generate_text.return_value = "- Vision Language Models\n- video agents, robotics\n* multimodal"
        bookmarks = [{"title": "A paper", "summary": "About things"}]

        keywords = generate_keyword_suggestions_from_bookmarks(bookmarks, ["multimodal"])

        self.assertEqual(keywords, ["vision language models", "video agents", "robotics"])

    @patch('src.backend.utils.generate_text')
    def test_keyword_suggestion_prompt_is_bounded(self, mock_generate_text):
        mock_generate_text.return_value = "agents"
        bookmarks = [{"title": f"Title {i}", "summary": "x" * 5000} for i in range(50)]

        generate_keyword_suggestions_from_bookmarks(bookmarks, [])

        prompt = mock_generate_text.call_args.args[0]
        self.assertLess(len(prompt), MAX_SUGGESTION_PROMPT_CHARS + 1500)
        self.assertIn("Title 0", prompt)

    @patch('src.backend.utils._fetch_article_text')
    @patch('src.backend.utils.generate_text')
    def test_summary_falls_back_to_title_on_llm_error(self, mock_generate_text, mock_fetch):
        mock_fetch.return_value = "word " * 100
        mock_generate_text.side_effect = Exception("model server down")

        with patch('src.backend.utils.time.sleep'):
            summary = generate_summary_from_link("http://fake-test.example/article", "The Title")

        self.assertEqual(summary, "The Title")
        self.assertEqual(mock_generate_text.call_count, 3)

if __name__ == '__main__':
    unittest.main()
