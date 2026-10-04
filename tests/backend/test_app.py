import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient

from src.backend.app import app, get_current_user


class TestApp(unittest.TestCase):

    def setUp(self):
        app.dependency_overrides[get_current_user] = lambda: "test-user"
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()

    @patch('src.backend.app.search_db_sources')
    def test_fetch_top_items_endpoint(self, mock_pipeline):
        # --- Setup Mock ---
        # Mock the final 'result' event from the pipeline as an async generator
        async def mock_async_generator():
            yield {'type': 'status', 'message': '...'}
            yield {'type': 'result', 'data': {
                'items': [{
                    'title': 'Test Item', 
                    'link': 'http://example.com', 
                    'summary': 'Test summary', 
                    'source': 'Test Source', 
                    'created_at': '2023-10-27T00:00:00'
                }],
                'total_count': 1,
                'sources': ['Test Source']
            }}
        
        mock_pipeline.return_value = mock_async_generator()

        # --- API Call ---
        response = self.client.post("/api/content/search", json={
            "selectedDays": 7,
            "topics": ["ai"],
            "maxResults": 1,
            "researchRatio": 0.5
        })

        # --- Assertions ---
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['total_count'], 1)
        self.assertEqual(data['items'][0]['title'], 'Test Item')
        mock_pipeline.assert_called_once_with(topics=["ai"], max_results=1, research_ratio=0.5, selected_days=7, session_id=None, discovery_mode=False, user_id="test-user")

    @patch('src.backend.app.search_db_sources')
    def test_fetch_top_items_stream_endpoint(self, mock_pipeline):
        # --- Setup Mock ---
        # Mock a sequence of events yielded by the pipeline as an async generator
        async def mock_async_generator():
            yield {'type': 'start', 'message': 'Starting'}
            yield {'type': 'progress', 'processed': 50, 'total': 100}
            yield {'type': 'complete', 'message': 'Finished'}
            yield {'type': 'result', 'data': {'items': [], 'total_count': 0, 'sources': []}}
        
        mock_pipeline.return_value = mock_async_generator()

        # --- API Call ---
        response = self.client.post("/api/content/search/stream", json={
            "selectedDays": 7,
            "topics": ["ai"],
            "maxResults": 1,
            "researchRatio": 0.5
        })

        # --- Assertions ---
        self.assertEqual(response.status_code, 200)
        self.assertIn('text/event-stream', response.headers['content-type'])

        # Check the content of the stream
        lines = response.text.strip().split('\n\n')
        self.assertIn('data: {"type": "start", "message": "Starting"}', lines)
        self.assertIn('data: {"type": "progress", "processed": 50, "total": 100}', lines)
        self.assertIn('data: {"type": "complete", "message": "Finished"}', lines)
        self.assertIn('data: [DONE]', lines)
        self.assertNotIn('access-control-allow-origin', response.headers)

    @patch('src.backend.app.search_db_sources')
    def test_discovery_mode_endpoint(self, mock_pipeline):
        """Test that discovery mode is passed correctly to the pipeline."""
        async def mock_async_generator():
            yield {'type': 'result', 'data': {'items': [], 'total_count': 0, 'sources': []}}
        
        mock_pipeline.return_value = mock_async_generator()
        
        # Test with discovery mode enabled
        response = self.client.post("/api/content/search", json={
            "selectedDays": 7,
            "topics": ["test"],
            "discoveryMode": True
        })
        
        self.assertEqual(response.status_code, 200)
        
        # Verify pipeline was called with discovery_mode=True
        mock_pipeline.assert_called_once()
        call_args, call_kwargs = mock_pipeline.call_args
        self.assertEqual(call_kwargs['discovery_mode'], True)

    def test_get_topics_endpoint(self):
        response = self.client.get("/api/topics")
        self.assertEqual(response.status_code, 200)
        self.assertIn('topics', response.json())

    @patch('src.backend.app.db_manager.is_bookmarked')
    def test_bookmarks_need_no_login(self, mock_is_bookmarked):
        mock_is_bookmarked.return_value = True

        # No Authorization header: the local user owns all bookmarks
        response = self.client.get("/api/bookmarks/check", params={"link": "http://example.com"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"is_bookmarked": True})
        mock_is_bookmarked.assert_called_once_with("test-user", "http://example.com")

    def test_auth_and_pipeline_endpoints_are_gone(self):
        self.assertEqual(self.client.post("/api/auth/google", json={"id_token": "x"}).status_code, 404)
        self.assertEqual(self.client.get("/api/auth/me").status_code, 404)
        self.assertEqual(self.client.post("/pipeline").status_code, 404)

    def test_cors_allows_only_the_frontend_origin(self):
        allowed = self.client.get("/api/config", headers={"Origin": "http://localhost:3000"})
        self.assertEqual(allowed.headers.get('access-control-allow-origin'), "http://localhost:3000")

        denied = self.client.get("/api/config", headers={"Origin": "http://evil.example"})
        self.assertNotIn('access-control-allow-origin', denied.headers)

if __name__ == '__main__':
    unittest.main()
