'use client'

import { useState, useEffect, useRef } from 'react'
import ThemeToggle from './components/ThemeToggle'

export default function Home() {
  const [selectedDays, setSelectedDays] = useState(1)
  const [defaultTopics, setDefaultTopics] = useState<string[]>([])
  const [customTopics, setCustomTopics] = useState<string[]>([])
  const [newKeyword, setNewKeyword] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [progress, setProgress] = useState(0)
  const [progressMessage, setProgressMessage] = useState('')
  const [showDetailedProgress, setShowDetailedProgress] = useState(false)
  const [isLoadingTopics, setIsLoadingTopics] = useState(true)
  const [fetchedItems, setFetchedItems] = useState<any[]>([])
  const [showResults, setShowResults] = useState(false)
  const [bookmarkedItems, setBookmarkedItems] = useState<Set<string>>(new Set())
  const [showBookmarks, setShowBookmarks] = useState(false)
  const [bookmarkedCards, setBookmarkedCards] = useState<any[]>([])
  const [expandedSummaries, setExpandedSummaries] = useState<Set<string>>(new Set())
  const [keywordMessage, setKeywordMessage] = useState('')
  const [selectedTag, setSelectedTag] = useState<string | null>(null)
  const [currentPage, setCurrentPage] = useState(1)
  const [bookmarksPage, setBookmarksPage] = useState(1)
  const [paginatedItems, setPaginatedItems] = useState<any[]>([])
  const [paginatedBookmarks, setPaginatedBookmarks] = useState<any[]>([])
  const [showReadMore, setShowReadMore] = useState<Set<string>>(new Set())
  const [maxResults, setMaxResults] = useState(10)
  const itemsPerPage = 5
  const [researchRatio, setResearchRatio] = useState(0.5)
  const [uploadUrl, setUploadUrl] = useState('')
  const [isUploading, setIsUploading] = useState(false)
  const [uploadMessage, setUploadMessage] = useState('')
  const [uploadProgress, setUploadProgress] = useState(0)
  const [uploadProgressMessage, setUploadProgressMessage] = useState('')
  const [deleteConfirmItem, setDeleteConfirmItem] = useState<any>(null)
  const [deleteConfirmPosition, setDeleteConfirmPosition] = useState<{top: number, left: number} | null>(null)
  const [showAdvancedSettings, setShowAdvancedSettings] = useState(false)
  const [editingSummary, setEditingSummary] = useState<string | null>(null)
  const [editedSummaryText, setEditedSummaryText] = useState('')
  const [isUpdatingSummary, setIsUpdatingSummary] = useState(false)
  const advancedSettingsRef = useRef<HTMLDivElement>(null)
  const clickTimeoutRef = useRef<NodeJS.Timeout | null>(null)

  // Close advanced settings when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (advancedSettingsRef.current && !advancedSettingsRef.current.contains(event.target as Node)) {
        setShowAdvancedSettings(false)
      }
    }

    document.addEventListener("mousedown", handleClickOutside)
    return () => {
      document.removeEventListener("mousedown", handleClickOutside)
    }
  }, [advancedSettingsRef])

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

  // Fetch default topics from backend
  const fetchDefaultTopics = async () => {
    try {
      setIsLoadingTopics(true)
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const response = await fetch(`${apiUrl}/api/topics`, {
        // Disable cache to always get fresh data
        cache: 'no-cache',
        headers: {
          'Cache-Control': 'no-cache'
        }
      })
      
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

  useEffect(() => {
    fetchDefaultTopics()
    loadBookmarkStatus()
  }, [])

  const handleAddKeyword = () => {
    const trimmedKeyword = newKeyword.trim()
    const allTopics = [...defaultTopics, ...customTopics]
    
    if (!trimmedKeyword) {
      setKeywordMessage('Please enter a keyword')
      setTimeout(() => setKeywordMessage(''), 3000)
      return
    }
    
    if (allTopics.includes(trimmedKeyword)) {
      setKeywordMessage('This keyword already exists in your topics')
      setTimeout(() => setKeywordMessage(''), 3000)
      return
    }
    
    setCustomTopics([...customTopics, trimmedKeyword])
    setNewKeyword('')
    setKeywordMessage('Keyword added successfully!')
    setTimeout(() => setKeywordMessage(''), 2000)
  }

  const handleRemoveCustomTopic = (topicToRemove: string) => {
    setCustomTopics(customTopics.filter(topic => topic !== topicToRemove))
  }

  const handleBookmark = async (item: any) => {
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const isCurrentlyBookmarked = bookmarkedItems.has(item.link)
      
      if (isCurrentlyBookmarked) {
        // Remove bookmark
        const response = await fetch(`${apiUrl}/api/bookmarks?link=${encodeURIComponent(item.link)}`, {
          method: 'DELETE'
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
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const response = await fetch(`${apiUrl}/api/bookmarks`)
      
      if (response.ok) {
        const data = await response.json()
        const bookmarkedLinks = new Set<string>(data.items.map((bookmark: any) => String(bookmark.link)))
        setBookmarkedItems(bookmarkedLinks)
      }
    } catch (error) {
      console.error('Failed to load bookmark status:', error)
    }
  }

  // Pagination helper function
  const paginateItems = (items: any[], page: number) => {
    const filtered = items.filter(item => selectedTag ? item.source === selectedTag : true)
    const startIndex = (page - 1) * itemsPerPage
    return filtered.slice(startIndex, startIndex + itemsPerPage)
  }

  // Check bookmark status when results are loaded
  useEffect(() => {
    setPaginatedItems(paginateItems(fetchedItems, currentPage))
  }, [fetchedItems, selectedTag, currentPage, itemsPerPage, bookmarkedItems])

  useEffect(() => {
    setPaginatedBookmarks(paginateItems(bookmarkedCards, bookmarksPage))
  }, [bookmarkedCards, selectedTag, bookmarksPage, itemsPerPage])

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

  const refreshBookmarks = async () => {
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const response = await fetch(`${apiUrl}/api/bookmarks`)
      
      if (response.ok) {
        const data = await response.json()
        setBookmarkedCards(data.items)
      }
    } catch (error) {
      console.error('Failed to fetch bookmarks:', error)
    }
  }

  const handleViewBookmarks = async () => {
    // Toggle bookmarks view
    if (showBookmarks) {
      setShowBookmarks(false)
      setBookmarkedCards([])
      setExpandedSummaries(new Set()) // Clear expanded state when hiding bookmarks
      setSelectedTag(null) // Clear tag filter when hiding bookmarks
      setBookmarksPage(1) // Reset bookmarks page when hiding
      setUploadUrl('') // Clear URL
      setUploadMessage('') // Clear message
      return
    }

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const response = await fetch(`${apiUrl}/api/bookmarks`)
      
      if (response.ok) {
        const data = await response.json()
        setBookmarkedCards(data.items)
        setShowBookmarks(true)
        // Keep search results available - don't hide them
        setExpandedSummaries(new Set()) // Clear expanded state when switching views
        setSelectedTag(null) // Clear tag filter when switching to bookmarks
        setBookmarksPage(1) // Reset to first page when showing bookmarks
        setUploadUrl('') // Clear any previous URL
        setUploadMessage('') // Clear any previous message
      }
    } catch (error) {
      console.error('Failed to fetch bookmarks:', error)
    }
  }


  const confirmDelete = async () => {
    if (!deleteConfirmItem) return
    
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const response = await fetch(`${apiUrl}/api/bookmarks?link=${encodeURIComponent(deleteConfirmItem.link)}`, {
        method: 'DELETE'
      })
      
      if (response.ok) {
        // Remove from bookmark state
        setBookmarkedItems(prev => {
          const newSet = new Set(prev)
          newSet.delete(deleteConfirmItem.link)
          return newSet
        })
        // Refresh bookmarks view if currently shown
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
    if (!editedSummaryText.trim()) {
      return
    }

    setIsUpdatingSummary(true)
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const response = await fetch(`${apiUrl}/api/bookmarks/summary?link=${encodeURIComponent(link)}&summary=${encodeURIComponent(editedSummaryText)}`, {
        method: 'PUT'
      })

      if (response.ok) {
        // Refresh bookmarks to show updated summary
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
    if (!uploadUrl.trim()) {
      setUploadMessage('Please enter a valid URL')
      setTimeout(() => setUploadMessage(''), 3000)
      return
    }

    // Basic URL validation
    try {
      new URL(uploadUrl)
    } catch {
      setUploadMessage('Please enter a valid URL (starting with http:// or https://)')
      setTimeout(() => setUploadMessage(''), 3000)
      return
    }

    setIsUploading(true)
    setUploadProgress(0)
    setUploadProgressMessage('Starting to process your link...')
    setUploadMessage('Processing your link...')

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      
      // Simulate progress steps for user feedback
      setUploadProgress(25)
      setUploadProgressMessage('Fetching content from URL...')
      
      const response = await fetch(`${apiUrl}/api/upload-link`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          url: uploadUrl.trim()
        })
      })
      
      if (response.ok) {
        const result = await response.json()
        
        if (result.success) {
          setUploadProgress(75)
          setUploadProgressMessage('Generating summary and categorizing...')
          setUploadProgress(100)
          setUploadProgressMessage('Processing complete!')
          setUploadMessage('Link uploaded and processed successfully!')
          setUploadUrl('')
          // Refresh bookmarks to show the new item
          if (showBookmarks) {
            refreshBookmarks()
          }
        } else {
          // Handle cases where response is OK but success=false (like duplicate links)
          setUploadMessage(result.message || 'Failed to upload link')
          //setUploadProgress(100)
          setUploadProgressMessage('') // Don't show "Processing complete!"
        }
      } else {
        const errorData = await response.json()
        setUploadMessage(errorData.detail || 'Failed to upload link')
      }
    } catch (error) {
      console.error('Failed to upload link:', error)
      setUploadMessage('Failed to upload link. Please try again.')
    } finally {
      setTimeout(() => {
        setIsUploading(false)
        setUploadProgress(0)
        setUploadProgressMessage('')
        setUploadMessage('')
      }, 2000)
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
    setSelectedTag(selectedTag === tag ? null : tag) // Toggle tag selection
    setCurrentPage(1) // Reset to first page when filtering
    setBookmarksPage(1) // Reset bookmarks page too
  }

  const handleExportBookmarks = async () => {
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const response = await fetch(`${apiUrl}/api/bookmarks/export`, {
        method: 'GET'
      })

      if (response.ok) {
        // Get the filename from the response headers or create a default one
        const contentDisposition = response.headers.get('Content-Disposition')
        let filename = 'multimodal_scout_bookmarks.xlsx'
        
        if (contentDisposition) {
          const filenameMatch = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/)
          if (filenameMatch && filenameMatch[1]) {
            filename = filenameMatch[1].replace(/['"]/g, '')
          }
        }

        // Convert response to blob and download
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
    
    if (totalPages <= 1) {
      return null
    }
    
    
    return (
      <div className="flex justify-center items-center gap-2 mt-6 p-4 bg-gray-100 rounded-lg">
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
        setShowDetailedProgress(true)
        setProgressMessage(eventData.message)
        setProgress(0)
        break
      case 'progress':
        const progressPercent = Math.round((eventData.processed / eventData.total) * 100)
        setProgress(progressPercent)
        setProgressMessage(eventData.message)
        break
      case 'complete':
        setProgress(100)
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
        setSelectedTag(null)
        setCurrentPage(1)
        setProgress(100)
        setProgressMessage('Complete!')
        // Load bookmark status for the new search results
        loadBookmarkStatus()
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
    setProgress(0)
    setProgressMessage('Starting fetch...')
    setShowDetailedProgress(false)
    
    try {
      const allTopics = [...defaultTopics, ...customTopics]
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      
      const response = await fetch(`${apiUrl}/api/fetch-stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ selectedDays, topics: allTopics, maxResults, researchRatio })
      })
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const reader = response.body?.getReader()
      if (!reader) {
        throw new Error('Failed to get response reader')
      }

      await processStreamData(reader)
      
    } catch (error) {
      console.error('Failed to fetch items:', error)
      alert('Failed to fetch items. Please check if the backend server is running.')
      setProgressMessage('Failed to fetch items')
    } finally {
      setTimeout(() => {
        setIsLoading(false)
        setProgress(0)
        setProgressMessage('')
        setShowDetailedProgress(false)
      }, 2000)
    }
  }

  return (
    <main className="min-h-screen bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="text-center mb-12">
          <h1 className="text-5xl font-bold text-gray-900 mb-4">
            Multimodal Scout
          </h1>
          <p className="text-xl text-gray-600">
            Find top stories and papers related to multimodal AI and AI agents.
          </p>
        </div>

        {/* Interest Topics Section */}
        <div className="bg-orange-100 rounded-lg p-8 mb-12">
          <div className="mb-6">
            <h2 className="text-2xl font-bold text-gray-800">My Interested Topics</h2>
          </div>
          
          {isLoadingTopics ? (
            <div className="flex justify-center items-center py-4">
              <div className="text-gray-700">Loading topics...</div>
            </div>
          ) : (
            <div className="flex flex-wrap gap-3 mb-6">
              {/* Default Topics (Read-only) */}
              {defaultTopics.map((topic, index) => (
                <span
                  key={`default-${index}`}
                  className="inline-flex items-center px-4 py-2 bg-white rounded-full text-gray-800 border border-gray-200"
                >
                  {topic}
                  <span className="ml-3 text-gray-400 text-sm">🔒</span>
                </span>
              ))}
              
              {/* Custom Topics (Removable) */}
              {customTopics.map((topic, index) => (
                <span
                  key={`custom-${index}`}
                  className="inline-flex items-center px-4 py-2 bg-white rounded-full text-gray-800 border border-gray-200"
                >
                  {topic}
                  <button
                    onClick={() => handleRemoveCustomTopic(topic)}
                    className="ml-3 w-5 h-5 rounded-full flex items-center justify-center hover:bg-red-500 focus:outline-none transition-colors text-sm font-bold"
                    title="Remove keyword"
                  >
                    ×
                  </button>
                </span>
              ))}
            </div>
          )}
          
          {/* Add Keywords Input */}
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
                className="w-14 h-14 text-gray-700 rounded-full hover:bg-orange-200 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2 font-medium flex items-center justify-center transition-colors"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
              </button>
            </div>
          </div>

          {/* Settings and Bookmarks Icons */}
          <div className="flex justify-between items-center mt-6">
            <div className="flex items-center gap-4">
              <button
                onClick={handleGearClick}
                disabled={isLoading}
                className={`bg-gray-100 p-3 text-gray-700 hover:text-gray-900 hover:bg-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-500 transition-colors flex items-center justify-center ${  
                  isLoading ? 'cursor-not-allowed opacity-50' : ''
                }`}
                title="Advanced Search Settings (double-click to close)"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
              </button>
              <button
                onClick={handleViewBookmarks}
                className="bg-gray-100 p-3 text-gray-700 hover:text-gray-900 hover:bg-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-500 transition-colors flex items-center justify-center"
                title="My Bookmarks"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z" />
                </svg>
              </button>
              <ThemeToggle />
            </div>

            <button
              onClick={handleFetchItems}
              disabled={isLoading}
              className={`px-8 py-3 text-white rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2 font-medium transition-colors ${
                isLoading
                  ? 'bg-gray-500 hover:bg-gray-600 cursor-not-allowed'
                  : 'bg-gray-500 hover:bg-gray-600'
              }`}
            >
              {isLoading ? 'Searching...' : 'Search'}
            </button>
          </div>
        </div>

        {/* Advanced Settings Panel */}
        {!showBookmarks && showAdvancedSettings && (
          <div className="rounded-lg p-6 mb-8">
            {/* Time Range Selector */}
          <div className="mb-6">
            <div className="flex items-center justify-center space-x-4">
              <span className="text-gray-700 font-medium">Retrieve content from the last</span>
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
                <strong>Smart Balanced Search:</strong> Prioritizes keyword matches first, then adds semantic matches by relevance score. Research papers use a higher similarity threshold to ensure quality, while industry content uses a lower threshold for variety.
              </div>
            </div>
          </div>
        </div>
        )}

        {/* Keyword feedback message */}
        {keywordMessage && (
          <div className={`mt-3 text-center text-sm font-medium ${
            keywordMessage.includes('successfully') 
              ? 'text-green-600' 
              : keywordMessage.includes('already exists') || keywordMessage.includes('Please enter')
              ? 'text-red-600' 
              : 'text-gray-600'
          }`}>
            {keywordMessage}
          </div>
        )}

        {/* Progress Message - Hide when viewing bookmarks */}
        {!showBookmarks && isLoading && progressMessage && (
          <div className="mt-6 text-center">
            <div className="inline-flex items-center px-4 py-2 text-blue-800 rounded-lg">
              <div className="animate-spin w-4 h-4 border-2 border-blue-600 border-t-transparent rounded-full mr-3"></div>
              <span className="text-sm font-medium">{progressMessage}</span>
            </div>
            {showDetailedProgress && (
              <div className="mt-2 text-xs text-gray-600">
                Summary generation can take 30-60 seconds per article. Thank you for your patience!
              </div>
            )}
          </div>
        )}

        {/* Results Section */}
        {showResults && fetchedItems.length > 0 && !showBookmarks && (
          <div className="mt-12">
            <div className="flex justify-between items-center mb-6">
              <div className="flex items-center gap-3">
                <div className="text-sm text-gray-600">
                  {selectedTag 
                    ? `${fetchedItems.filter(item => item.source === selectedTag).length} results for "${selectedTag}"` 
                    : `${fetchedItems.length} results`
                  }
                </div>
                {selectedTag && (
                  <div className="inline-flex items-center gap-1 px-3 py-1 bg-blue-100 text-blue-800 text-xs rounded-full">
                    <span>{selectedTag}</span>
                    <button
                      onClick={() => setSelectedTag(null)}
                      className="ml-2 w-4 h-4 bg-blue-200 hover:bg-red-200 rounded-full flex items-center justify-center text-blue-600 hover:text-red-600 focus:outline-none transition-colors text-xs font-bold"
                      title="Clear filter"
                    >
                      ×
                    </button>
                  </div>
                )}
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
                    <button
                      onClick={() => handleTagFilter(item.source)}
                      className={`inline-block px-3 py-1 text-xs font-medium rounded-full transition-colors hover:opacity-80 focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                        selectedTag === item.source
                          ? 'bg-blue-100 text-blue-800 ring-2 ring-blue-300'
                          : 'bg-gray-300 text-gray-800 hover:bg-gray-400'
                      }`}
                      title={`Filter by ${item.source}`}
                    >
                      {item.source}
                    </button>
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
                  {item.summary && item.summary !== "No summary available" && item.summary.trim() !== "" ? (
                    <div className="mb-4">
                      <div className="text-gray-700 text-sm leading-relaxed">
                        {expandedSummaries.has(item.link) ? (
                          // Full summary
                          <div>
                            <p>{item.summary}</p>
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
                            <p 
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
                              {item.summary}
                            </p>
                            {showReadMore.has(item.link) && (
                              <button
                                onClick={() => toggleSummaryExpansion(item.link)}
                                className="mt-2 text-blue-600 hover:text-blue-800 text-xs font-medium rounded focus:outline-none"
                              >
                                Read more ↓
                              </button>
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                  ) : (
                    // Debug: Show when no summary is available
                    <div className="mb-4 text-xs text-gray-400 italic">
                      {item.summary ? `Summary: "${item.summary.substring(0, 50)}..."` : 'No summary available'}
                    </div>
                  )}
                  
                  <div className="flex justify-end">
                    <a
                      href={item.link}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center px-4 py-2 bg-gray-500 text-white text-sm font-medium rounded-lg hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-gray-500 transition-colors"
                    >
                      Read the original post →
                    </a>
                  </div>
                </div>
                )
              })}
            </div>
            
            {/* Pagination for Results */}
            <PaginationControls
              currentPage={currentPage}
              setCurrentPage={setCurrentPage}
              totalItems={fetchedItems.filter(item => selectedTag ? item.source === selectedTag : true).length}
              itemsPerPage={itemsPerPage}
            />
          </div>
        )}

        {/* Bookmarks Section */}
        {showBookmarks && (
          <div className="mt-4">
            {selectedTag && (
              <div className="mb-6">
                <div className="inline-flex items-center gap-1 px-3 py-1 bg-blue-100 text-blue-800 text-xs rounded-full">
                  <span>{selectedTag}</span>
                  <button
                    onClick={() => setSelectedTag(null)}
                    className="ml-2 w-4 h-4 bg-blue-200 hover:bg-red-200 rounded-full flex items-center justify-center text-blue-600 hover:text-red-600 focus:outline-none transition-colors text-xs font-bold"
                    title="Clear filter"
                  >
                    ×
                  </button>
                </div>
              </div>
            )}
            
            {/* Upload Link Section */}
            <div className="mb-4">
              <div className="rounded-lg p-6 border border-blue-200">
                <div className="space-y-2">
                  <div className="flex gap-3">
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
                      className={`px-4 py-2 text-white text-sm font-medium rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-500 transition-all duration-200 ${
                        isUploading
                          ? 'bg-gray-300 cursor-not-allowed opacity-50'
                          : 'bg-gray-500 hover:bg-gray-600 shadow-lg hover:shadow-xl hover:scale-105'
                      }`}
                    >
                      {isUploading ? (
                        <div className="flex items-center justify-center gap-2">
                          <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                          Processing...
                        </div>
                      ) : (
                        'Add'
                      )}
                    </button>
                  </div>
                  {/* Upload Progress Bar */}
                  {isUploading && (
                    <div className="space-y-3">
                      <div className="w-full rounded-full h-2">
                        <div 
                          className="h-2 rounded-full transition-all duration-500 ease-out"
                          style={{ width: `${uploadProgress}%` }}
                        ></div>
                      </div>
                      <div className="text-sm text-blue-700 text-center font-medium">
                        {uploadProgressMessage}{uploadProgressMessage && ` (${uploadProgress}%)`}
                      </div>
                    </div>
                  )}
                  
                  {uploadMessage && (
                    <div className={`text-sm font-medium p-3 rounded-lg ${
                      uploadMessage.includes('successfully')
                        ? 'text-green-700 border border-green-200'
                        : uploadMessage.includes('Processing')
                        ? 'text-blue-700 border border-blue-200'
                        : uploadMessage.includes('already been added !') || uploadMessage.includes('already bookmarked !')
                        ? 'text-orange-700 border border-orange-200'
                        : 'text-red-700 border border-red-200'
                    }`}>
                      {uploadMessage}
                    </div>
                  )}
                </div>
                <div className="mt-6 text-xs text-gray-600 p-3 rounded">
                  <div className="flex items-start gap-2">
                    <span className="flex-shrink-0">💡</span>
                    <div>
                      <strong>Smart Processing:</strong> Upload your own link and we'll automatically scrape the content, generate a summary, and categorize it as Research, Industry, or General based on the content type.
                    </div>
                  </div>
                </div>
              </div>
            </div>
            
            {/* Bookmark Count - moved below upload section */}
            <div className="flex justify-between items-center mb-6">
              <div className="text-sm text-gray-600">
                {selectedTag 
                  ? `${bookmarkedCards.filter(item => item.source === selectedTag).length} bookmarks for "${selectedTag}"` 
                  : `${bookmarkedCards.length} bookmarks`
                }
              </div>
              <button
                onClick={handleExportBookmarks}
                className="w-6 h-6 flex items-center justify-center text-gray-500 hover:text-green-600 rounded-full hover:bg-green-50 focus:outline-none transition-colors"
                title="Export bookmarks to Excel"
              >
                📊
              </button>
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
                      <button
                        onClick={() => handleTagFilter(item.source)}
                        className={`inline-block px-3 py-1 text-xs font-medium rounded-full transition-colors hover:opacity-80 focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                          selectedTag === item.source
                            ? 'bg-blue-100 text-blue-800 ring-2 ring-blue-300'
                            : 'bg-gray-300 text-gray-800 hover:bg-gray-400'
                        }`}
                        title={`Filter by ${item.source}`}
                      >
                        {item.source}
                      </button>
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
                        title="Remove bookmark"
                      >
                        ★
                      </button>
                    </div>
                    
                    <h3 className="text-xl font-semibold text-gray-900 mb-4 leading-tight">
                      {item.title}
                    </h3>
                    
                    {/* Summary Section for Bookmarks */}
                    {item.summary && item.summary !== "No summary available" && item.summary.trim() !== "" && (
                      <div className="mb-4">
                        <div className="flex items-start justify-between mb-2">
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-medium text-gray-600">Summary</span>
                            {item.summary_edited && (
                              <span className="text-xs px-2 py-1 bg-blue-100 text-blue-700 rounded-full">
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
                              title="Edit summary"
                              className="text-xs text-gray-400 hover:text-gray-600 cursor-pointer focus:outline-none hover:bg-gray-600 rounded-full p-1"
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
                              className="w-full p-4 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm leading-relaxed text-left resize-none"
                              style={{ textAlign: 'left', lineHeight: '1.6' }}
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
                                <p>{item.summary}</p>
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
                                <p 
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
                                  {item.summary}
                                </p>
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
                  totalItems={bookmarkedCards.filter(item => selectedTag ? item.source === selectedTag : true).length}
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
      </div>
    </main>
  )
}