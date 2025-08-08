# Multimodal Scout

A smart content discovery platform that automatically finds, curates, and helps you bookmark the latest multimodal AI research papers and industry articles. Built with FastAPI, Next.js, and PostgreSQL.

## What It Does

Multimodal Scout scrapes content from Hugging Face trending papers and Hacker News, uses AI to generate summaries, and provides a clean web interface to:

- 🔍 **Discover** relevant multimodal AI content automatically
- 📚 **Bookmark** articles you want to read later  
- 🎯 **Filter** content based on your interests and custom keywords
- ⏰ **Stay updated** with configurable time ranges (1-7 days)

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
4. **Bookmark articles**: Click ☆ to save articles for later review
5. **Review bookmarks**: Use "View My Bookmarks" to see saved articles

## Architecture

```
Frontend (Next.js) ←→ Backend (FastAPI) ←→ Database (PostgreSQL)
     ↑                      ↑                      ↑
     └──────────────────────┼──────────────────────┘
                            │
                    Cron Jobs (Auto-scraping)
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

**Built with FastAPI, Next.js, PostgreSQL, and AI ✨**