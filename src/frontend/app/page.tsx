'use client'

import { useState, useEffect } from 'react'

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

  // Check bookmark status when results are loaded
  useEffect(() => {
    const checkBookmarks = async () => {
      if (fetchedItems.length === 0) return
      
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
        const bookmarkChecks = await Promise.all(
          fetchedItems.map(async (item) => {
            const response = await fetch(`${apiUrl}/api/bookmarks/check?link=${encodeURIComponent(item.link)}`)
            const data = await response.json()
            return { link: item.link, isBookmarked: data.is_bookmarked }
          })
        )
        
        const bookmarkedLinks = bookmarkChecks
          .filter(check => check.isBookmarked)
          .map(check => check.link)
        
        setBookmarkedItems(new Set(bookmarkedLinks))
      } catch (error) {
        console.error('Failed to check bookmarks:', error)
      }
    }
    
    checkBookmarks()
  }, [fetchedItems])

  const handleViewBookmarks = async () => {
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const response = await fetch(`${apiUrl}/api/bookmarks`)
      
      if (response.ok) {
        const data = await response.json()
        setBookmarkedCards(data.items)
        setShowBookmarks(true)
        setShowResults(false) // Hide search results when showing bookmarks
        setExpandedSummaries(new Set()) // Clear expanded state when switching views
      }
    } catch (error) {
      console.error('Failed to fetch bookmarks:', error)
    }
  }

  const handleHideBookmarks = () => {
    setShowBookmarks(false)
    setBookmarkedCards([])
    setExpandedSummaries(new Set()) // Clear expanded state when hiding bookmarks
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

  const handleFetchItems = async () => {
    setIsLoading(true)
    setProgress(0)
    setProgressMessage('Starting fetch...')
    setShowDetailedProgress(false)
    
    try {
      const allTopics = [...defaultTopics, ...customTopics]
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      
      const response = await fetch(`${apiUrl}/api/fetch-stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          selectedDays,
          topics: allTopics
        })
      })
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const reader = response.body?.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      
      if (!reader) {
        throw new Error('Failed to get response reader')
      }

      while (true) {
        const { done, value } = await reader.read()
        
        if (done) break
        
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || '' // Keep incomplete line in buffer
        
        for (const line of lines) {
          if (line.startsWith('data: ') && line !== 'data: [DONE]') {
            try {
              const eventData = JSON.parse(line.slice(6)) // Remove 'data: '
              
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
                  console.log('Successfully fetched items:', eventData.data)
                  setFetchedItems(eventData.data.items)
                  setShowResults(true)
                  setShowBookmarks(false) // Hide bookmarks when showing fresh search results
                  setExpandedSummaries(new Set()) // Clear expanded state for new results
                  setProgress(100)
                  setProgressMessage('Complete!')
                  break
              }
            } catch (parseError) {
              console.error('Failed to parse event data:', parseError)
            }
          } else if (line === 'data: [DONE]') {
            break
          }
        }
      }
      
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
      }, 2000) // Show completion message for 2 seconds
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

        {/* Time Range Selector */}
        <div className="flex items-center justify-center mb-12 space-x-4">
          <span className="text-gray-700 text-lg italic">Retrieve content from the last</span>
          <input
            type="number"
            value={selectedDays}
            onChange={(e) => setSelectedDays(Number(e.target.value))}
            className="w-16 px-3 py-2 border border-gray-300 rounded-md text-center focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent"
            min="1"
          />
          <span className="text-gray-700 text-lg">days</span>
          <div className="flex space-x-2">
            {[1, 3, 7].map((days) => (
              <button
                key={days}
                onClick={() => setSelectedDays(days)}
                className={`w-10 h-10 rounded-full font-medium transition-colors ${
                  selectedDays === days
                    ? 'bg-green-600 text-white'
                    : 'bg-gray-300 text-gray-700 hover:bg-gray-400'
                }`}
              >
                {days}
              </button>
            ))}
          </div>
        </div>

        {/* Interest Topics Section */}
        <div className="bg-orange-100 rounded-lg p-8 mb-12">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-2xl font-bold text-gray-800">My Interested Topics</h2>
            <button
              onClick={fetchDefaultTopics}
              disabled={isLoadingTopics}
              className="w-8 h-8 flex items-center justify-center text-gray-700 hover:text-gray-900 hover:bg-white rounded-full focus:outline-none disabled:opacity-50 transition-colors"
              title="Refresh topics"
            >
              {isLoadingTopics ? '⟳' : '↻'}
            </button>
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
                  className="inline-flex items-center px-4 py-2 bg-green-600 rounded-full text-white"
                >
                  {topic}
                  <button
                    onClick={() => handleRemoveCustomTopic(topic)}
                    className="ml-3 w-5 h-5 bg-white bg-opacity-20 rounded-full flex items-center justify-center text-white hover:bg-red-500 hover:bg-opacity-100 focus:outline-none transition-colors text-sm font-bold"
                  >
                    ×
                  </button>
                </span>
              ))}
            </div>
          )}
          
          {/* Add Keywords Input */}
          <div className="flex gap-4">
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
              className="px-8 py-3 bg-gray-500 text-white rounded-lg hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2 font-medium"
            >
              Add
            </button>
          </div>
          
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
        </div>

        {/* Action Buttons */}
        <div className="flex justify-center gap-6">
          <button
            onClick={handleFetchItems}
            disabled={isLoading}
            className={`relative px-8 py-4 text-white text-xl font-semibold rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2 transition-colors overflow-hidden ${
              isLoading 
                ? 'bg-gray-500 cursor-not-allowed' 
                : 'bg-green-600 hover:bg-green-700'
            }`}
          >
            {/* Progress Bar Background inside button */}
            {isLoading && (
              <div 
                className="absolute top-0 left-0 h-full bg-green-700 transition-all duration-300 ease-out"
                style={{ width: `${progress}%` }}
              />
            )}
            
            {/* Button Text */}
            <span className="relative z-10">
              {isLoading ? (showDetailedProgress ? `${progress}%` : 'Fetching...') : '🔍 Fetch Top Items'}
            </span>
          </button>
          
          <button
            onClick={handleViewBookmarks}
            className="px-8 py-4 bg-gray-500 text-white text-xl font-semibold rounded-lg hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2 transition-colors"
          >
            📚 View My Bookmarks
          </button>
        </div>

        {/* Progress Message */}
        {isLoading && progressMessage && (
          <div className="mt-6 text-center">
            <div className="inline-flex items-center px-4 py-2 bg-blue-100 text-blue-800 rounded-lg">
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
        {showResults && fetchedItems.length > 0 && (
          <div className="mt-12">
            <div className="flex justify-between items-center mb-6">
              <div className="text-sm text-gray-600">
                {fetchedItems.length} results
              </div>
              <button
                onClick={() => setShowResults(false)}
                className="w-6 h-6 flex items-center justify-center text-gray-500 hover:text-gray-700 rounded-full hover:bg-gray-200 focus:outline-none transition-colors"
                title="Hide results"
              >
                ×
              </button>
            </div>
            
            <div className="space-y-4">
              {fetchedItems
                .sort((a, b) => {
                  const aBookmarked = bookmarkedItems.has(a.link)
                  const bBookmarked = bookmarkedItems.has(b.link)
                  // Show non-bookmarked items first, bookmarked items last
                  if (aBookmarked && !bBookmarked) return 1
                  if (!aBookmarked && bBookmarked) return -1
                  return 0
                })
                .map((item, index) => (
                <div
                  key={index}
                  className="bg-white rounded-lg p-6 border border-gray-200 hover:shadow-lg transition-all duration-300"
                >
                  <div className="flex items-start justify-between mb-4">
                    <span className="inline-block px-3 py-1 bg-gray-300 text-gray-800 text-xs font-medium rounded-full">
                      {item.source}
                    </span>
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
                            <p>
                              {item.summary.length > 200 
                                ? `${item.summary.substring(0, 200)}...` 
                                : item.summary
                              }
                            </p>
                            {item.summary.length > 200 && (
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
              ))}
            </div>
          </div>
        )}

        {/* Bookmarks Section */}
        {showBookmarks && (
          <div className="mt-12">
            <div className="flex justify-between items-center mb-6">
              <div className="text-sm text-gray-600">
                {bookmarkedCards.length} bookmarks
              </div>
              <button
                onClick={handleHideBookmarks}
                className="w-6 h-6 flex items-center justify-center text-gray-500 hover:text-gray-700 rounded-full hover:bg-gray-200 focus:outline-none transition-colors"
                title="Hide bookmarks"
              >
                ×
              </button>
            </div>
            
            {bookmarkedCards.length === 0 ? (
              <div className="text-center py-12">
                <div className="text-gray-600 text-lg mb-2">📚</div>
                <div className="text-gray-600">No bookmarks yet</div>
                <div className="text-gray-500 text-sm mt-1">
                  Start bookmarking articles by clicking the ☆ icon
                </div>
              </div>
            ) : (
              <div className="space-y-4">
                {bookmarkedCards.map((item, index) => (
                  <div
                    key={index}
                    className="bg-white rounded-lg p-6 border border-gray-200 hover:shadow-lg transition-all duration-300"
                  >
                    <div className="flex items-start justify-between mb-4">
                      <span className="inline-block px-3 py-1 bg-gray-300 text-gray-800 text-xs font-medium rounded-full">
                        {item.source}
                      </span>
                      <div className="flex items-center gap-2">
                        <span className="text-yellow-600">★</span>
                        <button
                          onClick={() => handleBookmark(item)}
                          className="w-6 h-6 flex items-center justify-center text-gray-500 hover:text-red-500 rounded-full focus:outline-none transition-colors"
                          title="Remove bookmark"
                        >
                          ×
                        </button>
                      </div>
                    </div>
                    
                    <h3 className="text-xl font-semibold text-gray-900 mb-4 leading-tight">
                      {item.title}
                    </h3>
                    
                    {/* Summary Section for Bookmarks */}
                    {item.summary && item.summary !== "No summary available" && item.summary.trim() !== "" && (
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
                              <p>
                                {item.summary.length > 200 
                                  ? `${item.summary.substring(0, 200)}...` 
                                  : item.summary
                                }
                              </p>
                              {item.summary.length > 200 && (
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
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </main>
  )
}