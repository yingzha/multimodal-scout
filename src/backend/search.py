import re
import numpy as np
from typing import List

from .logger import logger
from .schema import SourceSchema
from .database import db_manager
from .client import genai_client, AI_ENABLED as SEMANTIC_SEARCH_ENABLED


def _normalize_text(text: str) -> str:
    """Converts text to lowercase and removes punctuation for keyword matching."""
    if not text:
        return ""
    # Remove punctuation (anything not a word character or whitespace) and convert to lowercase
    return re.sub(r'[^\w\s]', '', text.lower())




def _get_embedding(text: str) -> np.ndarray:
    """Get embedding for text using Google Gemini with database caching."""
    if not SEMANTIC_SEARCH_ENABLED or not genai_client:
        return np.array([])

    if not text or text.strip() == "":
        logger.warning("Cannot generate embedding for empty or None text")
        return np.array([])
         
    # Check cache first using the new abstracted method
    try:
        cached_embedding = db_manager.get_embedding_for_text(text)
        if cached_embedding is not None:
            logger.info(f"Using cached embedding for text: {text[:50]}...")
            return np.array(cached_embedding)
    except Exception as e:
        logger.warning(f"Failed to get embedding from cache: {e}")
    
    # Generate new embedding
    try:
        result = genai_client.models.embed_content(
            model="gemini-embedding-001",
            contents=text
        )
        
        if hasattr(result, 'embeddings') and len(result.embeddings) > 0:
            embedding = result.embeddings[0]
            if hasattr(embedding, 'values'):
                embedding_values = list(embedding.values)
                
                # Cache the new embedding using the new abstracted method
                try:
                    db_manager.add_embedding_for_text(text, embedding_values, "gemini-embedding-001")
                    logger.info(f"Generated and cached new embedding for text: {text[:50]}...")
                except Exception as e:
                    logger.warning(f"Failed to cache embedding: {e}")
                
                return np.array(embedding_values)

        logger.error(f"No embeddings found in result: {result}")
        return np.array([])
            
    except Exception as e:
        logger.error(f"Failed to get embedding for text '{text[:50]}...': {e}")
        return np.array([])


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Calculate cosine similarity between two vectors."""
    try:
        if a.size == 0 or b.size == 0:
            return 0.0
        
        # Ensure vectors are 1D
        a = np.atleast_1d(a).flatten()
        b = np.atleast_1d(b).flatten()
        
        if len(a) != len(b):
            logger.warning(f"Vector dimension mismatch: {len(a)} vs {len(b)}")
            return 0.0
            
        # Calculate norms
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
        
        # Normalize vectors and calculate cosine similarity
        a_norm = a / norm_a
        b_norm = b / norm_b
        
        return float(np.dot(a_norm, b_norm))
        
    except Exception as e:
        logger.error(f"Error calculating cosine similarity: {e}")
        return 0.0


def keyword_search(sources: List[SourceSchema], keywords: List[str]) -> List[SourceSchema]:
    """
    Performs a keyword search on a list of sources using normalized text.

    Args:
        sources: A list of SourceSchema objects to search through.
        keywords: A list of keywords to search for.

    Returns:
        A list of sources that match the keywords.
    """
    matches = []
    normalized_keywords = [_normalize_text(k) for k in keywords]

    for source in sources:
        searchable_text = _normalize_text(source.title)
        if source.summary:
            searchable_text += " " + _normalize_text(source.summary)
        if source.keywords:
            searchable_text += " " + " ".join(_normalize_text(k) for k in source.keywords)

        if any(keyword in searchable_text for keyword in normalized_keywords):
            matches.append(source)

    return matches


def semantic_search_with_scores(
    sources: List[SourceSchema], keywords: List[str], threshold: float = None
) -> List[tuple[SourceSchema, float]]:
    """
    Performs a semantic search on sources with summaries using Google Gemini embeddings.
    Returns sources with their similarity scores.

    Args:
        sources: A list of SourceSchema objects to search through.
        keywords: A list of keywords to find semantically similar content for.
        threshold: The minimum similarity score (0.0 to 1.0) to consider a match. If None, returns all with scores.

    Returns:
        A list of tuples (source, similarity_score) sorted by descending similarity.
    """
    if not SEMANTIC_SEARCH_ENABLED or not sources or not genai_client:
        logger.warning("Semantic search is disabled or no sources provided")
        return []

    matches = []
    
    try:
        # Combine keywords into a single query
        query_text = " ".join(keywords)
        query_embedding = _get_embedding(query_text)
        
        if len(query_embedding) == 0:
            logger.warning("Failed to get query embedding, skipping semantic search")
            return []

        logger.info(f"Running Gemini semantic search on {len(sources)} sources with query: '{query_text}'")
        
        for source in sources:
            if not source.summary or source.summary.strip() == "":
                continue
                
            # Get embedding for the source summary
            source_embedding = _get_embedding(source.summary)
            
            if len(source_embedding) == 0:
                continue
                
            # Calculate similarity
            similarity = _cosine_similarity(query_embedding, source_embedding)
            
            # Add to matches if no threshold or meets threshold
            if threshold is None or similarity > threshold:
                matches.append((source, similarity))
                if threshold is not None and similarity > threshold:
                    logger.info(f"Gemini semantic match found for: '{source.title}' (Score: {similarity:.3f})")
                
    except Exception as e:
        logger.error(f"Error in Gemini semantic search: {e}")
        return []

    # Sort by similarity score in descending order
    matches.sort(key=lambda x: x[1], reverse=True)
    
    logger.info(f"Gemini semantic search completed: {len(matches)} matches found")
    return matches


