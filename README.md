# Multimodal Scout

A smart content discovery platform that automatically finds, curates, and helps you bookmark the latest multimodal AI research papers and industry articles. Built with FastAPI, Next.js, PostgreSQL, and powered by Google Gemini AI.

## What It Does

Multimodal Scout scrapes content from Hugging Face trending papers and Hacker News, uses AI to generate intelligent summaries, and provides a clean web interface to:

- 🔍 **Discover** relevant multimodal AI content automatically
- 🧠 **AI-Powered Summaries** for Hacker News articles using Google Gemini
- 🎯 **Smart Balanced Search** with advanced filtering, content balancing, and configurable result limits
- 📚 **Bookmark** articles you want to read later with persistent storage
- ✏️ **Edit Summaries** inline with user-edited indicators and priority in search results
- 📤 **Upload Your Own Links** with automatic content processing, summary generation, and smart categorization
- 📊 **Export Bookmarks** to Excel with title, summary, source URL, and date columns
- ⏰ **Stay updated** with flexible time ranges (any number of days, with quick presets)
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
   - Default topics are locked (🔒) but you can add your own
   - Get real-time feedback when adding keywords (duplicate detection, validation)
2. **Configure search settings**: Customize your content discovery experience
   - **Time range**: Retrieve content from the last N days (any number, with quick presets for 1, 3, or 7 days)
   - **Result count**: Choose 5-50 results (default: 10)
   - **Content balance**: Adjust research/industry ratio from 0-100% (default: 50/50)
   - Smart Balanced Search is always enabled with optimized thresholds
3. **Fetch content**: Click "🔍 Fetch Top Items" to discover relevant articles
   - Watch real-time progress with detailed status updates
   - See AI summary generation and smart filtering progress
   - Progress bar shows completion percentage during processing
4. **Review results**: Browse intelligently filtered and balanced content
   - Results prioritize keyword matches first, then semantic matches by relevance
   - Click article tags to filter by category (Research, Industry, etc.)
   - Expand/collapse summaries with improved "Read more" functionality (only for long text)
   - See filtered result counts and clear filters easily
5. **Bookmark articles**: Click ☆ to save articles for later review
6. **Upload your own content**: In the bookmarks view, use "📤 Upload Your Own Link"
   - Paste any URL to automatically extract title, generate summary, and categorize content
   - AI intelligently tags content as Research, Industry, or General
   - Content is processed and added to your bookmarks instantly
7. **Manage bookmarks**: Use "📚 View My Bookmarks" to see and organize saved articles
   - Tag filtering also works in bookmarks view
   - Remove bookmarks with ★ button (with confirmation)
   - Export all bookmarks to Excel using the 📊 icon
   - Edit bookmark summaries inline

## Key Features

### 🤖 **AI-Powered Content Processing**
- **Intelligent Summaries**: Automatically generates summaries for Hacker News articles using Google Gemini AI with database caching
- **Advanced Semantic Search**: Uses Google Gemini embeddings with separate thresholds for research (0.65) vs industry (0.55) content
- **Smart Balanced Filtering**: New pipeline architecture prioritizes keyword matches, then adds semantic matches by relevance score with configurable research/industry balance
- **User Content Processing**: Upload any URL to automatically extract title, scrape content, generate AI summary, and categorize as Research/Industry/General
- **Smart Content Categorization**: AI analyzes URL patterns and content to intelligently classify uploaded links
- **Comprehensive Caching**: Stores generated summaries and embeddings in PostgreSQL to avoid reprocessing and improve performance

### ⏰ **Automated Content Collection**
- **Scheduled Scraping**: Automatic content collection via Docker cron service with robust environment variable handling
- **Hourly Updates**: Hacker News content fetched every hour to keep information fresh
- **Research Paper Monitoring**: Hugging Face trending papers collected every 6 hours for comprehensive coverage
- **Enhanced Logging**: Detailed cron job monitoring with timestamps, performance metrics, and visual indicators
- **Reliable Execution**: Fixed cron job environment issues with proper database connectivity and dependency management

### 📡 **Real-Time User Experience**
- **Streaming Progress Updates**: Server-Sent Events (SSE) provide live feedback during processing with visual progress bars
- **Enhanced Button States**: Loading animations, color changes, and spinner feedback for better UX
- **Progress Transparency**: Users see exactly what's happening (scraping, generating summaries, filtering)
- **Performance Indicators**: Clear messaging about processing times and expectations

### 🗄️ **Robust Data Management**
- **PostgreSQL Database**: Persistent storage for bookmarks and cached summaries with local time handling
- **Database Migrations**: Alembic-managed schema evolution
- **Batch Operations**: Optimized bulk database operations for improved performance
- **Health Monitoring**: Automatic table creation and database health checks

### 🔧 **Developer-Friendly Architecture**
- **FastAPI Backend**: Modern Python API with automatic documentation
- **Next.js Frontend**: React-based UI with TypeScript support
- **Docker Containerization**: Easy deployment and development setup with hot reload support
- **Microservices**: Separate services for web, API, database, and automated cron jobs
- **Production-Ready Cron Jobs**: Dockerized scheduled tasks with proper environment isolation and comprehensive logging

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
                            ┌─────────────┐      ┌─────────────┐
                            │ PostgreSQL  │      │ Cron Jobs   │
                            │ Database    │      │ (Docker)    │
                            │             │      │             │
                            │ • Bookmarks │      │ • HN Hourly │
                            │ • Summaries │ ←──→ │ • HF 6hr    │
                            │ • Cache     │      │ • Logging   │
                            └─────────────┘      └─────────────┘
```

## Documentation

- 📖 [API Documentation](docs/api.md)
- 🛠 [Development Setup](docs/development.md)
- ⏰ [Cron Jobs & Monitoring](docs/cron-jobs.md)

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
