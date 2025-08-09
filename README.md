# Multimodal Scout

A smart content discovery platform that automatically finds, curates, and helps you bookmark the latest multimodal AI research papers and industry articles. Built with FastAPI, Next.js, PostgreSQL, and powered by Google Gemini AI.

## What It Does

Multimodal Scout scrapes content from Hugging Face trending papers and Hacker News, uses AI to generate intelligent summaries, and provides a clean web interface to:

- 🔍 **Discover** relevant multimodal AI content automatically
- 🧠 **AI-Powered Summaries** for Hacker News articles using Google Gemini
- 🎯 **Smart Balanced Search** with advanced filtering, content balancing, and configurable result limits
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

1. **Configure search settings**: Customize your content discovery experience
   - **Smart Balanced Search**: Toggle advanced filtering with separate thresholds for research vs industry content
   - **Result count**: Choose 5-50 results (default: 10)
   - **Content balance**: Adjust research/industry ratio from 0-100% (default: 50/50)
2. **Set your interests**: Add custom keywords to the default multimodal AI topics
   - Default topics are locked (🔒) but you can add your own
   - Get real-time feedback when adding keywords (duplicate detection, validation)
3. **Choose time range**: Select 1, 3, or 7 days of content
4. **Fetch content**: Click "🔍 Fetch Top Items" to discover relevant articles
   - Watch real-time progress with detailed status updates
   - See AI summary generation and smart filtering progress
   - Progress bar shows completion percentage during processing
5. **Review results**: Browse intelligently filtered and balanced content
   - Results prioritize keyword matches first, then semantic matches by relevance
   - Click article tags to filter by category (Research, Industry, etc.)
   - Expand/collapse summaries with improved "Read more" functionality (only for long text)
   - See filtered result counts and clear filters easily
6. **Bookmark articles**: Click ☆ to save articles for later review
7. **Manage bookmarks**: Use "📚 View My Bookmarks" to see and organize saved articles
   - Tag filtering also works in bookmarks view
   - Remove bookmarks with ★ and × buttons

## Key Features

### 🤖 **AI-Powered Content Processing**
- **Intelligent Summaries**: Automatically generates summaries for Hacker News articles using Google Gemini AI
- **Advanced Semantic Search**: Uses Google Gemini embeddings with separate thresholds for research (0.65) vs industry (0.55) content
- **Smart Balanced Filtering**: Prioritizes keyword matches, then adds semantic matches by relevance score with configurable research/industry balance
- **Comprehensive Caching**: Stores generated summaries and embeddings to avoid reprocessing

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
│ • Topics    │             │   -stream   │                    
└─────────────┘             │ • /bookmarks│              ┌─────────────┐
                            └─────────────┘              │   Content   │
                                   ↓                     │   Sources   │
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

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**Built with FastAPI, Next.js, PostgreSQL, and Google Gemini AI ✨**
