import unittest
import asyncio
from unittest.mock import patch
import numpy as np

from src.backend.config import config
from src.backend.search import _get_embedding

class TestSearch(unittest.TestCase):

    @patch('src.backend.database.db_manager.get_embedding_for_text')
    @patch('src.backend.database.db_manager.add_embedding_for_text')
    @patch('src.backend.search.embed_text')
    def test_get_embedding_cached(self, mock_embed_text, mock_add_embedding, mock_get_embedding):
        # Setup: Embedding is found in cache
        mock_get_embedding.return_value = [0.1, 0.2, 0.3]
        text = "test text"

        # Call the async function
        async def run_test():
            return await _get_embedding(text)

        embedding = asyncio.run(run_test())

        # Assertions
        self.assertTrue(np.array_equal(embedding, np.array([0.1, 0.2, 0.3])))
        mock_get_embedding.assert_called_once_with(text, config.llm_embedding_model)
        mock_embed_text.assert_not_called() # Should not call API if cached
        mock_add_embedding.assert_not_called() # Should not add to cache if cached

    @patch('src.backend.database.db_manager.get_embedding_for_text')
    @patch('src.backend.database.db_manager.add_embedding_for_text')
    @patch('src.backend.search.embed_text')
    def test_get_embedding_generated_and_cached(self, mock_embed_text, mock_add_embedding, mock_get_embedding):
        # Setup: Embedding not found in cache, needs generation
        mock_get_embedding.return_value = None
        mock_embed_text.return_value = [0.4, 0.5, 0.6]

        text = "new text"

        # Call the async function
        async def run_test():
            return await _get_embedding(text)

        embedding = asyncio.run(run_test())

        # Assertions
        self.assertTrue(np.array_equal(embedding, np.array([0.4, 0.5, 0.6])))
        mock_get_embedding.assert_called_once_with(text, config.llm_embedding_model)
        mock_embed_text.assert_called_once_with(text)
        mock_add_embedding.assert_called_once_with(text, [0.4, 0.5, 0.6], config.llm_embedding_model)

    @patch('src.backend.database.db_manager.get_embedding_for_text')
    @patch('src.backend.database.db_manager.add_embedding_for_text')
    @patch('src.backend.search.embed_text')
    def test_get_embedding_api_disabled(self, mock_embed_text, mock_add_embedding, mock_get_embedding):
        # Temporarily disable the LLM for this test
        with patch('src.backend.search.is_llm_enabled', return_value=False):
            text = "disabled test"

            # Call the async function
            async def run_test():
                return await _get_embedding(text)

            embedding = asyncio.run(run_test())
            self.assertTrue(np.array_equal(embedding, np.array([])))
            mock_get_embedding.assert_not_called()
            mock_embed_text.assert_not_called()
            mock_add_embedding.assert_not_called()

    @patch('src.backend.database.db_manager.get_embedding_for_text')
    @patch('src.backend.database.db_manager.add_embedding_for_text')
    @patch('src.backend.search.embed_text')
    def test_get_embedding_api_error(self, mock_embed_text, mock_add_embedding, mock_get_embedding):
        # Setup: API call raises an exception
        mock_get_embedding.return_value = None
        mock_embed_text.side_effect = Exception("API Error")
        text = "error text"

        # Call the async function
        async def run_test():
            return await _get_embedding(text)

        embedding = asyncio.run(run_test())

        self.assertTrue(np.array_equal(embedding, np.array([])))
        mock_get_embedding.assert_called_once_with(text, config.llm_embedding_model)
        mock_embed_text.assert_called_once_with(text)
        mock_add_embedding.assert_not_called() # Should not add to cache on error

if __name__ == '__main__':
    unittest.main()
