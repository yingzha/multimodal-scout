import re
from typing import List

from .logger import logger
from .schema import SourceSchema

# --- Semantic Search Setup ---
# Load the model once when the module is loaded. This is memory-intensive
# but highly efficient for processing, as it avoids reloading the model.
logger.info("Loading sentence transformer model for semantic search...")
try:
    import sentence_transformers
    from sentence_transformers import SentenceTransformer, util
    SEMANTIC_MODEL = SentenceTransformer('all-MiniLM-L6-v2')
    SEMANTIC_SEARCH_ENABLED = True
    logger.info("Semantic search model loaded successfully")
except Exception as e:
    logger.warning(f"Could not load semantic search model. Semantic search disabled. Error: {e}")
    SEMANTIC_MODEL = None
    SEMANTIC_SEARCH_ENABLED = False


def _normalize_text(text: str) -> str:
    """Converts text to lowercase and removes punctuation for keyword matching."""
    if not text:
        return ""
    # Remove punctuation (anything not a word character or whitespace) and convert to lowercase
    return re.sub(r'[^\w\s]', '', text.lower())


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


def semantic_search(
    sources: List[SourceSchema], keywords: List[str], threshold: float
) -> List[SourceSchema]:
    """
    Performs a semantic search on sources with summaries.

    Args:
        sources: A list of SourceSchema objects to search through.
        keywords: A list of keywords to find semantically similar content for.
        threshold: The minimum similarity score (0.0 to 1.0) to consider a match.

    Returns:
        A list of sources that are semantically similar to the keywords.
    """
    if not SEMANTIC_SEARCH_ENABLED or not sources:
        return []
    
    try:
        from sentence_transformers import util
    except ImportError:
        logger.warning("sentence_transformers not available for semantic search")
        return []

    matches = []
    keyword_embeddings = SEMANTIC_MODEL.encode(keywords, convert_to_tensor=True)
    summaries = [source.summary for source in sources]

    summary_embeddings = SEMANTIC_MODEL.encode(summaries, convert_to_tensor=True)
    cosine_scores = util.cos_sim(summary_embeddings, keyword_embeddings)

    for i, source in enumerate(sources):
        if cosine_scores[i].max() > threshold:
            logger.info(f"Semantic match found for: '{source.title}' (Score: {cosine_scores[i].max():.2f})")
            matches.append(source)

    return matches