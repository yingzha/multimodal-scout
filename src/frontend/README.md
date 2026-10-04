# Frontend Service

Modern Next.js web interface for Multimodal Scout. Provides real-time content discovery and bookmark management.

> For complete setup and usage instructions, see [docs/development.md](../../docs/development.md)  
> For API documentation, see [docs/api.md](../../docs/api.md)  
> For automated pipeline details, see [docs/pipeline.md](../../docs/pipeline.md)

## 🚀 Key Features

- 🎯 **Smart Search**: Topic-based filtering with discovery mode and real-time text search  
- ⚡ **Live Updates**: Server-Sent Events for real-time progress tracking
- 📚 **Bookmark Management**: Bookmarking with export functionality
- 🌙 **Dark Mode**: System-aware theme with smooth transitions
- 📱 **Responsive UI**: Clean, modern interface optimized for all devices

## 🏗️ Architecture

**Tech Stack:**
- Next.js 16 (App Router) + TypeScript
- CSS Variables for theme-aware styling
- React Context for global state management

**Key Components:**
- `page.tsx` - Main SPA with search and bookmark modes
- `ThemeContext.tsx` - Dark mode state

**Data Flow:**
- REST API calls for standard operations
- Server-Sent Events for real-time progress updates
- Context providers for shared state management
