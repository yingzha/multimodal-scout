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
- [Google Gemini API key](https://aistudio.google.com/app/apikey)

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

4. **Monitor & Control:**
   ```bash
   # Watch pipeline automation
   docker-compose logs -f cron
   
   # Manual pipeline trigger
   curl -X POST "http://localhost:8000/pipeline" \
     -H "Authorization: Bearer test-token"
   
   # View all services
   docker-compose ps
   ```

🎉 **Ready!** The system auto-discovers and processes content every 30 minutes.

## ☁️ Cloud Deployment

Deploy to Google Cloud Platform with auto-scaling and cost optimization:

### Prerequisites
- [Google Cloud CLI](https://cloud.google.com/sdk/docs/install) installed and authenticated
- Google Cloud project with billing enabled
- [Required APIs enabled](./GOOGLE_CLOUD_SETUP.md)

### Deploy to Production

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

3. **Access Your App:**
   - Frontend URL will be displayed after deployment
   - Automatic HTTPS with custom domain support
   - Built-in monitoring and logging

### Cloud Features
- ⚡ **Auto-scaling**: 0 to 10+ instances based on traffic
- 💰 **Cost-optimized**: ~$5-8/month for <10 DAU
- 🔒 **Secure**: IAM, Cloud SQL, and encrypted connections
- 📊 **Monitored**: Cloud Scheduler + Logging + Metrics
- 🚀 **Fast**: Global CDN and optimized builds

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
