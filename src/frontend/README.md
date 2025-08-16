# Multimodal Scout Frontend

This is a modern, responsive web interface built with Next.js and TypeScript. It provides an intuitive UI to discover, bookmark, and manage multimodal AI content served by the backend.

## Frontend-Specific Features

- **🎯 Smart Topic Management**: Displays default topics and allows users to add/remove custom keywords.
- **⚡ Real-Time Progress**: Renders live progress updates via SSE during content processing.
- **📊 Advanced Search Settings**: Provides UI controls for time ranges, result counts, and content balance.
- **📚 Bookmark System**: A dedicated UI for viewing, filtering, and managing saved articles.
- **📤 Link Upload**: A form for submitting new URLs, with real-time validation and processing feedback.
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
│   │   └── ThemeToggle.tsx  # Dark mode toggle component
│   ├── context/
│   │   └── ThemeContext.tsx # Manages theme state (dark/light)
│   ├── globals.css          # Global styles and theme-aware CSS variables
│   ├── layout.tsx           # Root layout that includes the ThemeProvider
│   └── page.tsx             # The main single-page application component
├── package.json             # Frontend dependencies and scripts
└── next.config.js           # Next.js configuration
```

### State Management

The application relies on a combination of React's built-in hooks for state management:

- **`useState`**: Manages local component state for UI elements, inputs, and fetched data.
- **`useEffect`**: Handles side effects, such as fetching initial data or interacting with the browser.
- **`useContext`**: Manages the global theme state, allowing any component to access and update the current theme.

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
