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

    url: HttpUrl


class UploadLinkResponse(BaseModel):
    """Response model for upload link operations"""

    success: bool
    message: str
    bookmark_id: str = None
    title: str = None
    summary: str = None
    source_tag: str = None


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
