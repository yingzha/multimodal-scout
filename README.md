# Multimodal Scout

Multimodal Scout is a Python-based data pipeline designed to scrape, enrich, and filter content from various online sources. It leverages AI to generate summaries, uses hybrid search (keyword + semantic) to find relevant articles, and provides a structured, validated output.

## Features

- **Multi-Source Scraping**: Gathers data from Hugging Face Trending Papers and the Hacker News RSS feed.
- **AI-Powered Enrichment**: Uses the Google Gemini API to automatically generate summaries for sources that are missing them.
- **Data Tagging**: Automatically categorizes sources as `research` or `industry` based on heuristics.
- **Efficient Caching**: Caches generated summaries in a local `summary_cache.json` file to reduce redundant API calls and save costs.
- **Hybrid Search**: Filters content using a two-pass system:
  1.  A fast, normalized keyword search.
  2.  A sophisticated semantic search for conceptually related content.
- **Data Validation**: Employs Pydantic to ensure all collected data conforms to a strict, well-defined schema.
- **Structured Logging**: Provides clear, leveled logging for monitoring and debugging the pipeline's execution.

## Project Structure

The core logic resides in the `src/backend/` directory:

```
src/backend/
├── scraper.py       # Functions for scraping data from sources.
├── search.py        # Keyword and semantic search implementations.
├── utils.py         # Utilities for AI summary generation.
├── merger.py        # Main orchestrator for the data pipeline.
├── schema.py        # Pydantic data schema for sources.
├── cache.py         # Logic for reading/writing to the summary cache.
├── constants.py     # Centralized configuration and keywords.
└── logger.py        # Application-wide logger configuration.
```

## Setup and Installation

### Prerequisites
- Python 3.8+
- Git

### 1. Clone the Repository

```bash
git clone <your-repository-url>
cd multimodal-scout
```

### 2. Create and Activate a Virtual Environment

It's highly recommended to use a virtual environment to manage dependencies.

```bash
# For macOS/Linux
python3 -m venv venv
source venv/bin/activate

# For Windows
python -m venv venv
.\venv\Scripts\activate
```

### 3. Install Dependencies

Install all required packages from the `requirements.txt` file.

```bash
pip install -r requirements.txt
```

### 4. Set Up Google API Key

This project uses the Google Gemini API for summary generation. You need to set your API key as an environment variable.

```bash
# For macOS/Linux
export GOOGLE_API_KEY="your_api_key_here"

# For Windows (in Command Prompt)
set GOOGLE_API_KEY="your_api_key_here"
```

## How to Run

Execute the main merger script from the project's root directory. The script will run all scrapers, enrich the data, filter it, and print the final sorted list to the console.

```bash
python -m src.backend.merger
```

## How to Run Tests

The project includes unit tests to validate the scrapers. To run them, use `pytest`:

```bash
pytest
```