# Multimodal Scout Frontend

This is a modern, responsive web interface built with Next.js and TypeScript. It provides an intuitive UI to discover, bookmark, and manage multimodal AI content served by the backend.

## Frontend-Specific Features

- **🔐 User Authentication**: Secure login/registration modal for a personalized experience.
- **🎯 Smart Topic Management**: Displays default topics and allows users to add/remove custom keywords.
- **⚡ Real-Time Progress**: Renders live progress updates via SSE during content processing.
- **📊 Advanced Search Settings**: Provides UI controls for time ranges, result counts, and content balance.
- **📚 Contextual UI Modes**: Dynamically transforms between "My Interested Topics" (search mode) and "Bring Your Own URLs" (bookmark mode) for optimal user experience.
- **🔎 Integrated Text Search**: Real-time search functionality for both homepage results and bookmarks with instant filtering by keywords in titles and summaries.
- **🏷️ Multi-Tag Filtering**: Interactive tag-based filtering with clickable keyword tags and combined search capabilities.
- **📤 Multi-URL Processing**: A unified interface for batch URL submission (comma-separated), with smooth progress tracking and contextual feedback.
- **🎲 Discovery Mode**: Toggle between targeted search and serendipitous content discovery with hidden topic controls for clean UX.
- **📋 Personalized Bookmark Management**: Each user gets a private space for bookmarks with date-based filtering, result limits, and search through saved bookmarks with export functionality.
- **🌙 Dark Mode**: System-aware theme toggle with smooth transitions and persistence via localStorage.

## Frontend Architecture

### Technology Stack

- **Framework**: Next.js 14 (App Router)
- **Language**: TypeScript
- **Styling**: Standard CSS with CSS Variables for theme-aware styling.
- **State Management**: React Hooks (`useState`, `useEffect`) and Context API for theme management.

### Component Structure

```
src/frontend/
├── app/
│   ├── components/
│   │   ├── AuthModal.tsx    # Login/registration modal
│   │   └── ThemeToggle.tsx  # Dark mode toggle component
│   ├── contexts/
│   │   ├── AuthContext.tsx    # Manages user authentication state
│   │   └── ThemeContext.tsx # Manages theme state (dark/light)
│   ├── globals.css          # Global styles and theme-aware CSS variables
│   ├── layout.tsx           # Root layout that includes AuthProvider and ThemeProvider
│   └── page.tsx             # Main SPA with contextual UI modes and multi-URL processing
├── package.json             # Frontend dependencies and scripts
└── next.config.js           # Next.js configuration
```

### State Management

The application relies on a combination of React's built-in hooks for state management:

- **`useState`**: Manages local component state for UI elements, inputs, and fetched data.
- **`useEffect`**: Handles side effects, such as fetching initial data or interacting with the browser.
- **`useContext`**: Manages global state for authentication (`AuthContext`) and themes (`ThemeContext`).

Real-time data during content processing is pushed from the server via **Server-Sent Events (SSE)** and updated directly into the component state.

## API Integration

The frontend communicates with the FastAPI backend via two methods:

1.  **REST Endpoints**: Used for standard operations like fetching topics, managing bookmarks, and uploading links.
2.  **Server-Sent Events (SSE)**: A persistent connection to the `/api/fetch-stream` endpoint provides a stream of real-time status updates during content discovery.

## Development Notes

- **Hot Reload**: The Next.js development server, running inside Docker, supports hot reloading. Any changes made to the code are reflected in the browser automatically.
- **Dependencies**: All Node.js dependencies are defined in `package.json` and managed with `npm`. These are installed automatically within the Docker container, so no local `npm install` is needed.

---

**Built with Next.js 14 and TypeScript ✨**
