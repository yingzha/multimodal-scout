import re
from typing import Optional

from google import genai
import requests
from bs4 import BeautifulSoup
from pydantic import HttpUrl

from .constants import GEMINI_MODEL_NAME, USER_AGENT
from .logger import logger
from .client import genai_client, AI_ENABLED


def _fetch_article_text(link: HttpUrl) -> Optional[str]:
    """Fetches and extracts the main text content from a URL."""
    try:
        response = requests.get(str(link), headers={'User-Agent': USER_AGENT}, timeout=20)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        # Heuristic to find main content: look for <article>, then <body>, and get <p> tags.
        main_content = soup.find('article') or soup.find('body')
        if not main_content:
            return None

        paragraphs = main_content.find_all('p')
        return " ".join([p.get_text() for p in paragraphs])
    except requests.RequestException as e:
        logger.error(f"Error fetching article content from {link}: {e}")
        return None


def _is_non_english_summary(text: str) -> bool:
    """
    Basic heuristic to detect if a summary might not be in English.
    Checks for common non-English patterns and character sets.
    """
    if not text:
        return False
    
    # Check for common non-English character patterns
    # Chinese/Japanese/Korean characters
    if re.search(r'[\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff\uac00-\ud7af]', text):
        return True
    
    # Arabic characters
    if re.search(r'[\u0600-\u06ff]', text):
        return True
    
    # Cyrillic characters
    if re.search(r'[\u0400-\u04ff]', text):
        return True
    
    # Common French words (basic check)
    french_patterns = ['le ', 'la ', 'les ', 'de ', 'du ', 'des ', 'un ', 'une ', 'et ', 'est ', 'dans ', 'sur ', 'avec ', 'pour ', 'par ', 'comme ', 'plus ', 'mais ', 'qui ', 'que ', 'ce ', 'cette ', 'ces ']
    french_count = sum(1 for pattern in french_patterns if pattern in text.lower())
    if french_count > 3:  # If more than 3 French words detected
        return True
    
    # Common German words (basic check)  
    german_patterns = ['der ', 'die ', 'das ', 'den ', 'dem ', 'des ', 'ein ', 'eine ', 'einen ', 'und ', 'ist ', 'in ', 'mit ', 'von ', 'zu ', 'für ', 'auf ', 'als ', 'bei ', 'nach ', 'über ', 'durch ', 'um ']
    german_count = sum(1 for pattern in german_patterns if pattern in text.lower())
    if german_count > 3:  # If more than 3 German words detected
        return True
    
    # Common Spanish words (basic check)
    spanish_patterns = ['el ', 'la ', 'los ', 'las ', 'de ', 'del ', 'un ', 'una ', 'y ', 'es ', 'en ', 'con ', 'por ', 'para ', 'como ', 'más ', 'pero ', 'que ', 'se ', 'su ', 'sus ', 'este ', 'esta ', 'estos ', 'estas ']
    spanish_count = sum(1 for pattern in spanish_patterns if pattern in text.lower())
    if spanish_count > 3:  # If more than 3 Spanish words detected
        return True
    
    return False


def generate_summary_from_link(link: HttpUrl) -> Optional[str]:
    """Generates a summary for a given URL using the Gemini API."""
    if not AI_ENABLED:
        return None

    logger.info(f"Generating summary for: {link}")
    article_text = _fetch_article_text(link)

    if not article_text or len(article_text.strip()) < 100:  # Don't summarize very short texts
        logger.info("Could not extract sufficient text to summarize. Return the original text instead")
        return article_text

    try:
        prompt = f"""Please provide a concise, one-paragraph summary of the following article text in English only. 
        
Regardless of the source language, always respond in English. Focus on the key points and main insights.

Article text:
---
{article_text[:4000]}"""
        
        response = genai_client.models.generate_content(model=GEMINI_MODEL_NAME, contents=[prompt])
        summary = response.text.strip()
        
        # Validate that the summary is in English by checking for common non-English patterns
        if _is_non_english_summary(summary):
            logger.warning(f"Generated summary appears to be non-English, regenerating...")
            # Try again with more explicit English instruction
            english_prompt = f"""IMPORTANT: You must respond in English only. Do not use any other language.

Summarize this article in English, even if the source is in another language:

{article_text[:4000]}

Provide a concise English summary focusing on the main points."""
            
            response = genai_client.models.generate_content(model=GEMINI_MODEL_NAME, contents=[english_prompt])
            summary = response.text.strip()
        
        return summary
    except Exception as e:
        logger.error(f"Error generating summary with Gemini: {e}")
        return None