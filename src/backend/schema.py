from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, HttpUrl


class SourceSchema(BaseModel):
    """
    Represents the data schema for a source, providing validation and type hints.
    """

    title: str
    """The title of the source."""

    authors: List[str]
    """A list of authors for the source."""

    link: HttpUrl
    """A valid URL linking to the source."""

    summary: Optional[str] = None
    """An optional summary of the source content."""

    keywords: Optional[List[str]] = None
    """An optional list of keywords related to the source."""

    tags: List[str]
    """A list of tags for categorization (e.g., 'research', 'industry')."""

    date: datetime
    """The publication date of the source."""