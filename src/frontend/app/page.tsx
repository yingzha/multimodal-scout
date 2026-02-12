'use client'

import { useState, useEffect, useRef } from 'react'
import ThemeToggle from './components/ThemeToggle'
import AuthModal from './components/AuthModal'
import { useAuth } from './contexts/AuthContext'

export default function Home() {
  const { user, sessionToken, isAuthenticated, isLoading: authLoading, login, logout } = useAuth()

  // API configuration
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

  // UI State
  const [showAuthModal, setShowAuthModal] = useState(false)
  const [showResults, setShowResults] = useState(false)
  const [showBookmarks, setShowBookmarks] = useState(false)
  const [showAdvancedSettings, setShowAdvancedSettings] = useState(false)
  const [showUserMenu, setShowUserMenu] = useState(false)

  // Content and Data State
  const [fetchedItems, setFetchedItems] = useState<any[]>([])
  const [bookmarkedCards, setBookmarkedCards] = useState<any[]>([])
  const [bookmarkedItems, setBookmarkedItems] = useState<Set<string>>(new Set())
  const [expandedSummaries, setExpandedSummaries] = useState<Set<string>>(new Set())
  const [showReadMore, setShowReadMore] = useState<Set<string>>(new Set())

  // Topics and Keywords
  const [defaultTopics, setDefaultTopics] = useState<string[]>([])
  const [customTopics, setCustomTopics] = useState<string[]>([])
  const [newKeyword, setNewKeyword] = useState('')
  const [selectedTags, setSelectedTags] = useState<Set<string>>(new Set())
  const [isLoadingTopics, setIsLoadingTopics] = useState(true)

  // Search and Filtering
  const [homepageSearchQuery, setHomepageSearchQuery] = useState('')
  const [bookmarkSearchQuery, setBookmarkSearchQuery] = useState('')
  const [bookmarkSearchDays, setBookmarkSearchDays] = useState<number | null>(null)
  const [bookmarkSearchLimit, setBookmarkSearchLimit] = useState(50)

  // Settings and Configuration
  const [selectedDays, setSelectedDays] = useState(1)
  const [maxResults, setMaxResults] = useState(10)
  const [researchRatio, setResearchRatio] = useState(0.5)
  const [discoveryMode, setDiscoveryMode] = useState(false)
  const [appConfig, setAppConfig] = useState({ max_urls_per_request: 5 })

  // Loading and Progress State
  const [isLoading, setIsLoading] = useState(false)
  const [progressMessage, setProgressMessage] = useState('')
  const [keywordMessage, setKeywordMessage] = useState('')

  // Upload State
  const [uploadUrl, setUploadUrl] = useState('')
  const [isUploading, setIsUploading] = useState(false)
  const [uploadMessage, setUploadMessage] = useState('')
  const [uploadProgress, setUploadProgress] = useState(0)
  const [uploadProgressMessage, setUploadProgressMessage] = useState('')

  // Edit and Delete State
  const [editingSummary, setEditingSummary] = useState<string | null>(null)
  const [editedSummaryText, setEditedSummaryText] = useState('')
  const [isUpdatingSummary, setIsUpdatingSummary] = useState(false)
  const [deleteConfirmItem, setDeleteConfirmItem] = useState<any>(null)
  const [deleteConfirmPosition, setDeleteConfirmPosition] = useState<{top: number, left: number} | null>(null)

  // Navigation and Session State
  const [previousViewState, setPreviousViewState] = useState<{showResults: boolean, showBookmarks: boolean} | null>(null)
  const [sessionId] = useState(() => {
    // Try to get existing session ID from localStorage first
    if (typeof window !== 'undefined') {
      const existingSessionId = localStorage.getItem('multimodal-scout-session-id')
      if (existingSessionId) {
        return existingSessionId
      }
    }

    // Generate new session ID and store it
    const newSessionId = 'session_' + Math.random().toString(36).substring(2, 11) + '_' + Date.now()
    if (typeof window !== 'undefined') {
      localStorage.setItem('multimodal-scout-session-id', newSessionId)
    }
    return newSessionId
  })

  // Utility function to show temporary messages
  const showTemporaryMessage = (message: string, duration: number = 3000) => {
    setKeywordMessage(message)
    setTimeout(() => setKeywordMessage(''), duration)
  }

  // Reset to fresh homepage view
  const resetToHomepage = () => {
    setShowResults(false)
    setShowBookmarks(false)
    setShowAdvancedSettings(false)
    setShowAuthModal(false)
    setShowUserMenu(false)
    setKeywordMessage('')
    setFetchedItems([])
    setBookmarkedCards([])
    setPaginatedItems([])
    setPaginatedBookmarks([])
    setCurrentPage(1)
    setBookmarksPage(1)
    setExpandedSummaries(new Set())
    setShowReadMore(new Set())
    setBookmarkSearchQuery('')
    setHomepageSearchQuery('')
    setSelectedTags(new Set())
  }

  // Pagination State
  const [currentPage, setCurrentPage] = useState(1)
  const [bookmarksPage, setBookmarksPage] = useState(1)
  const [paginatedItems, setPaginatedItems] = useState<any[]>([])
  const [paginatedBookmarks, setPaginatedBookmarks] = useState<any[]>([])
  const itemsPerPage = 5

  // Refs
  const clickTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const userMenuRef = useRef<HTMLDivElement>(null)

  // Debounced search values to reduce API calls
  const [debouncedHomepageSearch, setDebouncedHomepageSearch] = useState(homepageSearchQuery)
  const [debouncedBookmarkSearch, setDebouncedBookmarkSearch] = useState(bookmarkSearchQuery)
  const homepageSearchTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const bookmarkSearchTimeoutRef = useRef<NodeJS.Timeout | null>(null)

  // ==============================
  // EFFECTS AND EVENT HANDLERS
  // ==============================

  // Debounce homepage search
  useEffect(() => {
    if (homepageSearchTimeoutRef.current) {
      clearTimeout(homepageSearchTimeoutRef.current)
    }
    homepageSearchTimeoutRef.current = setTimeout(() => {
      setDebouncedHomepageSearch(homepageSearchQuery)
    }, 300)

    return () => {
      if (homepageSearchTimeoutRef.current) {
        clearTimeout(homepageSearchTimeoutRef.current)
      }
    }
  }, [homepageSearchQuery])

  // Debounce bookmark search
  useEffect(() => {
    if (bookmarkSearchTimeoutRef.current) {
      clearTimeout(bookmarkSearchTimeoutRef.current)
    }
    bookmarkSearchTimeoutRef.current = setTimeout(() => {
      setDebouncedBookmarkSearch(bookmarkSearchQuery)
    }, 300)

    return () => {
      if (bookmarkSearchTimeoutRef.current) {
        clearTimeout(bookmarkSearchTimeoutRef.current)
      }
    }
  }, [bookmarkSearchQuery])

  // Handle clicking outside user menu to close it
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (userMenuRef.current && !userMenuRef.current.contains(event.target as Node)) {
        setShowUserMenu(false)
      }
    }

    if (showUserMenu) {
      document.addEventListener('mousedown', handleClickOutside)
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [showUserMenu])


  // Handle gear button clicks (single and double click)
  const handleGearClick = () => {
    if (clickTimeoutRef.current) {
      // This is a double click - clear the timeout and hide settings
      clearTimeout(clickTimeoutRef.current)
      clickTimeoutRef.current = null
      setShowAdvancedSettings(false)
    } else {
      // This is a single click - set a timeout to toggle settings
      clickTimeoutRef.current = setTimeout(() => {
        setShowAdvancedSettings(!showAdvancedSettings)
        clickTimeoutRef.current = null
      }, 200) // 200ms delay to detect double click
    }
  }

  // ==============================
  // API FUNCTIONS
  // ==============================

  // Fetch default topics from backend
  const fetchDefaultTopics = async () => {
    try {
      setIsLoadingTopics(true)
      const response = await fetch(`${apiUrl}/api/topics`)

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data = await response.json()
      setDefaultTopics(data.topics)
    } catch (error) {
      console.error('Failed to fetch default topics:', error)
      // Fallback to empty array if API fails - let backend be the source of truth
      setDefaultTopics([])
    } finally {
      setIsLoadingTopics(false)
    }
  }

  const fetchConfig = async () => {
    try {
      const response = await fetch(`${apiUrl}/api/config`, {
        cache: 'no-cache',
        headers: {
          'Cache-Control': 'no-cache'
        }
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data = await response.json()
      setAppConfig(data)
    } catch (error) {
      console.error('Failed to fetch app config:', error)
      // Keep default fallback values if API fails
    }
  }

  const fetchUserPreferences = async () => {
    if (!isAuthenticated || !sessionToken) return
    
    try {
      const response = await fetch(`${apiUrl}/api/user/preferences`, {
        headers: {
          'Authorization': `Bearer ${sessionToken}`,
          'Cache-Control': 'no-cache'
        }
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data = await response.json()
      setCustomTopics(data.custom_topics || [])
    } catch (error) {
      console.error('Failed to fetch user preferences:', error)
      // Keep empty array if API fails
    }
  }

  const saveUserPreferences = async (topics: string[]) => {
    if (!isAuthenticated || !sessionToken) return
    
    try {
      const response = await fetch(`${apiUrl}/api/user/preferences`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${sessionToken}`
        },
        body: JSON.stringify({
          custom_topics: topics
        })
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
    } catch (error) {
      console.error('Failed to save user preferences:', error)
    }
  }

  useEffect(() => {
    fetchDefaultTopics()
    fetchConfig()
  }, [])

  useEffect(() => {
    if (isAuthenticated && !authLoading) {
      loadBookmarkStatus()
      fetchUserPreferences()
    } else if (!authLoading) {
      // Clear custom topics for guest users
      setCustomTopics([])
    }
  }, [isAuthenticated, authLoading])

  useEffect(() => {
    if (!isAuthenticated) {
      setBookmarkedItems(new Set())
    }
  }, [isAuthenticated])

  const handleAddKeyword = () => {
    const trimmedKeyword = newKeyword.trim()
    const allTopics = [...defaultTopics, ...customTopics]

    if (!trimmedKeyword) {
      showTemporaryMessage('Please enter a keyword')
      return
    }

    if (allTopics.includes(trimmedKeyword)) {
      showTemporaryMessage('This keyword already exists in your topics')
      return
    }

    const updatedTopics = [...customTopics, trimmedKeyword]
    setCustomTopics(updatedTopics)
    setNewKeyword('')
    showTemporaryMessage('Keyword added successfully!', 1000)
    
    // Save to backend for authenticated users
    if (isAuthenticated) {
      saveUserPreferences(updatedTopics)
    }
  }

  const handleRemoveCustomTopic = (topicToRemove: string) => {
    const updatedTopics = customTopics.filter(topic => topic !== topicToRemove)
    setCustomTopics(updatedTopics)
    
    // Save to backend for authenticated users
    if (isAuthenticated) {
      saveUserPreferences(updatedTopics)
    }
  }

  const handleBookmark = async (item: any) => {
    if (!isAuthenticated) {
      showTemporaryMessage('⚠️ Login required: Please click the login icon to bookmark items', 4000)
      return
    }

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const isCurrentlyBookmarked = bookmarkedItems.has(item.link)
      // sessionToken is available from useAuth hook above

      if (isCurrentlyBookmarked) {
        // Remove bookmark
        const response = await fetch(`${apiUrl}/api/bookmarks?link=${encodeURIComponent(item.link)}`, {
          method: 'DELETE',
          headers: {
            'Authorization': `Bearer ${sessionToken}`,
          },
        })

        if (response.ok) {
          setBookmarkedItems(prev => {
            const newSet = new Set(prev)
            newSet.delete(item.link)
            return newSet
          })
        }
      } else {
        // Add bookmark
        const response = await fetch(`${apiUrl}/api/bookmarks`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${sessionToken}`,
          },
          body: JSON.stringify({
            title: item.title,
            link: item.link,
            source: item.source,
            summary: item.summary
          })
        })

        if (response.ok) {
          setBookmarkedItems(prev => new Set([...prev, item.link]))
        }
      }
    } catch (error) {
      console.error('Failed to toggle bookmark:', error)
    }
  }

  const loadBookmarkStatus = async () => {
    if (!isAuthenticated || !sessionToken) return

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const response = await fetch(`${apiUrl}/api/bookmarks`, {
        headers: {
          'Authorization': `Bearer ${sessionToken}`,
        },
      })

      if (response.ok) {
        const data = await response.json()
        const bookmarkedLinks = new Set<string>(data.items.map((bookmark: any) => String(bookmark.link)))
        setBookmarkedItems(bookmarkedLinks)
      }
    } catch (error) {
      console.error('Failed to load bookmark status:', error)
    }
  }

  // ==============================
  // UTILITY FUNCTIONS
  // ==============================

  // Reusable filtering logic
  const filterItems = (items: any[], searchQuery: string = '') => {
    return items.filter(item => {
      // Text search filter
      if (searchQuery.trim()) {
        const query = searchQuery.toLowerCase()
        const titleMatch = item.title?.toLowerCase().includes(query)
        const summaryMatch = item.summary?.toLowerCase().includes(query)
        if (!titleMatch && !summaryMatch) return false
      }

      // Tag filter
      if (selectedTags.size === 0) return true
      // Check if item matches any selected tag
      for (const tag of selectedTags) {
        // Filter by source tag
        if (item.source === tag) return true
        // Filter by matched keywords
        if (item.matched_keywords && item.matched_keywords.includes(tag)) return true
      }
      return false
    })
  }

  // Pagination helper function
  const paginateItems = (items: any[], page: number, searchQuery: string = '') => {
    const filtered = filterItems(items, searchQuery)
    const startIndex = (page - 1) * itemsPerPage
    return filtered.slice(startIndex, startIndex + itemsPerPage)
  }

  // Check bookmark status when results are loaded
  useEffect(() => {
    setPaginatedItems(paginateItems(fetchedItems, currentPage, debouncedHomepageSearch))
  }, [fetchedItems, selectedTags, currentPage, itemsPerPage, bookmarkedItems, debouncedHomepageSearch])

  useEffect(() => {
    setPaginatedBookmarks(paginateItems(bookmarkedCards, bookmarksPage, debouncedBookmarkSearch))
  }, [bookmarkedCards, selectedTags, bookmarksPage, itemsPerPage, debouncedBookmarkSearch])

  // Helper function to check if summary needs "Read More"
  const checkSummaryOverflow = (element: HTMLElement) => {
    const isOverflowing = element.scrollHeight > element.clientHeight + 20
    const textContent = element.textContent || ''
    const isLongEnoughText = textContent.length > 150
    return isOverflowing && isLongEnoughText
  }

  useEffect(() => {
    const newShowReadMore = new Set<string>()
    const checkSummaries = () => {
      document.querySelectorAll('[data-summary-text]').forEach(p => {
        const element = p as HTMLElement
        if (checkSummaryOverflow(element)) {
          const link = element.dataset.summaryText
          if (link) {
            newShowReadMore.add(link)
          }
        }
      })
      setShowReadMore(newShowReadMore)
    }

    const timeoutId = setTimeout(checkSummaries, 100)
    return () => clearTimeout(timeoutId)
  }, [paginatedItems, paginatedBookmarks, expandedSummaries])

  const refreshBookmarks = async (searchDays?: number | null, searchLimit?: number) => {
    if (!isAuthenticated || !sessionToken) return

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const params = new URLSearchParams()

      const days = searchDays !== undefined ? searchDays : bookmarkSearchDays
      const limit = searchLimit !== undefined ? searchLimit : bookmarkSearchLimit

      if (days !== null && days !== undefined) {
        params.append('days', days.toString())
      }
      params.append('limit', limit.toString())

      const url = `${apiUrl}/api/bookmarks?${params.toString()}`
      console.log('Fetching bookmarks from:', url)

      const response = await fetch(url, {
        headers: {
          'Authorization': `Bearer ${sessionToken}`,
        },
      })

      if (response.ok) {
        const data = await response.json()
        setBookmarkedCards(data.items)
        console.log('Bookmarks fetched successfully:', data.items.length)
      } else {
        console.error('Failed to fetch bookmarks, status:', response.status)
      }
    } catch (error) {
      console.error('Failed to fetch bookmarks:', error)
    }
  }

  const handleReturnHome = () => {
    // Close auth modal if open and restore previous view if available
    if (showAuthModal && previousViewState) {
      setShowResults(previousViewState.showResults)
      setShowBookmarks(previousViewState.showBookmarks)
      setPreviousViewState(null)
      setShowAuthModal(false)
      return
    } else if (showAuthModal) {
      setShowAuthModal(false)
    }

    // Reset to default search state
    if (showBookmarks) {
      setShowBookmarks(false)
      setBookmarkedCards([])
      setExpandedSummaries(new Set())
      setSelectedTags(new Set())
      setBookmarksPage(1)
      setUploadUrl('')
      setUploadMessage('')
    }

    // Reset any loading states
    setIsLoading(false)
    setProgressMessage('')

    // Clear any messages
    setKeywordMessage('')
    setUploadMessage('')
    setUploadProgressMessage('')

    // Reset to default time range
    setSelectedDays(1)

    // Close advanced settings
    setShowAdvancedSettings(false)
  }

  const handleViewBookmarks = async () => {
    if (!isAuthenticated) {
      showTemporaryMessage('⚠️ Login required: Please click the login icon to access bookmarks', 4000)
      return
    }

    setShowAdvancedSettings(false)

    if (showBookmarks) {
      setShowBookmarks(false)
      setBookmarkedCards([])
      setExpandedSummaries(new Set())
      setSelectedTags(new Set())
      setBookmarksPage(1)
      setUploadUrl('')
      setUploadMessage('')
      return
    }

    try {
      await refreshBookmarks()
      setShowBookmarks(true)
      setExpandedSummaries(new Set())
      setSelectedTags(new Set())
      setBookmarksPage(1)
      setUploadUrl('')
      setUploadMessage('')
    } catch (error) {
      console.error('Failed to fetch bookmarks:', error)
    }
  }


  const confirmDelete = async () => {
    if (!deleteConfirmItem || !sessionToken) return

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const response = await fetch(`${apiUrl}/api/bookmarks?link=${encodeURIComponent(deleteConfirmItem.link)}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${sessionToken}`,
        },
      })

      if (response.ok) {
        setBookmarkedItems(prev => {
          const newSet = new Set(prev)
          newSet.delete(deleteConfirmItem.link)
          return newSet
        })
        if (showBookmarks) {
          refreshBookmarks()
        }
      }
    } catch (error) {
      console.error('Failed to delete bookmark:', error)
    } finally {
      setDeleteConfirmItem(null)
      setDeleteConfirmPosition(null)
    }
  }

  const handleEditSummary = (item: any) => {
    setEditingSummary(item.link)
    setEditedSummaryText(item.summary)
  }

  const handleCancelEditSummary = () => {
    setEditingSummary(null)
    setEditedSummaryText('')
  }

  const handleSaveSummary = async (link: string) => {
    if (!editedSummaryText.trim() || !sessionToken) {
      return
    }

    setIsUpdatingSummary(true)
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const response = await fetch(`${apiUrl}/api/bookmarks/summary?link=${encodeURIComponent(link)}&summary=${encodeURIComponent(editedSummaryText)}`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${sessionToken}`,
        },
      })

      if (response.ok) {
        if (showBookmarks) {
          refreshBookmarks()
        }
        handleCancelEditSummary()
      }
    } catch (error) {
      console.error('Failed to update summary:', error)
    } finally {
      setIsUpdatingSummary(false)
    }
  }

  const handleUploadLink = async () => {
    if (!isAuthenticated) {
      setUploadMessage('⚠️ Login required: Please click the login icon to upload bookmarks')
      setTimeout(() => setUploadMessage(''), 4000)
      return
    }

    if (!uploadUrl.trim()) {
      setUploadMessage('Please enter at least one URL')
      setTimeout(() => setUploadMessage(''), 3000)
      return
    }

    // Parse multiple URLs separated by commas
    const urlStrings = uploadUrl.split(',').map(url => url.trim()).filter(url => url)
    const validUrls: string[] = []

    // Validate each URL
    for (const urlString of urlStrings) {
      try {
        new URL(urlString)
        validUrls.push(urlString)
      } catch {
        setUploadMessage(`Invalid URL: ${urlString}. Please check your URLs and try again.`)
        setTimeout(() => setUploadMessage(''), 4000)
        return
      }
    }

    if (validUrls.length === 0) {
      setUploadMessage('No valid URLs found. Please enter valid URLs starting with http:// or https://')
      setTimeout(() => setUploadMessage(''), 3000)
      return
    }

    // Check if we exceed the server limit (dynamic from backend)
    if (validUrls.length > appConfig.max_urls_per_request) {
      setUploadMessage(`❌ Too many URLs: Maximum ${appConfig.max_urls_per_request} URLs allowed per request, you provided ${validUrls.length}`)
      setTimeout(() => setUploadMessage(''), 4000)
      return
    }

    setIsUploading(true)
    setUploadProgress(0)
    setUploadProgressMessage(`Starting to process ${validUrls.length} URL${validUrls.length > 1 ? 's' : ''}...`)

    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
    let successful = 0
    let failed = 0

    try {
      // Process URLs one by one to show real progress
      for (let i = 0; i < validUrls.length; i++) {
        const currentUrl = validUrls[i]
        const urlNumber = i + 1

        setUploadProgressMessage(`Processing URL ${urlNumber}/${validUrls.length}: ${currentUrl.length > 50 ? currentUrl.substring(0, 50) + '...' : currentUrl}`)

        try {
          const response = await fetch(`${apiUrl}/api/content`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${sessionToken}`,
            },
            body: JSON.stringify({ urls: [currentUrl] })
          })

          const result = await response.json()

          if (response.ok && result.success) {
            successful++
            setUploadProgressMessage(`✅ Processed ${urlNumber}/${validUrls.length}: Success`)
          } else {
            failed++
            const errorMsg = result.detail?.message || result.detail || result.message || 'Failed'
            setUploadProgressMessage(`❌ Processed ${urlNumber}/${validUrls.length}: ${errorMsg}`)
          }

        } catch (error) {
          failed++
          setUploadProgressMessage(`❌ Processed ${urlNumber}/${validUrls.length}: Network error`)
        }

        // Update progress after processing each URL
        const progressPercent = Math.floor(((i + 1) / validUrls.length) * 100)
        setUploadProgress(progressPercent)

        // Small delay to show the result message briefly
        await new Promise(resolve => setTimeout(resolve, 800))
      }

      // Final results after processing all URLs
      if (successful === validUrls.length) {
        setUploadProgressMessage(`All ${successful} URL${successful > 1 ? 's' : ''} processed successfully!`)
        setUploadMessage(`🎉 Successfully processed ${successful} URL${successful > 1 ? 's' : ''}!`)
      } else if (successful > 0) {
        setUploadProgressMessage(`${successful}/${validUrls.length} URLs processed successfully`)
        setUploadMessage(`⚠️ Processed ${successful} URL${successful > 1 ? 's' : ''} successfully, ${failed} failed.`)
      } else {
        setUploadProgressMessage(`Failed to process all ${validUrls.length} URL${validUrls.length > 1 ? 's' : ''}`)
        setUploadMessage(`❌ Failed to process all URLs. Please check the URLs and try again.`)
      }

      setUploadUrl('')

      // Refresh bookmarks to show new items if any were successful
      if (showBookmarks && successful > 0) {
        refreshBookmarks()
      }

    } catch (error) {
      console.error('Failed to upload links:', error)
      setUploadMessage('Failed to process URLs. Please try again.')
    } finally {
      setTimeout(() => {
        setIsUploading(false)
        setUploadProgress(0)
        setUploadProgressMessage('')
        setUploadMessage('')
      }, 3000)
    }
  }

  const toggleSummaryExpansion = (itemLink: string) => {
    setExpandedSummaries(prev => {
      const newSet = new Set(prev)
      if (newSet.has(itemLink)) {
        newSet.delete(itemLink)
      } else {
        newSet.add(itemLink)
      }
      return newSet
    })
  }

  const handleTagFilter = (tag: string) => {
    setSelectedTags(prev => {
      const newSet = new Set(prev)
      if (newSet.has(tag)) {
        newSet.delete(tag)
      } else {
        newSet.add(tag)
      }
      return newSet
    })
    setCurrentPage(1) // Reset to first page when filtering
    setBookmarksPage(1) // Reset bookmarks page too
  }



  const handleExportBookmarks = async () => {
    if (!isAuthenticated || !sessionToken) {
      showTemporaryMessage('⚠️ Login required: Please click the login icon to export bookmarks', 4000)
      return
    }

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

      // Build URL with filter parameters based on current state
      const params = new URLSearchParams()

      // Add selected tags if any
      if (selectedTags.size > 0) {
        params.append('selected_tags', Array.from(selectedTags).join(','))
      }

      // Add search query if any (use bookmark search query when in bookmark mode)
      const searchQuery = showBookmarks ? bookmarkSearchQuery : homepageSearchQuery
      if (searchQuery.trim()) {
        params.append('search_query', searchQuery)
      }

      // Export HTML format
      params.append('export_format', 'html')

      const url = `${apiUrl}/api/bookmarks/export/chrome?${params.toString()}`
      const response = await fetch(url, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${sessionToken}`,
        },
      })

      if (response.ok) {
        const contentDisposition = response.headers.get('Content-Disposition')
        let filename = 'multimodal_scout_chrome_bookmarks.html'

        if (contentDisposition) {
          const filenameMatch = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/)
          if (filenameMatch && filenameMatch[1]) {
            filename = filenameMatch[1].replace(/['"]/g, '')
          }
        }

        const blob = await response.blob()
        const url = window.URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.style.display = 'none'
        a.href = url
        a.download = filename
        document.body.appendChild(a)
        a.click()
        window.URL.revokeObjectURL(url)
        document.body.removeChild(a)
      } else {
        console.error('Failed to export bookmarks')
      }
    } catch (error) {
      console.error('Failed to export bookmarks:', error)
    }
  }

  // Pagination component
  const PaginationControls = ({ currentPage, setCurrentPage, totalItems, itemsPerPage }: {
    currentPage: number
    setCurrentPage: (page: number) => void
    totalItems: number
    itemsPerPage: number
  }) => {
    const totalPages = Math.ceil(totalItems / itemsPerPage)

    if (totalPages <= 1 || totalItems === 0) {
      return null
    }


    return (
      <div className="flex justify-center items-center gap-2 mt-6 p-4 rounded-lg">
        <span className="text-sm text-gray-700 mr-4">
          Page {currentPage} of {totalPages}
        </span>

        <button
          onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
          disabled={currentPage === 1}
          className="px-4 py-2 text-sm text-gray-700 rounded-lg disabled:cursor-not-allowed hover:bg-blue-700 transition-colors"
        >
          Previous
        </button>

        {Array.from({ length: totalPages }, (_, i) => i + 1).map(page => (
          <button
            key={page}
            onClick={() => setCurrentPage(page)}
            className={`px-3 py-2 text-sm rounded-lg border transition-colors ${
              currentPage === page
                ? 'bg-white text-gray-700 border-blue-600'
                : 'border-gray-300 text-gray-700'
            }`}
          >
            {page}
          </button>
        ))}

        <button
          onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
          disabled={currentPage === totalPages}
          className="px-4 py-2 text-sm text-gray-700 rounded-lg disabled:cursor-not-allowed hover:bg-blue-700 transition-colors"
        >
          Next
        </button>
      </div>
    )
  }

  // Helper function to handle stream events
  const handleStreamEvent = (eventData: any) => {
    switch (eventData.type) {
      case 'status':
        setProgressMessage(eventData.message)
        break
      case 'start':
        setProgressMessage(eventData.message)
        break
      case 'progress':
        setProgressMessage(eventData.message)
        break
      case 'complete':
        setProgressMessage(eventData.message)
        break
      case 'info':
      case 'warning':
        setProgressMessage(eventData.message)
        break
      case 'error':
        console.error('Stream error:', eventData.message)
        alert(`Error: ${eventData.message}`)
        break
      case 'result':
        setFetchedItems(eventData.data.items)
        setShowResults(true)
        setShowBookmarks(false)
        setExpandedSummaries(new Set())
        setSelectedTags(new Set())
        setCurrentPage(1)
        if (eventData.data.items.length > 0) {
          setProgressMessage('Complete!')
          loadBookmarkStatus()
        }
        break
    }
  }

  // Helper function to process stream data
  const processStreamData = async (reader: ReadableStreamDefaultReader<Uint8Array>) => {
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (line.startsWith('data: ') && line !== 'data: [DONE]') {
          try {
            const eventData = JSON.parse(line.slice(6))
            handleStreamEvent(eventData)
          } catch (parseError) {
            console.error('Failed to parse event data:', parseError)
          }
        } else if (line === 'data: [DONE]') {
          break
        }
      }
    }
  }

  const handleFetchItems = async () => {
    setIsLoading(true)
    setShowBookmarks(false)
    setShowAdvancedSettings(false) // Close settings panel when search starts
    setShowAuthModal(false) // Close auth modal when search starts
    setProgressMessage('Starting fetch...')

    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), 30000)

    try {
      const allTopics = [...defaultTopics, ...customTopics]
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

      const headers: Record<string, string> = { 'Content-Type': 'application/json' }
      if (sessionToken) {
        headers['Authorization'] = `Bearer ${sessionToken}`
      }

      const response = await fetch(`${apiUrl}/api/content/search/stream`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ selectedDays, topics: allTopics, maxResults, researchRatio, sessionId, discoveryMode }),
        signal: controller.signal
      })

      if (!response.ok) {
        // Check for rate limiting first
        if (response.status === 429) {
          try {
            const errorData = await response.json()
            if (errorData.error === 'rate_limit_exceeded') {
              throw new Error(`RATE_LIMIT: ${errorData.message}`)
            }
            // If 429 but not our expected rate limit format, still treat as rate limit
            throw new Error(`RATE_LIMIT: Daily search limit exceeded for guest users. Please register for unlimited access.`)
          } catch (parseError) {
            // If we can't parse a 429 response, assume it's rate limiting
            throw new Error(`RATE_LIMIT: Daily search limit exceeded for guest users. Please register for unlimited access.`)
          }
        }
        // For other HTTP errors, throw generic error
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const reader = response.body?.getReader()
      if (!reader) {
        throw new Error('Failed to get response reader')
      }

      await processStreamData(reader)

    } catch (error) {
      console.error('Failed to fetch items:', error)
      const errorMessage = error instanceof Error ? error.message : 'Unknown error'

      if (error instanceof DOMException && error.name === 'AbortError') {
        setProgressMessage('Search timed out. Please try again.')
      } else if (errorMessage.startsWith('RATE_LIMIT:')) {
        const rateLimitMessage = errorMessage.replace('RATE_LIMIT: ', '')
        showTemporaryMessage(`⚠️ ${rateLimitMessage}`, 8000)
        setProgressMessage('Rate limit exceeded')
      } else {
        alert('Failed to fetch items. Please check if the backend server is running.')
        setProgressMessage('Failed to fetch items')
      }
    } finally {
      clearTimeout(timeoutId)
      setTimeout(() => {
        setIsLoading(false)
        setProgressMessage(prev => prev === 'Complete!' ? '' : prev)
      }, 2000)
    }
  }

  // ==============================
  // COMPONENT RENDER
  // ==============================

  return (
    <main className="min-h-screen bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="text-center mb-12">
          <h1 className="text-5xl font-bold text-gray-900 mb-4">
            Multimodal Scout
          </h1>
          <p className="text-xl text-gray-600 mb-2">
            Find top stories and papers related to multimodal AI and AI agents.
          </p>
          <p className="text-sm text-gray-600">
            An open source project • <a href="https://github.com/yingzha/multimodal-scout/" target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:text-blue-800 underline">View on GitHub</a>
          </p>
        </div>

        {/* Interest Topics Section */}
        <div className="bg-orange-100 rounded-lg p-8 mb-12">
          <div className="mb-6 flex justify-between items-center">
            <h2 className="text-2xl font-bold text-gray-800">
              {showBookmarks ? 'Bring Your Own URLs' : 'My Interested Topics'}
            </h2>
            {showBookmarks ? (
              <div className="flex items-center gap-4">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-gray-700">Last</span>
                  <select
                    value={bookmarkSearchDays || 'all'}
                    onChange={(e) => {
                      const days = e.target.value === 'all' ? null : parseInt(e.target.value)
                      setBookmarkSearchDays(days)
                      refreshBookmarks(days, bookmarkSearchLimit)
                    }}
                    className="px-2 py-1 text-sm border  border-gray-300 text-gray-700 rounded-full focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="all">All time</option>
                    <option value="1">1 day</option>
                    <option value="3">3 days</option>
                    <option value="7">7 days</option>
                    <option value="30">30 days</option>
                  </select>
                  <span className="text-sm font-medium text-gray-700">|</span>
                  <span className="text-sm font-medium text-gray-700">Show</span>
                  <select
                    value={bookmarkSearchLimit}
                    onChange={(e) => {
                      const limit = parseInt(e.target.value)
                      setBookmarkSearchLimit(limit)
                      refreshBookmarks(bookmarkSearchDays, limit)
                    }}
                    className="px-2 py-1 text-sm border border-gray-300 text-gray-700 rounded-full focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="10">10</option>
                    <option value="25">25</option>
                    <option value="50">50</option>
                    <option value="100">100</option>
                  </select>
                  <span className="text-sm font-medium text-gray-700">items</span>
                </div>
              </div>
            ) : (
              <div className="flex items-center gap-4">
                <span className="text-sm font-medium text-blue-700">Discovery Mode</span>
              <button
                onClick={() => {
                  console.log('Toggle clicked, current state:', discoveryMode)
                  setDiscoveryMode(!discoveryMode)
                }}
                className={`relative inline-flex h-5 w-8 flex-shrink-0 cursor-pointer rounded-full transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-gray-300 focus:ring-offset-1 ${
                  discoveryMode ? 'bg-gray-500' : 'bg-gray-100'
                }`}
                style={{
                  boxShadow: 'inset 0 1px 3px rgba(0, 0, 0, 0.3), 0 1px 0 rgba(255, 255, 255, 0.1)'
                }}
                role="switch"
                aria-checked={discoveryMode}
                aria-label="Toggle discovery mode"
              >
                <span
                  className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow-sm ring-0 transition duration-200 ease-in-out ${
                    discoveryMode ? 'translate-x-3' : 'translate-x-0'
                  }`}
                  style={{
                    transform: discoveryMode ? 'translateX(12px)' : 'translateX(0px)',
                    transition: 'transform 200ms ease-in-out'
                  }}
                />
              </button>
              </div>
            )}
          </div>

          {showBookmarks ? (
            /* Smart Processing Mode - URL Input */
            <div className="space-y-4">
              <div className="text-sm text-gray-700 mb-4">
                🔗 Add one or more URLs (separated by commas, max {appConfig.max_urls_per_request}) and we'll automatically extract the content, create smart summaries, and organize them for you!
              </div>
              <div className="flex gap-2">
                <input
                  type="url"
                  value={uploadUrl}
                  onChange={(e) => setUploadUrl(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && !isUploading && handleUploadLink()}
                  placeholder="https://example.com/article"
                  className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-gray-700"
                  disabled={isUploading}
                />
                <button
                  onClick={handleUploadLink}
                  disabled={isUploading}
                  className={`w-14 h-14 rounded-full focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2 font-medium flex items-center justify-center transition-colors ${
                    isUploading
                      ? 'text-gray-700 hover:bg-orange-200 cursor-not-allowed'
                      : 'text-gray-700 hover:bg-orange-200'
                  }`}
                  data-tooltip={isUploading ? 'Processing URL...' : 'Add URL to bookmarks'}
                >
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                  </svg>
                </button>
              </div>

              {/* Upload Progress Message */}
              {isUploading && uploadProgressMessage && (
                <div className="text-sm text-blue-700 text-center font-medium">
                  {uploadProgressMessage}{uploadProgressMessage && ` (${uploadProgress}%)`}
                </div>
              )}

              {uploadMessage && (
                <div className={`text-sm font-medium p-3 rounded-lg ${
                  uploadMessage.includes('successfully')
                    ? 'text-green-700 bg-green-50 border border-green-200'
                    : uploadMessage.includes('Processing')
                    ? 'text-blue-700 bg-blue-50 border border-blue-200'
                    : uploadMessage.includes('already been added !') || uploadMessage.includes('already bookmarked !')
                    ? 'text-orange-700 bg-orange-50 border border-orange-200'
                    : 'text-red-700 bg-red-50 border border-red-200'
                }`}>
                  {uploadMessage}
                </div>
              )}
            </div>
          ) : isLoadingTopics ? (
            <div className="flex justify-center items-center py-4">
              <div className="text-gray-700">Loading topics...</div>
            </div>
          ) : (
            <>
              {/* Hide topics when discovery mode is enabled */}
              {!discoveryMode && (
                <div className="flex flex-wrap gap-3 mb-6">
                  {/* Default Topics (Read-only) */}
                  {defaultTopics.map((topic, index) => (
                    <span
                      key={`default-${index}`}
                      className="inline-flex items-center px-4 py-2 bg-white rounded-full border border-gray-200 text-gray-800"
                    >
                      {topic}
                      <span className="ml-3 text-gray-400 text-sm" data-tooltip="Default system topic">🔒</span>
                    </span>
                  ))}

                  {/* Custom Topics (Removable) */}
                  {customTopics.map((topic, index) => (
                    <span
                      key={`custom-${index}`}
                      className="inline-flex items-center px-4 py-2 bg-white rounded-full border border-gray-200 text-gray-800"
                    >
                      {topic}
                      <button
                        onClick={() => handleRemoveCustomTopic(topic)}
                        className="ml-3 w-5 h-5 rounded-full flex items-center justify-center focus:outline-none transition-colors text-sm font-bold hover:bg-red-500 hover:text-white"
                        title="Remove keyword"
                      >
                        ×
                      </button>
                    </span>
                  ))}
                </div>
              )}

              {/* Discovery Mode Info */}
              {discoveryMode && (
                <div className="mb-6 p-4 border border-blue-200 rounded-lg">
                  <div className="flex items-start gap-2">
                    <span className="flex-shrink-0 text-blue-600">✨</span>
                    <div className="text-sm text-purple-700">
                      <strong>Discovery Mode Active:</strong> Randomly sampling from all available content for serendipitous discovery. Your topics are disabled while discovery mode is on.
                    </div>
                  </div>
                </div>
              )}
            </>
          )}

          {/* Add Keywords Input - Hide in bookmark mode and discovery mode */}
          {!showBookmarks && !discoveryMode && (
            <div className="flex gap-4">
            <div className="flex gap-2 flex-1">
              <input
                type="text"
                value={newKeyword}
                onChange={(e) => setNewKeyword(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleAddKeyword()}
                placeholder="Add keywords (e.g., computer vision, robotics)"
                className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent text-gray-700"
              />
              <button
                onClick={handleAddKeyword}
                className="w-14 h-14 rounded-full focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2 font-medium flex items-center justify-center transition-colors text-gray-700 hover:bg-orange-200"
                data-tooltip="Add keyword"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
              </button>
            </div>
            </div>
          )}

          {/* Keyword feedback message - only show when not in bookmark mode and not in discovery mode */}
          {!showBookmarks && !discoveryMode && keywordMessage && (
            <div className={`mt-6 text-sm font-medium p-3 rounded-lg ${
              keywordMessage.includes('successfully')
                ? 'text-green-700 bg-green-50 border border-green-200'
                : keywordMessage.includes('already exists') || keywordMessage.includes('Please enter')
                ? 'text-red-700 bg-red-50 border border-red-200'
                : 'text-gray-700 bg-gray-50 border border-gray-200'
            }`}>
              {keywordMessage}
            </div>
          )}

          {/* Bookmark mode info message */}
          {showBookmarks && (
            <div className="mt-6 text-sm text-gray-600 border border-gray-200 p-3 rounded-lg">
              <div className="flex items-start gap-2">
                <span className="flex-shrink-0">ℹ️</span>
                <div>
                  Search settings are disabled in this view as they only apply to content discovery.
                </div>
              </div>
            </div>
          )}

          {/* Settings and Bookmarks Icons */}
          <div className="flex justify-between items-center mt-6 relative z-10">
            <div className="flex items-center gap-4">
              <button
                onClick={handleReturnHome}
                className="bg-gray-100 p-3 text-gray-700 hover:text-gray-900 hover:bg-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-500 transition-colors flex items-center justify-center"
                data-tooltip="Homepage"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V9Z"/>
                  <polyline points="9,22 9,12 15,12 15,22"/>
                </svg>
              </button>
              <button
                onClick={handleViewBookmarks}
                className="bg-gray-100 p-3 text-gray-700 hover:text-gray-900 hover:bg-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-500 transition-colors flex items-center justify-center"
                data-tooltip="Bookmarks"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z" />
                </svg>
              </button>
              <button
                onClick={handleGearClick}
                disabled={isLoading || showBookmarks}
                className={`bg-gray-100 p-3 text-gray-700 hover:text-gray-900 hover:bg-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-500 transition-colors flex items-center justify-center ${
                  isLoading || showBookmarks ? 'cursor-not-allowed opacity-50' : ''
                }`}
                data-tooltip='Search Settings'
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
              </button>
              <ThemeToggle />

              {isAuthenticated ? (
                <div className="relative" ref={userMenuRef}>
                  <button
                    onClick={() => setShowUserMenu(!showUserMenu)}
                    className="bg-gray-100 p-3 text-gray-700 hover:text-gray-900 hover:bg-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-500 transition-colors flex items-center justify-center"
                    data-tooltip="User Menu"
                  >
                    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                    </svg>
                  </button>

                  {showUserMenu && (
                    <div className="absolute right-0 top-full mt-2 w-64 bg-white rounded-lg shadow-lg border border-gray-200 py-3 px-4 z-50">
                      <div className="flex items-center gap-3 mb-3 pb-3 border-b border-gray-100">
                        <div className="w-8 h-8 bg-gray-300 rounded-full flex items-center justify-center">
                          <span className="text-gray-600 font-medium text-sm">
                            {user?.username?.charAt(0).toUpperCase()}
                          </span>
                        </div>
                        <div>
                          <p className="font-medium text-gray-900">Hello, {user?.username}!</p>
                          <p className="text-xs text-gray-500">{user?.email}</p>
                        </div>
                      </div>
                      <button
                        onClick={() => {
                          logout()
                          resetToHomepage()
                        }}
                        className="w-full text-left px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 rounded-md transition-colors"
                      >
                        Logout
                      </button>
                    </div>
                  )}
                </div>
              ) : (
                <button
                  onClick={() => {
                    if (showAuthModal) {
                      // If modal is open, close it and restore previous view
                      if (previousViewState) {
                        setShowResults(previousViewState.showResults)
                        setShowBookmarks(previousViewState.showBookmarks)
                        setPreviousViewState(null)
                      }
                      setShowAuthModal(false)
                    } else {
                      // If modal is closed, open it
                      setPreviousViewState({ showResults, showBookmarks })
                      setShowResults(false)
                      setShowBookmarks(false)
                      setShowAuthModal(true)
                    }
                  }}
                  className="bg-gray-100 p-3 text-gray-700 hover:text-gray-900 hover:bg-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-500 transition-colors flex items-center justify-center"
                  data-tooltip="Login"
                >
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                  </svg>
                </button>
              )}
            </div>

            {!showBookmarks && (
              <button
                onClick={handleFetchItems}
                disabled={isLoading}
                className={`px-8 py-3 text-white rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2 font-medium transition-colors ${
                  isLoading
                    ? 'bg-gray-500 hover:bg-gray-600 cursor-not-allowed'
                    : 'bg-gray-500 hover:bg-gray-600'
                }`}
              >
                {isLoading ? 'Search Content...' : 'Search'}
              </button>
            )}
          </div>
        </div>

        {/* Advanced Settings Panel */}
        {showAdvancedSettings && (
          <div className="rounded-lg p-6 mb-8">
            {/* Time Range Selector */}
          <div className="mb-6">
            <div className="flex items-center justify-center space-x-4">
              <span className="text-gray-700 font-medium">Show recently discovered content from the last</span>
              <input
                type="number"
                value={selectedDays}
                onChange={(e) => setSelectedDays(Number(e.target.value))}
                className="w-16 px-3 py-2 border border-gray-300 rounded-md text-center focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                min="1"
              />
              <span className="text-gray-700 font-medium">days</span>
              <div className="flex space-x-2">
                {[1, 3, 7].map((days) => (
                  <button
                    key={days}
                    onClick={() => setSelectedDays(days)}
                    className={`w-10 h-10 rounded-full text-sm font-medium transition-colors ${
                      selectedDays === days
                        ? 'bg-green-600 text-white shadow-lg ring-2 ring-green-300'
                        : 'bg-gray-300 text-gray-700 hover:bg-gray-400'
                    }`}
                  >
                    {days}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Number of Results and Content Balance - Side by Side */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-16 mb-6">
            {/* Number of Results */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-3">
                Number of Results: {maxResults}
              </label>
              <input
                type="range"
                min="5"
                max="50"
                step="5"
                value={maxResults}
                onChange={(e) => setMaxResults(Number(e.target.value))}
                className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <div className="flex justify-between text-xs text-gray-500 mt-2">
                <span>5</span>
                <span>25</span>
                <span>50</span>
              </div>
            </div>

            {/* Content Balance */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-3">
                Content Balance: {Math.round(researchRatio * 100)}% Research / {Math.round((1 - researchRatio) * 100)}% Industry
              </label>
              <input
                type="range"
                min="0"
                max="1"
                step="0.1"
                value={researchRatio}
                onChange={(e) => setResearchRatio(Number(e.target.value))}
                className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <div className="flex justify-between text-xs text-gray-500 mt-2">
                <span>All Industry</span>
                <span>Balanced</span>
                <span>All Research</span>
              </div>
            </div>
          </div>

          <div className="text-xs text-blue-700 p-3 rounded">
            <div className="flex items-start gap-2">
              <span className="flex-shrink-0">🎯</span>
              <div>
                <strong>Smart Balanced Search:</strong> Shows recently discovered content based on when we found it, not publication date. Prioritizes keyword matches first, then adds semantic matches by relevance score. Research papers use a higher similarity threshold to ensure quality, while industry content uses a lower threshold for variety.
              </div>
            </div>
          </div>
        </div>
        )}


        {/* Progress Message - Hide when viewing bookmarks */}
        {!showBookmarks && isLoading && progressMessage && (
          <div className="mt-6 text-center">
            <div className="inline-flex items-center px-4 py-2 text-blue-800 rounded-lg">
              <div className="animate-spin w-4 h-4 border-2 border-blue-600 border-t-transparent rounded-full mr-3"></div>
              <span className="text-sm font-medium">{progressMessage}</span>
            </div>
          </div>
        )}

        {/* Results Section */}
        {showResults && (!showBookmarks || showAdvancedSettings) && (
          <div className="mt-12">
            {fetchedItems.length === 0 ? (
              <div className="text-center py-12">
                <p className="text-lg font-medium text-gray-600 mb-2">No matching results found</p>
                <p className="text-sm text-gray-500">
                  {progressMessage || 'Try adjusting your topics or expanding the time range.'}
                </p>
              </div>
            ) : (
            <>
            <div className="flex justify-between items-center mb-6">
              <div className="flex items-center gap-3">
                <div className="text-sm text-gray-600">
                  {(() => {
                    const filteredItems = filterItems(fetchedItems, debouncedHomepageSearch)

                    const hasFilters = selectedTags.size > 0 || debouncedHomepageSearch.trim()
                    if (hasFilters) {
                      const filterParts = []
                      if (selectedTags.size > 0) {
                        filterParts.push(`tags: ${Array.from(selectedTags).map(tag => `"${tag}"`).join(', ')}`)
                      }
                      if (homepageSearchQuery.trim()) {
                        filterParts.push(`search: "${homepageSearchQuery}"`)
                      }
                      return `${filteredItems.length} results for ${filterParts.join(' + ')}`
                    }
                    return `${fetchedItems.length} results`
                  })()}
                </div>
                {selectedTags.size > 0 && (
                  <div className="flex items-center gap-2">
                    {Array.from(selectedTags).map(tag => (
                      <div key={tag} className="inline-flex items-center gap-1 px-3 py-1 bg-blue-100 text-blue-800 text-xs rounded-full">
                        <span>{tag}</span>
                        <button
                          onClick={() => handleTagFilter(tag)}
                          className="ml-2 w-4 h-4 bg-blue-200 hover:bg-gray-200 rounded-full flex items-center justify-center text-blue-600 hover:text-red-600 focus:outline-none transition-colors text-xs"
                          data-tooltip="Remove filter"
                        >
                          ×
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
              <div className="flex items-center gap-3">
                <div className="relative">
                  <input
                    type="text"
                    placeholder="Filter by keyword"
                    value={homepageSearchQuery}
                    onChange={(e) => setHomepageSearchQuery(e.target.value)}
                    className="w-48 px-3 py-1 pr-8 text-sm border border-gray-300 rounded-full focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                  {homepageSearchQuery ? (
                    <button
                      onClick={() => setHomepageSearchQuery('')}
                      className="w-4 h-4 absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600 focus:outline-none"
                      title="Clear filter"
                    >
                      <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  ) : (
                    <svg className="w-4 h-4 absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 pointer-events-none" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                    </svg>
                  )}
                </div>
              </div>
            </div>

            <div className="space-y-4">
              {paginatedItems.map((item, index) => {
                const startIndex = (currentPage - 1) * itemsPerPage
                return (
                <div
                  key={`${item.link}-${startIndex + index}`}
                  className="bg-white rounded-lg p-6 border border-gray-200 hover:shadow-lg transition-all duration-300"
                >
                  <div className="flex items-start justify-between mb-4">
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => handleTagFilter(item.source)}
                        className={`inline-block px-3 py-1 text-xs font-medium rounded-full transition-colors hover:opacity-80 focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                          selectedTags.has(item.source)
                            ? 'bg-blue-100 text-blue-800 ring-2 ring-blue-300'
                            : 'bg-gray-300 text-gray-800 hover:bg-gray-400'
                        }`}
                        title={`Filter by ${item.source}`}
                      >
                        {item.source}
                      </button>
                      {item.matched_keywords && item.matched_keywords.length > 0 && (
                        <div className="flex items-center gap-2">
                          {item.matched_keywords.map((keyword: string, keywordIndex: number) => (
                            <button
                              key={keywordIndex}
                              onClick={() => handleTagFilter(keyword)}
                              className={`px-3 py-1 text-xs font-medium rounded-full transition-colors hover:opacity-80 focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                                selectedTags.has(keyword)
                                  ? 'bg-blue-100 text-blue-800 ring-2 ring-blue-300'
                                  : 'bg-gray-300 text-gray-800 hover:bg-gray-400'
                              }`}
                              title={`Filter by keyword: ${keyword}`}
                            >
                              {keyword}
                            </button>
                          ))}
                        </div>
                      )}
                      {item.is_new && (
                        <span className="px-2 py-1 text-xs font-bold italic text-red-600 bg-red-100 rounded-full">
                          New!
                        </span>
                      )}
                    </div>
                    <button
                      onClick={() => handleBookmark(item)}
                      className={`w-8 h-8 flex items-center justify-center rounded-full focus:outline-none transition-colors ${
                        bookmarkedItems.has(item.link)
                          ? 'text-yellow-600 bg-yellow-100 hover:bg-yellow-200'
                          : 'text-gray-500 hover:text-yellow-600 hover:bg-yellow-100'
                      }`}
                      title={bookmarkedItems.has(item.link) ? 'Remove bookmark' : 'Add bookmark'}
                    >
                      {bookmarkedItems.has(item.link) ? '★' : '☆'}
                    </button>
                  </div>

                  <h3 className="text-xl font-semibold text-gray-900 mb-4 leading-tight">
                    {item.title}
                  </h3>

                  {/* Summary Section */}
                  {item.summary ? (
                    <div className="mb-4">
                      <div className="text-gray-700 text-sm leading-relaxed">
                        {expandedSummaries.has(item.link) ? (
                          // Full summary
                          <div>
                            <div>{item.summary.split('\n').map((line: string, index: number) => (
                              <div key={index} dangerouslySetInnerHTML={{ __html: line.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>') || '&nbsp;' }} />
                            ))}</div>
                            <button
                              onClick={() => toggleSummaryExpansion(item.link)}
                              className="mt-4 text-blue-600 hover:text-blue-800 text-xs focus:outline-none"
                            >
                              Show less ↑
                            </button>
                          </div>
                        ) : (
                          // Truncated summary
                          <div>
                            <div
                              className="line-clamp-2 overflow-hidden text-ellipsis"
                              style={{
                                display: '-webkit-box',
                                WebkitLineClamp: 2,
                                WebkitBoxOrient: 'vertical',
                                lineHeight: '1.5em',
                                maxHeight: '3em' // 2 lines * 1.5em line height
                              }}
                              data-summary-text={item.link}
                            >
                              {item.summary.split('\n').map((line: string, index: number) => (
                                <div key={index} dangerouslySetInnerHTML={{ __html: line.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>') || '&nbsp;' }} />
                              ))}
                            </div>
                            {showReadMore.has(item.link) && (
                              <button
                                onClick={() => toggleSummaryExpansion(item.link)}
                                className="mt-4 text-blue-600 hover:text-blue-800 text-xs rounded focus:outline-none"
                              >
                                Read more ↓
                              </button>
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                  ) : (
                    <div className="mb-4 text-xs text-gray-400 italic">
                      No summary available
                    </div>
                  )}

                  <div className="flex justify-between items-center">
                    <a
                      href={item.link}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center px-4 py-2 bg-gray-500 text-white text-sm font-medium rounded-lg hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-gray-500 transition-colors"
                    >
                      Read the original post →
                    </a>
                    {item.created_at && (
                      <span className="text-xs text-gray-500">
                        Created {new Date(item.created_at).toLocaleDateString()}
                      </span>
                    )}
                  </div>
                </div>
                )
              })}
            </div>

            {/* Pagination for Results */}
            <PaginationControls
              currentPage={currentPage}
              setCurrentPage={setCurrentPage}
              totalItems={filterItems(fetchedItems, debouncedHomepageSearch).length}
              itemsPerPage={itemsPerPage}
            />
            </>
            )}
          </div>
        )}

        {/* Bookmarks Section */}
        {showBookmarks && !showAdvancedSettings && (
          <div className="mt-12">
            {/* Bookmark Count and Search */}
            <div className="flex justify-between items-center mb-6">
              <div className="flex items-center gap-3">
                <div className="text-sm text-gray-600">
                  {(() => {
                    const filteredItems = filterItems(bookmarkedCards, debouncedBookmarkSearch)

                    const hasFilters = selectedTags.size > 0 || debouncedBookmarkSearch.trim()
                    if (hasFilters) {
                      const filterParts = []
                      if (selectedTags.size > 0) {
                        filterParts.push(`tags: ${Array.from(selectedTags).map(tag => `"${tag}"`).join(', ')}`)
                      }
                      if (bookmarkSearchQuery.trim()) {
                        filterParts.push(`search: "${bookmarkSearchQuery}"`)
                      }
                      return `${filteredItems.length} bookmarks for ${filterParts.join(' + ')}`
                    }
                    return `${bookmarkedCards.length} bookmarks`
                  })()}
                </div>
                {selectedTags.size > 0 && (
                  <div className="flex items-center gap-2">
                    {Array.from(selectedTags).map(tag => (
                      <div key={tag} className="inline-flex items-center gap-1 px-3 py-1 bg-blue-100 text-blue-800 text-xs rounded-full">
                        <span>{tag}</span>
                        <button
                          onClick={() => handleTagFilter(tag)}
                          className="ml-2 w-4 h-4 bg-blue-200 hover:bg-gray-200 rounded-full flex items-center justify-center text-blue-600 hover:text-red-600 focus:outline-none transition-colors text-xs"
                          data-tooltip="Remove filter"
                        >
                          ×
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
              <div className="flex items-center gap-3">
                <div className="relative">
                  <input
                    type="text"
                    placeholder="Filter by keyword"
                    value={bookmarkSearchQuery}
                    onChange={(e) => setBookmarkSearchQuery(e.target.value)}
                    className="w-48 px-3 py-1 pr-8 text-sm border border-gray-300 rounded-full focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                  {bookmarkSearchQuery ? (
                    <button
                      onClick={() => setBookmarkSearchQuery('')}
                      className="w-4 h-4 absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600 focus:outline-none"
                      title="Clear search"
                    >
                      <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  ) : (
                    <svg className="w-4 h-4 absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 pointer-events-none" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                    </svg>
                  )}
                </div>
                <button
                  onClick={handleExportBookmarks}
                  className="bg-gray-100 p-3 text-gray-700 hover:text-gray-900 hover:bg-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-500 transition-colors flex items-center justify-center"
                  data-tooltip="Export bookmarks"
                >
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                </button>
              </div>
            </div>

            {bookmarkedCards.length === 0 ? (
              <div className="text-center py-12">
                <div className="text-gray-600 text-lg mb-2">📚</div>
                <div className="text-gray-600">No bookmarks yet</div>
                <div className="text-gray-500 text-sm mt-1">
                  Start bookmarking articles by clicking the ☆ icon or upload your own links
                </div>
              </div>
            ) : (
              <>
                <div className="space-y-4">
                  {paginatedBookmarks.map((item, index) => {
                      const bookmarkStartIndex = (bookmarksPage - 1) * itemsPerPage
                      return (
                  <div
                    key={`bookmark-${item.link}-${bookmarkStartIndex + index}`}
                    className="bg-white rounded-lg p-6 border border-gray-200 hover:shadow-lg transition-all duration-300"
                  >
                    <div className="flex items-start justify-between mb-4">
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => handleTagFilter(item.source)}
                          className={`inline-block px-3 py-1 text-xs font-medium rounded-full transition-colors hover:opacity-80 focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                            selectedTags.has(item.source)
                              ? 'bg-blue-100 text-blue-800 ring-2 ring-blue-300'
                              : 'bg-gray-300 text-gray-800 hover:bg-gray-400'
                          }`}
                        >
                          {item.source}
                        </button>
                        {item.matched_keywords && item.matched_keywords.length > 0 && (
                          <div className="flex items-center gap-2">
                            {item.matched_keywords.map((keyword: string, keywordIndex: number) => (
                              <button
                                key={keywordIndex}
                                onClick={() => handleTagFilter(keyword)}
                                className={`px-3 py-1 text-xs font-medium rounded-full transition-colors hover:opacity-80 focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                                  selectedTags.has(keyword)
                                    ? 'bg-blue-100 text-blue-800 ring-2 ring-blue-300'
                                    : 'bg-gray-300 text-gray-800 hover:bg-gray-400'
                                }`}
                                title={`Filter by keyword: ${keyword}`}
                              >
                                {keyword}
                              </button>
                            ))}
                          </div>
                        )}
                      </div>
                      <button
                        onClick={(e) => {
                          const rect = e.currentTarget.getBoundingClientRect()
                          setDeleteConfirmPosition({
                            top: rect.bottom + window.scrollY + 10,
                            left: rect.left + window.scrollX - 200
                          })
                          setDeleteConfirmItem(item)
                        }}
                        className="w-8 h-8 flex items-center justify-center text-yellow-600 bg-yellow-100 hover:bg-yellow-200 rounded-full focus:outline-none transition-colors"
                        data-tooltip="Remove bookmark"
                      >
                        ★
                      </button>
                    </div>

                    <h3 className="text-xl font-semibold text-gray-900 mb-4 leading-tight">
                      {item.title}
                    </h3>

                    {/* Summary Section for Bookmarks */}
                    {item.summary && (
                      <div className="mb-4">
                        <div className="flex items-start justify-between">
                          <div className="flex items-center gap-2">
                            {item.summary_edited && (
                              <span className="text-xs px-2 py-1 bg-blue-100 text-blue-700 rounded-full mb-2">
                                edited
                              </span>
                            )}
                          </div>
                          {editingSummary !== item.link && (
                            <span
                              onClick={() => handleEditSummary(item)}
                              onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { handleEditSummary(item); } }}
                              role="button"
                              tabIndex={0}
                              data-tooltip="Edit summary"
                              className="text-xs text-gray-400 hover:text-gray-600 cursor-pointer focus:outline-none hover:bg-gray-600 rounded-full p-1 mb-2"
                            >
                              ✏️
                            </span>
                          )}
                        </div>

                        {editingSummary === item.link ? (
                          // Editing mode
                          <div className="space-y-3">
                            <textarea
                              value={editedSummaryText}
                              onChange={(e) => {
                                setEditedSummaryText(e.target.value);
                                const target = e.target as HTMLTextAreaElement;
                                target.style.height = 'auto';
                                target.style.height = `${target.scrollHeight}px`;
                              }}
                              className="w-full max-w-full p-4 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm leading-relaxed text-left resize-none overflow-hidden"
                              style={{
                                textAlign: 'left',
                                lineHeight: '1.6',
                                boxSizing: 'border-box',
                                resize: 'vertical'
                              }}
                              data-editing-summary={item.link}
                              rows={4}
                              placeholder="Edit the summary..."
                            />
                            <div className="flex gap-2">
                              <button
                                onClick={() => handleSaveSummary(item.link)}
                                disabled={isUpdatingSummary || !editedSummaryText.trim()}
                                className={`px-4 py-2 text-sm rounded-lg focus:outline-none transition-all duration-200 ${
                                  isUpdatingSummary || !editedSummaryText.trim()
                                    ? 'bg-gray-200 text-gray-700 cursor-not-allowed'
                                    : 'bg-gray-200 text-gray-700 hover:bg-gray-200'
                                }`}
                              >
                                {isUpdatingSummary ? 'Saving...' : 'Save'}
                              </button>
                              <button
                                onClick={handleCancelEditSummary}
                                disabled={isUpdatingSummary}
                                className="px-4 py-2 text-sm bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-200 focus:outline-none transition-colors"
                              >
                                Cancel
                              </button>
                            </div>
                          </div>
                        ) : (
                          // Display mode
                          <div className="text-gray-700 text-sm leading-relaxed">
                            {expandedSummaries.has(item.link) ? (
                              // Full summary
                              <div>
                                <div>{item.summary.split('\n').map((line: string, index: number) => (
                              <div key={index} dangerouslySetInnerHTML={{ __html: line.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>') || '&nbsp;' }} />
                            ))}</div>
                                <button
                                  onClick={() => toggleSummaryExpansion(item.link)}
                                  className="mt-2 text-blue-600 hover:text-blue-800 text-xs font-medium focus:outline-none"
                                >
                                  Show less ↑
                                </button>
                              </div>
                            ) : (
                              // Truncated summary
                              <div>
                                <div
                                  className="line-clamp-2 overflow-hidden text-ellipsis"
                                  style={{
                                    display: '-webkit-box',
                                    WebkitLineClamp: 2,
                                    WebkitBoxOrient: 'vertical',
                                    lineHeight: '1.5em',
                                    maxHeight: '3em' // 2 lines * 1.5em line height
                                  }}
                                  data-summary-text={item.link}
                                >
                                  {item.summary.split('\n').map((line: string, index: number) => (
                                    <div key={index} dangerouslySetInnerHTML={{ __html: line.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>') || '&nbsp;' }} />
                                  ))}
                                </div>
                                {showReadMore.has(item.link) && (
                                  <button
                                    onClick={() => toggleSummaryExpansion(item.link)}
                                    className="mt-2 text-blue-600 hover:text-blue-800 text-xs font-medium focus:outline-none"
                                  >
                                    Read more ↓
                                  </button>
                                )}
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    )}

                    <div className="flex justify-between items-center">
                      <a
                        href={item.link}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center px-4 py-2 bg-gray-500 text-white text-sm font-medium rounded-lg hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-gray-500 transition-colors"
                      >
                        Read the original post →
                      </a>
                      <span className="text-xs text-gray-500">
                        Saved {new Date(item.created_at).toLocaleDateString()}
                      </span>
                    </div>
                  </div>
                      )
                    })}
                </div>

                {/* Pagination for Bookmarks */}
                <PaginationControls
                  currentPage={bookmarksPage}
                  setCurrentPage={setBookmarksPage}
                  totalItems={filterItems(bookmarkedCards, debouncedBookmarkSearch).length}
                  itemsPerPage={itemsPerPage}
                />
              </>
            )}
          </div>
        )}

        {/* Delete Confirmation Dialog */}
        {deleteConfirmItem && deleteConfirmPosition && (
          <div
            className="fixed inset-0 z-50"
            onClick={() => {
              setDeleteConfirmItem(null)
              setDeleteConfirmPosition(null)
            }}
          >
            <div
              className="absolute bg-white rounded-lg p-4 max-w-sm shadow-2xl border border-gray-300"
              style={{
                top: `${deleteConfirmPosition.top}px`,
                left: `${Math.max(10, Math.min(deleteConfirmPosition.left, window.innerWidth - 250))}px`
              }}
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex justify-between items-center mb-3">
                <h3 className="text-lg font-semibold text-gray-900">
                  Delete Bookmark?
                </h3>
                <div className="flex gap-2">
                  <button
                    onClick={() => {
                      setDeleteConfirmItem(null)
                      setDeleteConfirmPosition(null)
                    }}
                    className="px-3 py-1 text-sm text-gray-800 bg-gray-200 rounded hover:bg-gray-200 focus:outline-none focus:ring-2 focus:ring-gray-500 transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={confirmDelete}
                    className="px-3 py-1 text-sm text-gray-900 bg-gray-200 rounded hover:bg-gray-200 focus:outline-none focus:ring-2 focus:ring-gray-500 transition-colors"
                  >
                    Delete
                  </button>
                </div>
              </div>
              <p className="text-blue-600 text-sm">
                Are you sure you want to delete "<strong>{deleteConfirmItem.title}</strong>"?
              </p>
            </div>
          </div>
        )}

        {/* Login Page View */}
        {showAuthModal && !showResults && !showBookmarks && (
          <div className="mt-12">
            <AuthModal
              isOpen={showAuthModal}
              onClose={() => {
                if (previousViewState) {
                  setShowResults(previousViewState.showResults)
                  setShowBookmarks(previousViewState.showBookmarks)
                  setPreviousViewState(null)
                }
                setShowAuthModal(false)
              }}
              onSuccess={(sessionToken, userInfo) => {
                login(sessionToken, userInfo)
                loadBookmarkStatus()
                setShowAuthModal(false)
                setPreviousViewState(null)
              }}
              asPage={true}
            />
          </div>
        )}

        {/* Authentication Modal (for other cases) */}
        {showAuthModal && (showResults || showBookmarks) && (
          <AuthModal
            isOpen={showAuthModal}
            onClose={() => setShowAuthModal(false)}
            onSuccess={(sessionToken, userInfo) => {
              login(sessionToken, userInfo)
              loadBookmarkStatus()
              setShowAuthModal(false)
            }}
          />
        )}
      </div>
    </main>
  )
}