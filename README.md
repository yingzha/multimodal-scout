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

### **Modern, Minimalist Interface**
The app features a clean, rounded design with intuitive navigation:

1. **Add interests**: Use the rounded search bar to add custom keywords
   - Type keywords and click the **+** icon or press Enter
   - Default topics are shown with lock icons (🔒)
   - Custom topics appear as blue pills with **×** to remove

2. **Quick actions**: Access key features from the search bar icons
   - **+ icon**: Add keywords instantly  
   - **⚙️ icon**: Open advanced search settings
   - **📖 icon**: View your bookmarks
   - **🌙 icon**: Toggle dark/light mode

3. **Discover content**: Click the central "🔍 Discover Content" button
   - Watch real-time progress with animated loading states
   - Progress bar and spinner show processing status
   - See AI summary generation and smart filtering progress

4. **Manage bookmarks**: Click any bookmark icon for a focused bookmark view
   - **Bookmark-focused interface**: Hides search elements, shows only bookmark-relevant features
   - **Multiple access points**: Bookmark icon in search bar or topics section
   - **Upload links**: Add your own URLs with automatic processing
   - **Edit summaries**: Click the edit icon (✏️) to modify summaries inline
   - **Export to Excel**: Use the 📊 icon to download all bookmarks

5. **Advanced settings**: Configure your search experience
   - **Time range**: Content from last N days (quick presets: 1, 3, 7 days)
   - **Result count**: 5-50 results (default: 10)  
   - **Content balance**: Research vs industry ratio (default: 50/50)
   - **Smart filtering**: Keyword priority + semantic search with optimized thresholds

6. **Browse results**: Intelligently filtered and categorized content
   - Click article tags to filter by category (Research, Industry, etc.)
   - Expand/collapse long summaries with "Read more" functionality
   - Bookmark articles with ☆ icon for later review

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

### 📡 **Modern User Experience**
- **Minimalist Design**: Clean, rounded interface inspired by modern search platforms with intuitive navigation
- **Dark Mode Support**: System-aware dark/light theme toggle with localStorage persistence
- **Smart Interface Modes**: Focused bookmark view hides irrelevant content discovery elements for better UX
- **Contextual Icons**: Multiple access points for bookmarks, settings, and theme toggle integrated seamlessly into the interface
- **Streaming Progress Updates**: Server-Sent Events (SSE) provide live feedback during processing with visual progress bars
- **Enhanced Loading States**: Animated progress bars, spinners, and button state changes for clear user feedback
- **Progress Transparency**: Users see exactly what's happening (scraping, generating summaries, filtering)
- **Responsive Pill Design**: Topic tags and UI elements use modern rounded pill styling for better visual hierarchy

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
