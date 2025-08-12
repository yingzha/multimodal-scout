import unittest
import json
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient

from src.backend.app import app


class TestApp(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)

    @patch('src.backend.app.process_content_pipeline')
    def test_fetch_top_items_endpoint(self, mock_pipeline):
        # --- Setup Mock ---
        # Mock the final 'result' event from the pipeline
        mock_pipeline.return_value = [
            {'type': 'status', 'message': '...'}, 
            {'type': 'result', 'data': {
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
        ]

        # --- API Call ---
        response = self.client.post("/api/fetch", json={
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
        mock_pipeline.assert_called_once_with(topics=["ai"], max_results=1, research_ratio=0.5, selected_days=7)

    @patch('src.backend.app.process_content_pipeline')
    def test_fetch_top_items_stream_endpoint(self, mock_pipeline):
        # --- Setup Mock ---
        # Mock a sequence of events yielded by the pipeline
        mock_pipeline.return_value = (
            e for e in [
                {'type': 'start', 'message': 'Starting'},
                {'type': 'progress', 'processed': 50, 'total': 100},
                {'type': 'complete', 'message': 'Finished'},
                {'type': 'result', 'data': {'items': [], 'total_count': 0, 'sources': []}}
            ]
        )

        # --- API Call ---
        response = self.client.post("/api/fetch-stream", json={
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

    def test_get_topics_endpoint(self):
        response = self.client.get("/api/topics")
        self.assertEqual(response.status_code, 200)
        self.assertIn('topics', response.json())

if __name__ == '__main__':
    unittest.main()
