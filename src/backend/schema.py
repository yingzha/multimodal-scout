from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, HttpUrl


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
    tags: List[str] # A list of tags for categorization (e.g., 'research', 'industry').
    date: datetime
