from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, HttpUrl, EmailStr


class SourceSchema(BaseModel):
    """
    Represents the data schema for a source, providing validation and type hints.
    """

    title: str
    authors: List[str]
    link: HttpUrl
    source_link: HttpUrl
    summary: Optional[str] = None
    keywords: Optional[List[str]] = None
    tags: List[str]  # A list of tags for categorization (e.g., 'research', 'industry').
    date: datetime


class FetchRequest(BaseModel):
    """Request model for fetching top items"""

    selectedDays: int
    topics: List[str]
    maxResults: int = 10  # Default to 10 results
    researchRatio: float = 0.5  # Default to 50/50 research/industry balance
    sessionId: Optional[str] = None  # Browser session ID for tracking new cards
    discoveryMode: bool = False  # Enable discovery mode (ignores topics, uses AI)


class TopicResponse(BaseModel):
    """Response model for default topics"""

    topics: List[str]


class ItemResponse(BaseModel):
    """Response model for individual items"""

    title: str
    link: str
    summary: str
    source: str
    created_at: str
    summary_edited: bool = False
    is_new: bool = False  # True if this card is new for the user session
    matched_keywords: List[str] = []  # Keywords that matched during search
    comment_insights: Optional[str] = None  # HN comment insights if available
    comment_count: Optional[int] = None  # Number of comments for HN posts


class FetchResponse(BaseModel):
    """Response model for fetched items"""

    items: List[ItemResponse]
    total_count: int
    sources: List[str]


class BookmarkRequest(BaseModel):
    """Request model for bookmarking"""

    title: str
    link: str
    source: str
    summary: str = ""


class BookmarkResponse(BaseModel):
    """Response model for bookmark operations"""

    success: bool
    message: str
    bookmark_id: str = None


class UploadLinkRequest(BaseModel):
    """Request model for uploading user links"""

    urls: List[HttpUrl]  # Changed to support multiple URLs (max 5)


class UploadLinkResponse(BaseModel):
    """Response model for upload link operations"""

    success: bool
    message: str
    results: List[dict] = []  # List of results for multiple URLs
    failed_urls: List[str] = []  # URLs that failed to process


class UserRegistrationRequest(BaseModel):
    """Request model for user registration"""

    email: EmailStr
    password: str
    username: str


class UserLoginRequest(BaseModel):
    """Request model for user login"""

    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    """Response model for authentication operations"""

    success: bool
    message: str
    session_token: str = None
    user_id: str = None


class UserResponse(BaseModel):
    """Response model for user information"""

    user_id: str
    email: str
    username: str
    created_at: str
    last_login: str = None


class ConfigResponse(BaseModel):
    """Response model for application configuration"""

    max_urls_per_request: int
    user_content_daily_limit: int
    guest_daily_limit: int


class UserPreferencesResponse(BaseModel):
    """Response model for user preferences"""

    custom_topics: List[str]


class UpdateUserPreferencesRequest(BaseModel):
    """Request model for updating user preferences"""

    custom_topics: List[str]


class CommentInsight(BaseModel):
    """Response model for Hacker News comment insights"""

    title: str
    link: HttpUrl
    comment_count: int
    insights: Optional[str] = None
    generated_at: Optional[str] = None


class CommentInsightRequest(BaseModel):
    """Request model for generating comment insights"""

    link: HttpUrl
