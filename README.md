# Multimodal Scout

A smart content discovery platform that automatically finds, curates, and helps you bookmark the latest multimodal AI research papers and industry articles. Built with FastAPI, Next.js, and PostgreSQL, powered by Google Gemini AI.

![Multimodal Scout Interface](./assets/homepage.png)

## ✨ Features

- 🤖 **AI-Powered Curation**: Auto-discovers and summarizes multimodal AI research and industry content
- 🔍 **Smart Search**: Advanced filtering, real-time search, and "Discovery Mode" for exploration  
- 📚 **Personal Library**: Secure bookmarking with editing, export, and management
- 🌙 **Modern UI**: Clean, responsive interface with dark mode support
- ⚡ **Real-time Updates**: Live content processing with progress tracking

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose
- Google Gemini API key
- Google Cloud CLI (optional)

### Local Development

1. **Clone & Setup:**
   ```bash
   git clone https://github.com/yingzha/multimodal-scout.git
   cd multimodal-scout
   
   # Configure environment
   ./scripts/configure-env.sh local
   
   # Add your API key
   echo "GOOGLE_API_KEY=your_actual_api_key" >> .env
   ```

2. **Start All Services:**
   ```bash
   docker-compose up -d
   ```
   
   This launches:
   - 🗄️ **PostgreSQL** (port 5432)
   - 🖥️ **Backend API** (port 8000) 
   - 🌐 **Frontend** (port 3000)
   - ⏰ **Cron Pipeline** (every 30 min)

3. **Access Applications:**
   - **Main App**: http://localhost:3000
   - **API Docs**: http://localhost:8000/docs

### Production Deployment

1. **Prepare Environment:**
   ```bash
   # Configure for cloud deployment
   ./scripts/configure-env.sh cloud
   
   # Set up infrastructure (run once)
   ./setup-infrastructure.sh YOUR_PROJECT_ID us-central1
   ```

2. **Deploy Services:**
   ```bash
   # Build and deploy all services
   ./deploy-services.sh YOUR_PROJECT_ID us-central1
   ```

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                            Frontend (Next.js)                           │ 
│                     Real-time UI + Authentication                       │
└─────────────────────────┬───────────────────────────────────────────────┘
                          │ REST API + SSE
┌─────────────────────────▼───────────────────────────────────────────────┐
│                            Backend (FastAPI)                            │
│                    API Endpoints + Pipeline Logic                       │
└─────┬─────────────────────────────┬─────────────────────────────────────┘
      │                             │
      ▼                             ▼
┌──────────────┐            ┌──────────────────┐
│  PostgreSQL  |            |    Google Gemini │
│   Database   │            │      AI API      │
│              │            │                  │
│ • Bookmarks  │            │ • Summarization  │
│ • Content    │            │ • Categorization │
│ • Users      │            │ • Smart Filters  │
│ • Cache      │            └──────────────────┘
└──────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                         Automated Pipeline                              │
│                        (Every 30 minutes)                               │
│                                                                         │
│ Content Discovery  →  AI Processing  →  Storage & Indexing              │
│                                                                         │
│ • Hacker News         →  • Summarization   →  • PostgreSQL              │
│ • Substack Feeds      →  • Categorization  →  • Search Embeddings       │
│ • Hugging Face        →  • Quality Filter  →  • Cache Management        │
└─────────────────────────────────────────────────────────────────────────┘
```

**Local Development:**
- 4 Docker services: Frontend, Backend, PostgreSQL, Cron
- Automated content processing every 30 minutes
- Real-time monitoring and manual triggers

**Cloud Production:**
- Google Cloud Run (auto-scaling)
- Google Cloud SQL (managed PostgreSQL)
- Google Cloud Scheduler (automated pipeline)
- Cost-optimized: ~$5-8/month for <10 DAU

## 🔧 Configuration

Switch between environments easily:

```bash
# Local development
./scripts/configure-env.sh local

# Cloud deployment  
./scripts/configure-env.sh cloud
```

## 📚 Documentation

- 🛠️ **[Development Guide](docs/development.md)** - Local setup, testing, and workflows
- 🔗 **[API Reference](docs/api.md)** - Complete REST API documentation
- ⏰ **[Automation Guide](docs/cron-jobs.md)** - Pipeline and content processing
- ☁️ **[Cloud Setup](GOOGLE_CLOUD_SETUP.md)** - Google Cloud deployment guide

## 🤝 Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

See the [Development Guide](docs/development.md) for detailed setup and workflow instructions.

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.
