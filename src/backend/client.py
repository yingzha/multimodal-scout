#!/usr/bin/env python3
"""
Centralized LLM client for any OpenAI-compatible API (Ollama by default).
"""

import re
from typing import List

import requests

from .config import config
from .logger import logger

_THINK_BLOCK = re.compile(r"<think>.*?</think>", re.DOTALL)


def _headers() -> dict:
    return {"Authorization": f"Bearer {config.llm_api_key}"}


def is_llm_enabled() -> bool:
    """Check if AI features are configured."""
    return bool(config.llm_base_url)


def _post(path: str, payload: dict) -> dict:
    response = requests.post(
        f"{config.llm_base_url}{path}",
        headers=_headers(),
        json=payload,
        timeout=config.llm_timeout_seconds,
    )
    if not response.ok:
        # Keep the server's explanation, e.g. a model that has not been pulled
        raise requests.HTTPError(
            f"{response.status_code} from {path}: {response.text[:200]}",
            response=response,
        )
    return response.json()


def generate_text(prompt: str) -> str:
    """Send a single prompt to the chat model and return its reply."""
    data = _post(
        "/chat/completions",
        {
            "model": config.llm_chat_model,
            "messages": [{"role": "user", "content": prompt}],
        },
    )
    content = data["choices"][0]["message"]["content"] or ""

    # Reasoning models may inline their thinking; keep only the answer
    text = _THINK_BLOCK.sub("", content).strip()
    if not text:
        raise ValueError("LLM returned an empty response")
    return text


def embed_text(text: str) -> List[float]:
    """Get the embedding vector for a text from the embedding model."""
    data = _post("/embeddings", {"model": config.llm_embedding_model, "input": text})
    return data["data"][0]["embedding"]


def is_llm_ready() -> bool:
    """Check that the server answers and that both configured models work."""
    if not is_llm_enabled():
        return False

    try:
        embed_text("ping")
        generate_text("Reply with the single word OK.")
        return True
    except (requests.RequestException, ValueError, KeyError, IndexError) as e:
        logger.warning(f"LLM not ready at {config.llm_base_url}: {e}")
        return False
