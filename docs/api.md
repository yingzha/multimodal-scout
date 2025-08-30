# Multimodal Scout API Documentation

RESTful API built with FastAPI for content discovery and bookmark management. All endpoints return JSON responses and follow standard HTTP status codes.

## Base URL

- **Local Development**: `http://localhost:8000`
- **Production**: `https://your-backend-service.region.run.app`

## Authentication

Endpoints related to user-specific data (like bookmarks) are protected and require a bearer token in the `Authorization` header.

`Authorization: Bearer <your_session_token>`

You can obtain a session token by using the `/api/auth/login` or `/api/auth/register` endpoints.

### Authentication Endpoints

**POST /api/auth/register**
- **Description**: Register a new user.
- **Request Body**:
  ```json
  {
    "email": "user@example.com",
    "password": "your_password",
    "username": "your_username"
  }
  ```
- **Response**:
  ```json
  {
    "success": true,
    "user_id": "user-uuid-here",
    "session_token": "session-token-here"
  }
  ```

**POST /api/auth/login**
- **Description**: Log in a user.
- **Request Body**:
  ```json
  {
    "email": "user@example.com",
    "password": "your_password"
  }
  ```
- **Response**:
  ```json
  {
    "success": true,
    "session_token": "session-token-here"
  }
  ```

**POST /api/auth/logout**
- **Description**: Log out a user by invalidating the session token.
- **Authentication**: Required.
- **Response**:
  ```json
  {
    "success": true,
    "message": "Logged out successfully"
  }
  ```

**GET /api/auth/me**
- **Description**: Get information about the currently authenticated user.
- **Authentication**: Required.
- **Response**:
  ```json
  {
    "user_id": "user-uuid-here",
    "email": "user@example.com",
    "username": "your_username"
  }
  ```

## Endpoints

### Health & Status

**GET /**
- **Description**: Basic welcome endpoint
- **Response**: `{"message": "Multimodal Scout API", "version": "1.0.0", "docs": "/docs"}`

**GET /health**
- **Description**: Health check endpoint for monitoring with database connectivity test
- **Response**: `{"status": "healthy", "database": "connected"}`
- **Error Response** (503): `{"detail": "Service unhealthy"}` when database is unreachable

### Topics Management

**GET /api/topics**
- **Description**: Get the default interested topics configured in the backend
- **Authentication**: Not required
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

### Content Management

**POST /api/content/search**
- **Description**: Search for content from various sources based on topics and time range
- **Authentication**: Optional (guest users: 3 searches/day, authenticated: unlimited)
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
  - `selectedDays` (required): Number of days to look back (1-30)
  - `topics` (required): Array of keywords to search for
  - `maxResults` (optional): Maximum results to return (5-50, default: 10)
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
        "created_at": "2025-01-08T10:30:00Z"
      }
    ],
    "total_count": 15,
    "sources": ["Hugging Face", "Hacker News"]
  }
  ```

**POST /api/content/search/stream**
- **Description**: Streaming version of content search with real-time progress updates via Server-Sent Events (SSE)
- **Authentication**: Optional (same rate limits as `/api/content/search`)
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
- **Description**: Create content item from user-provided link with automatic processing
- **Authentication**: Required
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
    "message": "Link processed and added to bookmarks as 'Research' content",
    "bookmark_id": "uuid-here",
    "title": "Extracted Article Title",
    "summary": "AI-generated summary...",
    "source_tag": "Research"
  }
  ```
- **Features**:
  - Automatic title extraction from webpage
  - AI-powered content summarization using Google Gemini
  - Smart categorization as Research, Industry, or General
  - Automatic bookmark creation for processed content

### Bookmark Management

#### Collection Operations

**GET /api/bookmarks**
- **Description**: Get all user bookmarks with optional filtering
- **Authentication**: Required
- **Query Parameters** (optional):
  - `limit` (default: 100): Maximum number of bookmarks to return
  - `days`: Filter bookmarks from the last N days
- **Response**: Same format as content search but only bookmarked items
  ```json
  {
    "items": [...],
    "total_count": 25,
    "sources": ["Bookmarks"]
  }
  ```

**POST /api/bookmarks**
- **Description**: Add a new bookmark
- **Authentication**: Required.
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

#### Individual Resource Operations (RESTful)

**GET /api/bookmarks/{bookmark_id}**
- **Description**: Get a specific bookmark by ID
- **Authentication**: Required.
- **Path Parameters**:
  - `bookmark_id` (required): UUID of the bookmark
- **Response**:
  ```json
  {
    "id": "uuid-here",
    "title": "Article Title",
    "link": "https://example.com/article",
    "summary": "Article summary...",
    "source": "Research",
    "created_at": "2025-01-08T10:30:00Z",
    "summary_edited": false
  }
  ```
- **Error Response** (404): `{"detail": "Bookmark not found"}`

**DELETE /api/bookmarks/{bookmark_id}**
- **Description**: Delete a specific bookmark by ID
- **Authentication**: Required.
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
- **Authentication**: Required.
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

**GET /api/bookmarks/export**
- **Description**: Export all bookmarks to Excel (.xlsx) file
- **Authentication**: Required.
- **Response**: Excel file download with columns: Title, Summary, Link, Source, Date Added
- **Content-Type**: `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`
- **Headers**: `Content-Disposition: attachment; filename="multimodal_scout_bookmarks_{timestamp}.xlsx"`

**GET /api/bookmarks/export/chrome**
- **Description**: Export bookmarks in Chrome-compatible HTML format with optional filtering
- **Authentication**: Required
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

## Rate Limiting

The API implements rate limiting for guest users to ensure fair usage:

- **Authenticated Users**: Unlimited access to all endpoints
- **Guest Users**: 3 searches per day for `/api/content/search` and `/api/content/search/stream` (rate limited by IP address)
- **Window**: 24-hour rolling window

### Rate Limit Response

When rate limit is exceeded, the API returns:

**Status Code**: 429 (Too Many Requests)

**Response**:
```json
{
  "error": "rate_limit_exceeded",
  "message": "Daily search limit exceeded for guest users (3 searches/day). Please register for unlimited access.",
  "reset_in_hours": 12.5,
  "current_usage": 3,
  "daily_limit": 3
}
```

### Hybrid Access Model

The API supports both authenticated and guest access:
- **Guest Access**: Limited searches per day, no bookmark management
- **Authenticated Access**: Unlimited searches, full bookmark management, export capabilities
