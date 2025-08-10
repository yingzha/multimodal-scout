# Multimodal Scout Frontend

A modern, responsive web interface built with Next.js 14 and TypeScript that provides an intuitive way to discover, bookmark, and manage multimodal AI content.

## Features

- **🎯 Smart Topic Management**: Default AI topics with ability to add custom keywords
- **⚡ Real-Time Progress**: Streaming updates during content processing with visual feedback
- **📊 Advanced Search Settings**: Configurable time ranges, result counts, and research/industry balance
- **📚 Bookmark System**: Save articles with persistent storage and easy management
- **🔍 Content Filtering**: Filter results by content type (Research, Industry, etc.)
- **📱 Responsive Design**: Works seamlessly on desktop and mobile devices
- **🚀 Optimized UX**: Enhanced button states, loading animations, and smooth interactions

## Technology Stack

- **Framework**: Next.js 14 with App Router
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **Build Tool**: Node.js with npm
- **Containerization**: Docker with multi-stage builds

## Quick Start with Docker

### Prerequisites

- Docker and Docker Compose (frontend is part of the main docker-compose setup)
- No local Node.js installation required!

### Development Setup

```bash
# Start all services from project root
cd multimodal-scout
docker-compose up -d

# Frontend will be available at:
# http://localhost:3000
```

The frontend automatically connects to the backend API and provides a complete user interface.

## Architecture

### Component Structure

```
src/frontend/
├── app/
│   ├── globals.css          # Global styles and Tailwind configuration
│   ├── layout.tsx           # Root layout with metadata and fonts
│   └── page.tsx             # Main application component
├── package.json             # Dependencies and scripts
├── next.config.js           # Next.js configuration
├── tailwind.config.js       # Tailwind CSS configuration
└── tsconfig.json           # TypeScript configuration
```

### Key Components

**Main Application (`page.tsx`)**
- **Topic Management**: Default topics with custom keyword addition
- **Search Settings**: Time range, result count, and content balance controls
- **Real-Time Progress**: SSE-based progress updates with visual feedback
- **Results Display**: Paginated results with filtering and bookmark capabilities
- **Bookmark Management**: Persistent bookmark system with tag filtering

### State Management

The application uses React's built-in state management with hooks:

- `useState`: Component-level state for UI interactions
- `useEffect`: Side effects for data fetching and DOM updates
- Real-time state updates via Server-Sent Events (SSE)

## User Experience Features

### 🎯 **Intelligent Topic Management**
- **Default Topics**: Pre-configured AI topics with lock indicators (🔒)
- **Custom Topics**: Add/remove personal keywords with validation
- **Feedback System**: Real-time messages for duplicate detection and validation

### ⚡ **Enhanced Loading States**
- **Visual Progress**: Animated progress bars and percentage indicators
- **Button Feedback**: Color changes, scaling, and spinner animations
- **Status Messages**: Clear messaging about processing stages

### 📊 **Advanced Controls**
- **Time Range**: Quick selection (1, 3, 7 days) or custom input
- **Result Count**: Slider control (5-50 results)
- **Content Balance**: Research/Industry ratio slider (0-100%)
- **Smart Search**: Always-enabled balanced search with optimized thresholds

### 📚 **Bookmark Experience**
- **One-Click Bookmarking**: Star/unstar articles with visual feedback
- **Bookmark Management**: Dedicated view with filtering and removal
- **Persistence**: Bookmarks saved across sessions
- **Tag Filtering**: Filter by content type in both results and bookmarks

### 🔍 **Content Discovery**
- **Smart Filtering**: Click tags to filter by content type
- **Expandable Summaries**: "Read more" for long summaries with smart detection
- **Pagination**: Smooth navigation through large result sets
- **External Links**: Direct access to original articles

## API Integration

The frontend communicates with the FastAPI backend through:

### RESTful Endpoints
- `GET /api/topics` - Fetch default topics
- `POST /api/fetch` - Standard content fetching
- `POST /api/bookmarks` - Bookmark management
- `DELETE /api/bookmarks` - Remove bookmarks
- `GET /api/bookmarks` - Fetch saved bookmarks

### Real-Time Communication
- `POST /api/fetch-stream` - Server-Sent Events for real-time progress
- Progressive loading with detailed status updates
- Error handling with user-friendly messages

## Development Features

### 🔄 **Hot Reload**
- Automatic reloading during development
- Live updates for code changes
- Preserved state where possible

### 🎨 **Modern Styling**
- **Tailwind CSS**: Utility-first styling approach
- **Responsive Design**: Mobile-first responsive layouts
- **Animations**: Smooth transitions and micro-interactions
- **Accessibility**: Proper focus management and ARIA labels

### 📦 **Optimized Builds**
- **Next.js Optimization**: Automatic code splitting and optimization
- **TypeScript**: Full type safety and developer experience
- **Production Ready**: Minified bundles and optimized assets

## Configuration

### Environment Variables

The frontend uses the following environment variable:

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

This is automatically set in the Docker configuration and points to the backend API.

### Styling Configuration

**Tailwind CSS** (`tailwind.config.js`):
- Custom color schemes
- Typography settings
- Responsive breakpoints
- Component utilities

## Development Workflow

### Making Changes

1. **Component Updates**: Edit `app/page.tsx` for main functionality
2. **Styling Changes**: Modify `app/globals.css` for global styles
3. **Configuration**: Update config files as needed

### Testing Changes

```bash
# View logs
docker-compose logs -f frontend

# Rebuild after major changes
docker-compose build frontend
docker-compose restart frontend
```

### Production Build

```bash
# Build optimized version
docker-compose exec frontend npm run build

# Test production build locally
docker-compose exec frontend npm start
```

## Browser Support

- **Modern Browsers**: Chrome, Firefox, Safari, Edge (latest versions)
- **Mobile Browsers**: iOS Safari, Chrome Mobile, Firefox Mobile
- **Features Used**: ES6+, CSS Grid, Flexbox, WebSocket/SSE

## Performance

- **Initial Load**: ~100KB (optimized bundles)
- **Runtime**: Minimal JavaScript with efficient React patterns
- **Caching**: Next.js automatic caching for static assets
- **Streaming**: Real-time updates without page refreshes

## Deployment

The frontend is containerized and deploys automatically with the main application:

```bash
# Production deployment
docker-compose up -d

# The frontend will be built and served automatically
# Available at http://localhost:3000
```

## No Local Setup Required!

Unlike traditional frontend development, you don't need to:
- Install Node.js or npm locally
- Manage package versions
- Configure build tools
- Set up development servers

Docker handles everything automatically. Just run `docker-compose up` and start developing!

---

**Built with Next.js 14, TypeScript, and Tailwind CSS ✨**