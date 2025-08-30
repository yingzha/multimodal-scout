# Frontend Service

Modern Next.js web interface for Multimodal Scout. Provides real-time content discovery and bookmark management.

> For complete setup and usage instructions, see [docs/development.md](../../docs/development.md)  
> For API documentation, see [docs/api.md](../../docs/api.md)  
> For automated pipeline details, see [docs/cron.md](../../docs/cron.md)

## 🚀 Key Features

- 🔐 **User Authentication**: Secure login/registration with session management
- 🎯 **Smart Search**: Topic-based filtering with discovery mode and real-time text search  
- ⚡ **Live Updates**: Server-Sent Events for real-time progress tracking
- 📚 **Bookmark Management**: Private bookmarking with export functionality
- 🌙 **Dark Mode**: System-aware theme with smooth transitions
- 📱 **Responsive UI**: Clean, modern interface optimized for all devices

## 🏗️ Architecture

**Tech Stack:**
- Next.js 14 (App Router) + TypeScript
- CSS Variables for theme-aware styling
- React Context for global state management

**Key Components:**
- `page.tsx` - Main SPA with search and bookmark modes
- `AuthModal.tsx` - Login/registration interface
- `AuthContext.tsx` - User session management  
- `ThemeContext.tsx` - Dark mode state

**Data Flow:**
- REST API calls for standard operations
- Server-Sent Events for real-time progress updates
- Context providers for shared state management
