import os
import unittest
from unittest.mock import patch, MagicMock

from src.backend import client


def _chat_response(content):
    response = MagicMock()
    response.json.return_value = {"choices": [{"message": {"content": content}}]}
    return response


class TestClient(unittest.TestCase):

    @patch('src.backend.client.requests.post')
    def test_generate_text_returns_reply(self, mock_post):
        mock_post.return_value = _chat_response("  A summary.  ")

        self.assertEqual(client.generate_text("prompt"), "A summary.")

        url = mock_post.call_args.args[0]
        payload = mock_post.call_args.kwargs['json']
        self.assertTrue(url.endswith("/chat/completions"))
        self.assertEqual(payload['messages'], [{"role": "user", "content": "prompt"}])

    @patch('src.backend.client.requests.post')
    def test_generate_text_strips_thinking(self, mock_post):
        mock_post.return_value = _chat_response("<think>\nlet me see\n</think>\nIndustry")

        self.assertEqual(client.generate_text("prompt"), "Industry")

    @patch('src.backend.client.requests.post')
    def test_generate_text_raises_on_empty_reply(self, mock_post):
        mock_post.return_value = _chat_response("<think>only thoughts</think>")

        with self.assertRaises(ValueError):
            client.generate_text("prompt")

    @patch('src.backend.client.requests.post')
    def test_embed_text_returns_vector(self, mock_post):
        response = MagicMock()
        response.json.return_value = {"data": [{"embedding": [0.1, 0.2, 0.3]}]}
        mock_post.return_value = response

        self.assertEqual(client.embed_text("some text"), [0.1, 0.2, 0.3])

        url = mock_post.call_args.args[0]
        self.assertTrue(url.endswith("/embeddings"))
        self.assertEqual(mock_post.call_args.kwargs['json']['input'], "some text")

    @patch('src.backend.client.requests.post')
    def test_disabled_when_base_url_is_empty(self, mock_post):
        with patch.dict(os.environ, {"LLM_BASE_URL": ""}):
            self.assertFalse(client.is_llm_enabled())
            self.assertFalse(client.is_llm_ready())
        mock_post.assert_not_called()

    @patch('src.backend.client.requests.post')
    def test_not_ready_when_server_is_down(self, mock_post):
        mock_post.side_effect = client.requests.ConnectionError("refused")

        self.assertFalse(client.is_llm_ready())

    @patch('src.backend.client.requests.post')
    def test_not_ready_when_model_is_missing(self, mock_post):
        response = MagicMock()
        response.ok = False
        response.status_code = 404
        response.text = '{"error":{"message":"model not found, try pulling it first"}}'
        mock_post.return_value = response

        with self.assertLogs('src.backend.logger', level='WARNING') as logs:
            self.assertFalse(client.is_llm_ready())
        self.assertIn("try pulling it first", "\n".join(logs.output))

    @patch('src.backend.client.requests.post')
    def test_ready_when_both_models_answer(self, mock_post):
        embedding = MagicMock()
        embedding.json.return_value = {"data": [{"embedding": [0.1, 0.2]}]}
        mock_post.side_effect = [embedding, _chat_response("OK")]

        self.assertTrue(client.is_llm_ready())
        self.assertEqual(mock_post.call_count, 2)

if __name__ == '__main__':
    unittest.main()
