# API Documentation

The Multimodal Scout backend provides a RESTful API built with FastAPI. All endpoints return JSON responses and follow standard HTTP status codes.

## Base URL

```
http://localhost:8000
```

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
- **Caching**: Cached for 30 minutes (client & server-side)
- **Headers**: `Cache-Control: public, max-age=1800`
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
  - `selectedDays` (required): Number of days to look back (1-30)
  - `topics` (required): Array of keywords to search for
  - `maxResults` (optional): Maximum results to return (5-50, default: 10)
  - `researchRatio` (optional): Ratio of research vs industry content (0.0-1.0, default: 0.5)
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
- **Request Body**: Same as `/api/content/search`
- **Response**: Server-Sent Events stream with progress updates and final result
- **Content-Type**: `text/event-stream`
- **Event Types**:
  - `status`: General status messages
  - `progress`: Progress updates with percentage (0-100)
  - `error`: Error occurred
  - `result`: Final search results
- **Example Events**:
  ```
  data: {"type": "status", "message": "Starting search..."}
  data: {"type": "progress", "message": "Generating summaries...", "processed": 50, "total": 100}
  data: {"type": "result", "data": {"items": [...], "total_count": 10}}
  ```

**POST /api/content**
- **Description**: Create content item from user-provided link with automatic processing
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
- **Description**: Get all user bookmarks
- **Authentication**: Required.
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

#### Legacy Endpoints (Deprecated)

**DELETE /api/bookmarks**
- **Description**: Remove a bookmark by URL (deprecated - use DELETE /api/bookmarks/{id})
- **Authentication**: Required.
- **Query Parameters**: 
  - `link` (required): URL of the bookmark to remove

**GET /api/bookmarks/check**
- **Description**: Check if a URL is bookmarked (deprecated)
- **Authentication**: Required.
- **Query Parameters**:
  - `link` (required): URL to check

**PUT /api/bookmarks/summary**
- **Description**: Update bookmark summary by URL (deprecated - use PATCH /api/bookmarks/{id})
- **Authentication**: Required.
- **Query Parameters**:
  - `link` (required): URL of the bookmark
  - `summary` (required): New summary text

#### Export Operations

**GET /api/bookmarks/export**
- **Description**: Export all bookmarks to Excel (.xlsx) file
- **Authentication**: Required.
- **Response**: Excel file download with columns: Title, Summary, Link, Source, Date Added
- **Content-Type**: `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`
- **Headers**: `Content-Disposition: attachment; filename="multimodal_scout_bookmarks_{timestamp}.xlsx"`

**GET /api/bookmarks/export/chrome**
- **Description**: Export bookmarks in Chrome-compatible HTML format
- **Authentication**: Required.
- **Response**: HTML file that can be imported into Chrome browser
- **Content-Type**: `text/html`
- **Headers**: `Content-Disposition: attachment; filename="multimodal_scout_chrome_bookmarks_{timestamp}.html"`
- **Features**:
  - Creates "Multimodal Scout" folder with "Research" and "Industry" subfolders
  - Automatically categorizes bookmarks based on source tags
  - Compatible with Chrome's bookmark import feature


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