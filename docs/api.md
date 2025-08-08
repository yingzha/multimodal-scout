# API Documentation

The Multimodal Scout backend provides a RESTful API built with FastAPI. All endpoints return JSON responses and follow standard HTTP status codes.

## Base URL

```
http://localhost:8000
```

## Authentication

Currently, no authentication is required for API access.

## Endpoints

### Health Check

**GET /** 
- **Description**: Check if the API is running
- **Response**: `{"message": "Multimodal Scout API is running", "status": "healthy"}`

### Topics Management

**GET /api/topics**
- **Description**: Get the default interested topics configured in the backend
- **Response**:
  ```json
  {
    "topics": [
      "open-source multimodal models",
      "multimodal APIs", 
      "multimodal retrieval",
      "document processing",
      "image processing",
      "video processing",
      "multimodal agents"
    ]
  }
  ```

### Content Fetching

**POST /api/fetch**
- **Description**: Fetch and filter articles based on topics and time range
- **Request Body**:
  ```json
  {
    "selectedDays": 7,
    "topics": ["multimodal agents", "computer vision", "custom topic"]
  }
  ```
- **Response**:
  ```json
  {
    "items": [
      {
        "title": "MIRIX: Multi-Agent Memory System for LLM-Based Agents",
        "link": "https://example.com/paper",
        "summary": "AI-generated summary of the content...",
        "source": "Research",
        "created_at": "2025-01-08T10:30:00Z"
      }
    ],
    "total_count": 15,
    "sources": ["Hugging Face", "Hacker News"]
  }
  ```

### Bookmark Management

**POST /api/bookmarks**
- **Description**: Add a new bookmark
- **Request Body**:
  ```json
  {
    "title": "Article Title",
    "link": "https://example.com/article", 
    "source": "Research",
    "summary": "Article summary..."
  }
  ```
- **Response**:
  ```json
  {
    "success": true,
    "message": "Bookmark added successfully",
    "bookmark_id": "uuid-here"
  }
  ```

**DELETE /api/bookmarks**
- **Description**: Remove a bookmark by URL
- **Query Parameters**: 
  - `link` (required): URL of the article to remove
- **Example**: `DELETE /api/bookmarks?link=https://example.com/article`
- **Response**:
  ```json
  {
    "success": true,
    "message": "Bookmark removed successfully"
  }
  ```

**GET /api/bookmarks**
- **Description**: Get all user bookmarks
- **Response**: Same format as `/api/fetch` but only bookmarked items

**GET /api/bookmarks/check**
- **Description**: Check if a URL is bookmarked
- **Query Parameters**:
  - `link` (required): URL to check
- **Example**: `GET /api/bookmarks/check?link=https://example.com/article`
- **Response**:
  ```json
  {
    "is_bookmarked": true
  }
  ```

## Interactive Documentation

FastAPI automatically generates interactive API documentation:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Error Handling

The API uses standard HTTP status codes:

- **200**: Success
- **404**: Resource not found  
- **422**: Validation error
- **500**: Internal server error

Error responses include details:
```json
{
  "detail": "Error message describing what went wrong"
}
```

## Rate Limiting

Currently no rate limiting is implemented, but it's recommended for production deployments.