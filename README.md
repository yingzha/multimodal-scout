# Multimodal Scout

A smart content discovery platform that automatically finds, curates, and helps you bookmark the latest multimodal AI research papers and industry articles. Built with FastAPI, Next.js, and PostgreSQL, and powered by Google Gemini AI.

![Multimodal Scout Interface](./assets/screenshot.png)

## Key Features

- 🔍 **Automated Content Discovery**: Scrapes and processes content from Hacker News and Hugging Face.
- 🧠 **AI-Powered Summaries**: Generates intelligent summaries for articles using Google Gemini.
- 🎯 **Smart Filtering**: Balances content between research and industry, with configurable result limits.
- 📚 **Persistent Bookmarks**: Save articles, edit summaries, and export your collection to Excel.
- 📤 **Upload & Process Links**: Add your own URLs for automatic scraping, summarization, and categorization.
- ⏰ **Real-time Progress**: Live progress updates during content fetching and processing via SSE.
- 🌙 **Modern UI**: A clean, responsive interface with dark mode support.

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Google Gemini API key

### Installation

1.  **Clone and Configure:**
    ```bash
    git clone https://github.com/yingzha/multimodal-scout.git
    cd multimodal-scout
    echo "GOOGLE_API_KEY=your_api_key_here" > .env
    ```

2.  **Start Services:**
    ```bash
    docker-compose up -d
    ```

3.  **Open Your Browser:**
    - **Frontend:** http://localhost:3000
    - **API Docs:** http://localhost:8000/docs

The system will automatically start scraping and processing content in the background.

## Architecture Overview

The application runs in separate, containerized services:

- **Frontend:** A **Next.js** application providing the user interface.
- **Backend:** A **FastAPI** server that handles API requests, content processing, and AI integration.
- **Database:** A **PostgreSQL** instance for persistent storage of bookmarks and cached data.
- **Cron:** A scheduled service for automated, periodic content scraping.

```
Frontend (Next.js)          Backend (FastAPI)           External Services
       ↓                           ↓                            ↓
┌─────────────┐             ┌─────────────┐              ┌─────────────┐
│   Web UI    │    SSE      │   API       │              │ Google      │
│  (React)    │ ←────────→  │  Endpoints  │ ←──────────→ │ Gemini AI   │
└─────────────┘             └─────────────┘              └─────────────┘
                                   ↓                            ↑
                            ┌─────────────┐              ┌─────────────┐
                            │  AI Engine  │              │   Content   │
                            │             │ ←──────────→ │   Sources   │
                            └─────────────┘              └─────────────┘
                                   ↓
                            ┌─────────────┐      ┌─────────────┐
                            │ PostgreSQL  │      │ Cron Jobs   │
                            │ Database    │ ←──→ │ (Docker)    │
                            └─────────────┘      └─────────────┘
```

## Developer Documentation

For more detailed information on development, deployment, and specific service architecture, please see the READMEs in the service directories:

- **📖 [Backend README](src/backend/README.md)**
- **🛠 [Frontend README](src/frontend/README.md)**
- **⏰ [Cron Job Docs](docs/cron-jobs.md)**

## Contributing

1.  Fork the repository.
2.  Create your feature branch (`git checkout -b feature/amazing-feature`).
3.  Commit your changes (`git commit -m 'Add some amazing feature'`).
4.  Push to the branch (`git push origin feature/amazing-feature`).
5.  Open a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.