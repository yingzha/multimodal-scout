# Multimodal Scout

A smart content discovery platform that automatically finds, curates, and helps you bookmark the latest multimodal AI research papers and industry articles. Built with FastAPI, Next.js, PostgreSQL, and powered by Google Gemini AI.

## What It Does

Multimodal Scout scrapes content from Hugging Face trending papers and Hacker News, uses AI to generate intelligent summaries, and provides a clean web interface to:

- 🔍 **Discover** relevant multimodal AI content automatically
- 🧠 **AI-Powered Summaries** for Hacker News articles using Google Gemini
- 🎯 **Smart Filtering** with both keyword and semantic search capabilities
- 📚 **Bookmark** articles you want to read later with persistent storage
- ⏰ **Stay updated** with configurable time ranges (1-7 days)
- 📊 **Real-time Progress** tracking during content processing

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Google Gemini API key ([Get one here](https://makersuite.google.com/app/apikey))

### Deploy in 3 Steps

1. **Clone and configure:**
   ```bash
   git clone https://github.com/yingzha/multimodal-scout.git
   cd multimodal-scout
   echo "GOOGLE_API_KEY=your_api_key_here" > .env
   ```

2. **Start all services:**
   ```bash
   docker-compose up -d
   ```

3. **Open your browser:**
   - Frontend: http://localhost:3000
   - API docs: http://localhost:8000/docs

That's it! The system will automatically start scraping and processing content.

## How to Use

1. **Set your interests**: Add custom keywords to the default multimodal AI topics
2. **Choose time range**: Select 1, 3, or 7 days of content
3. **Fetch content**: Click "Fetch Top Items" to discover relevant articles
   - Watch real-time progress as the system scrapes sources
   - See AI summary generation progress for Hacker News articles
   - Get notified when processing is complete
4. **Review results**: Browse AI-filtered content with intelligent summaries
5. **Bookmark articles**: Click ☆ to save articles for later review
6. **Manage bookmarks**: Use "View My Bookmarks" to see and organize saved articles

## Key Features

### 🤖 **AI-Powered Content Processing**
- **Intelligent Summaries**: Automatically generates summaries for Hacker News articles using Google Gemini AI
- **Semantic Search**: Uses sentence-transformers for finding semantically similar content
- **Smart Caching**: Stores generated summaries to avoid reprocessing

### 📡 **Real-Time User Experience**
- **Streaming Progress Updates**: Server-Sent Events (SSE) provide live feedback during processing
- **Progress Transparency**: Users see exactly what's happening (scraping, generating summaries, filtering)
- **Performance Indicators**: Clear messaging about processing times and expectations

### 🗄️ **Robust Data Management**
- **PostgreSQL Database**: Persistent storage for bookmarks and cached summaries
- **Database Migrations**: Alembic-managed schema evolution
- **Health Monitoring**: Automatic table creation and database health checks

### 🔧 **Developer-Friendly Architecture**
- **FastAPI Backend**: Modern Python API with automatic documentation
- **Next.js Frontend**: React-based UI with TypeScript support
- **Docker Containerization**: Easy deployment and development setup
- **Microservices**: Separate services for web, API, database, and cron jobs

## Architecture

```
Frontend (Next.js)          Backend (FastAPI)           External Services
      ↓                           ↓                           ↓
┌─────────────┐             ┌─────────────┐              ┌─────────────┐
│   Web UI    │    SSE      │   API       │              │ Google      │
│  (React)    │ ←────────→  │  Endpoints  │ ←──────────→ │ Gemini AI   │
│             │             │             │              │             │
│ • Progress  │             │ • /api/fetch│              └─────────────┘
│ • Bookmarks │             │ • /api/fetch│                     ↑
│ • Topics    │             │   -stream   │                     │
└─────────────┘             │ • /bookmarks│              ┌─────────────┐
                            └─────────────┘              │   Content   │
                                   ↓                      │   Sources   │
                            ┌─────────────┐              │             │
                            │  AI Engine  │              │ • Hugging   │
                            │             │ ←──────────→ │   Face      │
                            │ • Summary   │              │ • Hacker    │
                            │   Generation│              │   News      │
                            │ • Semantic  │              └─────────────┘
                            │   Search    │                     
                            │ • Caching   │                     
                            └─────────────┘                     
                                   ↓                            
                            ┌─────────────┐                     
                            │ PostgreSQL  │                     
                            │ Database    │                     
                            │             │                     
                            │ • Bookmarks │                     
                            │ • Summaries │                     
                            │ • Cache     │                     
                            └─────────────┘                     
```

## Documentation

- 📖 [API Documentation](docs/api.md)
- 🛠 [Development Setup](docs/development.md)
- 🚀 [Deployment Guide](docs/deployment.md)
- 🎨 [Frontend Architecture](docs/frontend.md)

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**Built with FastAPI, Next.js, PostgreSQL, Google Gemini AI, and sentence-transformers ✨**