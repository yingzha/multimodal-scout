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
- **Description**: Fetch and filter articles based on topics and time range using Smart Balanced Search
- **Request Body**:
  ```json
  {
    "selectedDays": 7,
    "topics": ["multimodal agents", "computer vision", "custom topic"],
    "maxResults": 10,
    "researchRatio": 0.5
  }
  ```
- **Parameters**:
  - `selectedDays` (required): Number of days to look back (1-7)
  - `topics` (required): Array of keywords to search for
  - `maxResults` (optional): Maximum results to return (5-50, default: 10)
  - `researchRatio` (optional): Ratio of research vs industry content (0.0-1.0, default: 0.5)
- **Note**: Smart Balanced Search is always enabled with optimized thresholds (research: 0.65, industry: 0.55)
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

**POST /api/fetch-stream**
- **Description**: Streaming version of `/api/fetch` with real-time progress updates via Server-Sent Events (SSE)
- **Request Body**: Same as `/api/fetch`
- **Response**: Server-Sent Events stream with progress updates and final result
- **Content-Type**: `text/event-stream`
- **Event Types**:
  - `status`: General status messages
  - `progress`: Progress updates with percentage (0-100)
  - `complete`: Processing complete
  - `error`: Error occurred
  - `result`: Final filtered results
- **Example Events**:
  ```
  data: {"type": "status", "message": "Starting fetch..."}
  data: {"type": "progress", "message": "Generating summaries...", "processed": 50, "total": 100}
  data: {"type": "result", "data": {"items": [...], "total_count": 10}}
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
  - `link` (required): URL of the article to update
  - `summary` (required): The new summary text
- **Example**: `PUT /api/bookmarks/summary?link=https%3A//example.com/article&summary=New%20summary%20text`
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

**PUT /api/bookmarks/summary**
- **Description**: Update the summary of a bookmarked item (user-edited summaries take priority in search results)
- **Request Body**:
  ```json
  {
    "link": "https://example.com/article",
    "summary": "Updated summary text..."
  }
  ```
- **Response**:
  ```json
  {
    "success": true,
    "message": "Summary updated successfully"
  }
  ```

**GET /api/bookmarks/export**
- **Description**: Export all bookmarks to an Excel (.xlsx) file
- **Response**: Excel file download with columns: Title, Summary, Source URL, Date
- **Content-Type**: `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`
- **Headers**: `Content-Disposition: attachment; filename="bookmarks.xlsx"`

### Content Upload

**POST /api/upload-link**  
- **Description**: Upload and process a custom URL with automatic AI summary generation and categorization
- **Request Body**:
  ```json
  {
    "url": "https://example.com/article"
  }
  ```
- **Response**:
  ```json
  {
    "success": true,
    "message": "Link processed and bookmarked successfully",
    "processed_item": {
      "title": "Extracted Article Title",
      "link": "https://example.com/article", 
      "summary": "AI-generated summary...",
      "source": "Research",
      "created_at": "2025-01-08T10:30:00Z"
    }
  }
  ```
- **Features**:
  - Automatic title extraction from webpage
  - AI-powered content summarization using Google Gemini
  - Smart categorization as Research, Industry, or General
  - Intelligent URL pattern analysis for source classification
  - Automatic bookmark creation for processed content

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