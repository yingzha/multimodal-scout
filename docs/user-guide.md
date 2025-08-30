# User Guide

A comprehensive guide to using Multimodal Scout effectively.

**🌐 Live Demo**: [https://multimodal-scout.app/](https://multimodal-scout.app/)

## Getting Started

Visit [https://multimodal-scout.app/](https://multimodal-scout.app/) to start exploring! The platform works in two modes:
- **Guest Mode**: Browse and search content (5 searches/day limit)
- **Registered User**: Unlimited searches + bookmark management

## Main Interface Overview

### 🏠 Homepage Controls
- **🏠 Home Button**: Return to main search interface
- **📚 Bookmarks Button**: View your saved bookmarks (*login required*)
- **⚙️ Settings Button**: Access advanced search options (time range, content balance, result count)
- **🌙 Theme Toggle**: Switch between light and dark modes
- **👤 User Button**: Login/register or access user menu when logged in

### 🔍 Search & Discovery
1. **Topic Keywords**: 
   - Default topics are provided (multimodal, image understanding, etc.)
   - Add custom keywords using the "+" button
   - Remove custom keywords with the "×" button
   - 🔒 locked topics are system defaults (cannot be removed)

2. **Discovery Mode Toggle**: 
   - Enable for serendipitous content discovery without specific topics
   - Randomly samples from all available content sources

3. **Search Button**: Start content discovery with your selected parameters

### 📋 Search Results
Each result card shows:
- **Source Tags**: Click to filter results by source type
- **Matched Keywords**: See which keywords triggered this result
- **"New!" Badge**: Indicates recently discovered content
- **⭐ Bookmark Button**: Save to your personal library (*login required*)
- **Title & Summary**: AI-generated content overview with "Read more/less" expansion
- **"Read the original post →"**: Visit the source article

### 🔍 Filtering & Search
- **Keyword Filter**: Search within results by title/summary
- **Tag Filters**: Click source tags or keywords to filter results
- **Active Filters**: View and remove applied filters with "×" button
- **Pagination**: Navigate through large result sets

## 📚 Bookmark Management (*Login Required*)

### Accessing Bookmarks
- Click the **Bookmarks** button in the top navigation
- Requires user registration/login for privacy and data persistence

### Bookmark Features
- **Time Filters**: View bookmarks from last 1, 3, 7, or 30 days, or all time
- **Result Limits**: Show 10, 25, 50, or 100 bookmarks per page
- **Search**: Filter bookmarks by keyword in title or summary
- **Tag Filtering**: Filter by source type or matched keywords

### Individual Bookmark Actions
- **⭐ Remove**: Delete bookmark from your collection  
- **✏️ Edit Summary**: Click the edit icon to customize the AI-generated summary
- **Expand/Collapse**: Read full summaries with "Read more/less"
- **Visit Source**: Click "Read the original post →" to visit the original article

### Export Bookmarks
- **Export Button**: Download your bookmarks as HTML file
- **Chrome Compatible**: Import directly into Chrome browser bookmarks
- **Organized Structure**: Automatically sorted into Research/Industry folders
- **Filtered Export**: Exports respect current search and tag filters

## 🔗 Add Your Own Content

### URL Upload (in Bookmark Mode)
- Switch to bookmark view, then use the URL input field
- **Multiple URLs**: Separate multiple URLs with commas
- **Automatic Processing**: 
  - Extracts article title and content
  - Generates AI summary using Google Gemini
  - Categorizes as Research/Industry/General
  - Adds to your bookmark collection
- **Progress Tracking**: Real-time progress bar for multiple URL processing

## 👤 User Account Management

### Registration/Login
- **Guest Users**: 5 searches per day, no bookmarking
- **Registered Users**: Unlimited searches, full bookmark management
- **User Menu**: Access account info and logout when logged in
- **Session Management**: Secure token-based authentication

### Account Features
- **Email & Username**: Personal account identification
- **Session Persistence**: Stay logged in across browser sessions
- **Secure Logout**: Invalidate session tokens for security

## 💡 Pro Tips

- **Bookmark Before Reading**: Save interesting articles first, read later
- **Use Discovery Mode**: Find unexpected relevant content outside your normal topics  
- **Custom Keywords**: Add specific research areas or companies you follow
- **Export Regularly**: Back up your bookmarks to local files
- **Filter Combinations**: Combine text search with tag filters for precise results
- **Time Range Optimization**: Use shorter ranges (1-3 days) for latest content, longer for comprehensive searches

## 🔄 Content Sources

Multimodal Scout automatically discovers content from:
- **Hacker News**: Latest tech discussions and papers
- **Substack Feeds**: AI/ML newsletters and blogs  
- **Hugging Face**: Research papers and model releases
- **User Submissions**: Your own URLs via the upload feature

## 🤖 AI Features

- **Smart Summarization**: Google Gemini generates concise summaries
- **Auto-Categorization**: Content automatically tagged as Research/Industry/General
- **Semantic Search**: Find content similar to your interests
- **Quality Filtering**: AI filters low-quality or irrelevant content

## 🛟 Troubleshooting

### Common Issues
- **"Login required" messages**: Register for unlimited access and bookmarking
- **Search limit reached**: Guest users have 5 searches/day - register for unlimited access
- **Slow loading**: First-time visits may take a few seconds due to server startup
- **Export not working**: Ensure you're logged in and have bookmarks to export

### Getting Help
- Check the [Development Guide](development.md) for technical details
- Review the [API Documentation](api.md) for integration information
- File issues on the project GitHub repository