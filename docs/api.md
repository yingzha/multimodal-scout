# Multimodal Scout API Documentation

RESTful API built with FastAPI for content discovery and bookmark management. All endpoints return JSON responses and follow standard HTTP status codes.

## Base URL

`http://localhost:8000`

## Access

The API serves a single local user, who owns all bookmarks and preferences (`LOCAL_USER_EMAIL`, default `local@localhost`). Requests need no credentials.

Browsers may only call the API from the origins listed in `CORS_ORIGINS` (default `http://localhost:3000,http://127.0.0.1:3000`). The default Docker setup publishes the API on `127.0.0.1` only.

## Endpoints

### Health & Status

**GET /**
- **Description**: Basic welcome endpoint
- **Response**: `{"message": "Multimodal Scout API", "version": "1.0.0", "docs": "/docs"}`

**GET /health**
- **Description**: Health check endpoint for monitoring with database connectivity test
- **Response**: `{"status": "healthy", "database": "connected"}`
- **Error Response** (503): `{"detail": "Service unhealthy"}` when database is unreachable

**GET /api/config**
- **Description**: Get application configuration values for client-side validation
- **Response**:
  ```json
  {
    "max_urls_per_request": 5
  }
  ```
- **Purpose**: Allows frontend to dynamically adapt to backend configuration changes

### Topics Management

**GET /api/topics**
- **Description**: Get the default interested topics configured in the backend
- **Caching**: Cached for 1 hour (client & server-side)
- **Headers**: `Cache-Control: public, max-age=3600`
- **Response**:
  ```json
  {
    "topics": [
      "multimodal", 
      "image understanding",
      "video understanding",
      "visual agents"
    ]
  }
  ```

**GET /api/user/preferences**
- **Description**: Get the custom topics saved for the local user
- **Response**:
  ```json
  {
    "custom_topics": ["robotics", "world models"]
  }
  ```

**PUT /api/user/preferences**
- **Description**: Replace the saved custom topics
- **Request Body**:
  ```json
  {
    "custom_topics": ["robotics", "world models"]
  }
  ```
- **Response**: `{"success": true, "message": "Preferences updated successfully"}`

**GET /api/keywords/suggestions**
- **Description**: Suggest up to 5 new keywords based on the titles and summaries of saved bookmarks. Calls the chat model, so it can take several seconds
- **Response**:
  ```json
  {
    "suggested_keywords": ["vision language models", "video agents"],
    "existing_keywords": ["robotics"],
    "total_bookmarks_analyzed": 12
  }
  ```

### Content Management

**POST /api/content/search**
- **Description**: Search for content from various sources based on topics and time range
- **Request Body**:
  ```json
  {
    "selectedDays": 7,
    "topics": ["multimodal agents", "computer vision"],
    "maxResults": 10,
    "researchRatio": 0.5,
    "sessionId": "optional-session-id",
    "discoveryMode": false
  }
  ```
- **Parameters**:
  - `selectedDays` (required): Number of days to look back
  - `topics` (required): Array of keywords to search for
  - `maxResults` (optional): Maximum results to return (default: 10)
  - `researchRatio` (optional): Ratio of research vs industry content (0.0-1.0, default: 0.5)
  - `sessionId` (optional): Session identifier for tracking
  - `discoveryMode` (optional): Enable random content discovery (default: false)
- **Response**:
  ```json
  {
    "items": [
      {
        "title": "MIRIX: Multi-Agent Memory System for LLM-Based Agents",
        "link": "https://example.com/paper",
        "summary": "AI-generated summary of the content...",
        "source": "Research",
        "created_at": "2025-01-08T10:30:00Z",
        "comment_insights": "• Main technical concerns about memory efficiency\n• Community discussion on real-world applications\n• Comparison with existing agent frameworks",
        "comment_count": 42
      }
    ],
    "total_count": 15,
    "sources": ["Hugging Face", "Hacker News"]
  }
  ```
- **Note**: `comment_insights` and `comment_count` fields are only included for Hacker News sources, and only when comment insights are enabled (see below).

**POST /api/content/search/stream**
- **Description**: Streaming version of content search with real-time progress updates via Server-Sent Events (SSE)
- **Request Body**: Same as `/api/content/search`
- **Response**: Server-Sent Events stream with progress updates and final result
- **Content-Type**: `text/event-stream`
- **Event Types**:
  - `status`: General status messages
  - `start`: Search started
  - `progress`: Progress updates during processing
  - `complete`: Step completion
  - `info`/`warning`: Informational messages
  - `error`: Error occurred
  - `result`: Final search results
- **Example Events**:
  ```
  data: {"type": "start", "message": "Starting content search..."}
  data: {"type": "progress", "message": "Generating summaries..."}
  data: {"type": "result", "data": {"items": [...], "total_count": 10, "sources": [...]}}
  data: [DONE]
  ```

**POST /api/content**
- **Description**: Create content items from user-provided URLs with automatic processing
- **Request Body**:
  ```json
  {
    "urls": [
      "https://example.com/article1",
      "https://example.com/article2"
    ]
  }
  ```
- **Constraints**:
  - Maximum 5 URLs per request (configurable via `/api/config`)
  - URLs must be valid HTTP/HTTPS links
- **Response**:
  ```json
  {
    "success": true,
    "message": "Successfully processed all 2 URLs",
    "results": [
      {
        "url": "https://example.com/article1",
        "title": "Extracted Article Title",
        "summary": "AI-generated summary...",
        "source_tag": "Research",
        "bookmark_id": "uuid-here"
      }
    ],
    "failed_urls": []
  }
  ```
- **Error Responses**:
  - **400**: URL count exceeds limit
    ```json
    {
      "error": "validation_error",
      "message": "Maximum 5 URLs allowed per request",
      "provided": 8,
      "limit": 5
    }
    ```
- **Features**:
  - Batch processing of multiple URLs
  - Automatic title extraction from webpages
  - AI-powered content summarization with the configured model
  - Smart categorization as Research, Industry, or General
  - Automatic bookmark creation for processed content
  - Partial success handling (some URLs may fail while others succeed)

### Bookmark Management

#### Collection Operations

**GET /api/bookmarks**
- **Description**: Get all user bookmarks with optional filtering
- **Query Parameters** (optional):
  - `limit` (default: 100): Maximum number of bookmarks to return
  - `days`: Filter bookmarks from the last N days
- **Response**: Same format as content search but only bookmarked items
  ```json
  {
    "items": [
      {
        "title": "Advanced AI Discussion",
        "link": "https://news.ycombinator.com/item?id=123456",
        "summary": "**Content Summary:**\nOriginal article summary...\n\n**Community Discussion (25 comments):**\n• Key technical insights from practitioners\n• Industry adoption challenges discussed\n• Performance benchmarks shared",
        "source": "Industry",
        "created_at": "2025-01-08T10:30:00Z",
        "comment_insights": "• Key technical insights from practitioners\n• Industry adoption challenges discussed\n• Performance benchmarks shared",
        "comment_count": 25
      }
    ],
    "total_count": 25,
    "sources": ["Bookmarks"]
  }
  ```
- **Note**: For HN bookmarks, the API returns two-section summaries combining original content with community insights.

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
- **Note**: Adding a link that is already bookmarked succeeds and returns the existing bookmark's id

**DELETE /api/bookmarks**
- **Description**: Remove a bookmark by its link
- **Query Parameters**:
  - `link` (required): URL of the bookmarked item
- **Response**: `{"success": true, "message": "Bookmark removed successfully", "bookmark_id": null}`, or `{"success": false, "message": "Bookmark not found", "bookmark_id": null}` when no bookmark has that link

**GET /api/bookmarks/check**
- **Description**: Check whether a link is bookmarked
- **Query Parameters**:
  - `link` (required): URL to check
- **Response**: `{"is_bookmarked": true}`

**PUT /api/bookmarks/summary**
- **Description**: Replace the summary of a bookmark, identified by its link
- **Query Parameters**:
  - `link` (required): URL of the bookmarked item
  - `summary` (required): New summary text
- **Response**: `{"success": true, "message": "Bookmark summary updated successfully", "bookmark_id": null}`

#### Individual Resource Operations (RESTful)

**GET /api/bookmarks/{bookmark_id}**
- **Description**: Get a specific bookmark by ID
- **Path Parameters**:
  - `bookmark_id` (required): UUID of the bookmark
- **Response**:
  ```json
  {
    "id": "uuid-here",
    "title": "Article Title",
    "link": "https://news.ycombinator.com/item?id=123456",
    "summary": "**Content Summary:**\nOriginal article summary...\n\n**Community Discussion (18 comments):**\n• Technical implementation details discussed\n• Community feedback on performance\n• Alternative approaches suggested",
    "source": "Research",
    "created_at": "2025-01-08T10:30:00Z",
    "summary_edited": false,
    "comment_insights": "• Technical implementation details discussed\n• Community feedback on performance\n• Alternative approaches suggested",
    "comment_count": 18
  }
  ```
- **Note**: For Hacker News bookmarks, `comment_insights` and `comment_count` are included. The `summary` field contains the two-section format combining content summary and community discussion.
- **Error Response** (404): `{"detail": "Bookmark not found"}`

**DELETE /api/bookmarks/{bookmark_id}**
- **Description**: Delete a specific bookmark by ID
- **Path Parameters**:
  - `bookmark_id` (required): UUID of the bookmark
- **Response**:
  ```json
  {
    "message": "Bookmark deleted successfully"
  }
  ```
- **Error Response** (404): `{"detail": "Bookmark not found"}`

**PATCH /api/bookmarks/{bookmark_id}**
- **Description**: Update a bookmark's summary by ID
- **Path Parameters**:
  - `bookmark_id` (required): UUID of the bookmark
- **Request Body**:
  ```json
  {
    "summary": "Updated summary text..."
  }
  ```
- **Response**:
  ```json
  {
    "message": "Bookmark updated successfully"
  }
  ```
- **Error Response** (404): `{"detail": "Bookmark not found"}`

#### Export Operations

**GET /api/bookmarks/export/chrome**
- **Description**: Export bookmarks in Chrome-compatible HTML format with optional filtering
- **Query Parameters** (optional):
  - `selected_tags`: Comma-separated list of source tags to filter
  - `search_query`: Text search filter for title/summary
  - `export_format`: `html` (default) or `markdown`
- **Response**: HTML or Markdown file download
- **Content-Type**: `text/html` or `text/markdown`
- **Headers**: `Content-Disposition: attachment; filename="multimodal_scout_chrome_bookmarks_{timestamp}.html"`
- **Features**:
  - Creates "Multimodal Scout" folder with "Research" and "Industry" subfolders
  - Automatically categorizes bookmarks based on source tags
  - Compatible with Chrome's bookmark import feature
  - Support for filtered exports based on current view


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

## Hacker News Comment Insights

The pipeline can generate AI-powered insights from Hacker News discussions. This is off by default; set `COMMENT_INSIGHTS_ENABLED = True` in `src/backend/constants.py` to turn it on.

### Features
- **Smart Caching**: 5-minute TTL prevents redundant processing of recently updated sources
- **Minimum Threshold**: Only posts with 10+ comments receive insights
- **Batch Processing**: Efficient database operations for multiple HN sources
- **Two-Section Display**: Combined content summary and community discussion format

### Response Fields
- `comment_insights` (string, optional): AI-generated bullet points of key community discussion themes
- `comment_count` (integer, optional): Total number of comments on the HN post
- Enhanced `summary` field: For HN sources, includes both content and community sections

### Processing Logic
- Comments are fetched from the Hacker News API during automated pipeline runs
- AI analysis identifies main themes, technical concerns, and expert insights
- Results are cached with 5-minute TTL to optimize performance
- Only meaningful updates (10+ new comments) trigger reprocessing

### Example Enhanced Summary Format
```
**Content Summary:**
[Original article summary from AI analysis]

**Community Discussion (42 comments):**
• Main technical concerns about implementation complexity
• Community sharing real-world deployment experiences  
• Debate over performance vs. accuracy tradeoffs
• Suggestions for alternative approaches and frameworks
```
