# Hacker News Comment Insights Feature

## Overview

This feature automatically generates AI-powered insights from Hacker News discussions and displays them to registered users in a two-section format.

## Architecture

### Content Enrichment Pipeline
- **Location**: `src/backend/merger.py` - `enrich_hackernews_comments()`
- **Trigger**: During cron jobs via `enrich_sources_with_summaries_and_embeddings()`
- **Smart Updates**: Only regenerates insights when ≥10 new comments since last update
- **5-Minute TTL Cache**: Prevents unnecessary HN API calls for recently processed sources
- **Batch Processing**: Parallel processing with controlled concurrency (max 5 workers)
- **Rate Limiting**: No artificial delays (HN API has no rate limits)

### Database Storage
- **Table**: `comment_insights` (already existed)
- **Fields**: `source_id`, `link`, `title`, `comment_count`, `insights`, `generated_at`
- **Methods**: `save_comment_insights()` (batch), `get_comment_insights()` (batch)
- **Optimization**: All database operations use batch processing to reduce transactions

### API Response Schema
- **Schema**: `ItemResponse` in `src/backend/schema.py`
- **New Fields**: `comment_insights: Optional[str]`, `comment_count: Optional[int]`
- **Backwards Compatible**: Optional fields with `None` defaults

## User Experience

### Registered Users
- See enhanced HN posts with two-section summaries:
  ```
  **Content Summary:**
  [Original article summary]
  
  **Community Discussion (X comments):**
  [AI-generated community insights]
  ```

### Guest Users  
- See standard single-section summaries only
- Comment insights are hidden to incentivize registration

### Bookmarks
- Always show comment insights (require authentication)
- Same two-section format as search results

## Technical Implementation

### Caching System
- **Location**: `src/backend/utils.py` - module-level cache functions
- **TTL**: 5 minutes (300 seconds) for comment insight processing
- **Functions**: `is_comment_insight_recently_processed()`, `mark_comment_insight_as_processed()`
- **Purpose**: Prevents redundant HN API calls during the 5-minute window
- **Cache Cleanup**: Automatically removes expired entries to prevent memory leaks

### Batch Processing
- **Database Operations**: All comment insight queries use batch processing
- **Parallel Processing**: ThreadPoolExecutor with max 5 workers for HN API calls
- **Batch Saving**: Multiple insights saved in single database transaction
- **Performance**: Reduces database overhead and improves processing speed

### Endpoints Modified
1. **Search Pipeline** (`src/backend/utils.py:528-589`)
   - `get_hn_comment_insights_with_summaries()` function for batch processing
   - Conditionally shows insights based on `user_id`
   - Creates combined two-section summary for registered users

2. **Bookmarks** (via `get_hn_comment_insights_with_summaries()`)
   - Always shows insights (authentication required)
   - Preserves user-edited summaries in content section

### Smart Update Logic
- **Minimum Threshold**: 10 comments required (`MIN_COMMENTS_FOR_INSIGHTS`)
- **Update Trigger**: Only when ≥10 new comments since last processing
- **5-Minute Cache**: Prevents reprocessing the same source within 5 minutes
- **Prevents**: Unnecessary API calls and redundant processing

## Testing Results

### Automated Tests
- ✅ All 20 existing tests pass
- ✅ No regressions introduced
- ✅ Schema validation works correctly
- ✅ Backwards compatibility maintained

### Manual Testing
- ✅ HN comment fetching works with real posts
- ✅ AI insight generation produces quality output  
- ✅ Two-section display format renders correctly
- ✅ User access controls work as expected
- ✅ Non-HN sources are ignored correctly
- ✅ Smart update logic prevents unnecessary calls

### Integration Testing
- ✅ Enrichment pipeline processes HN sources during cron jobs
- ✅ API responses include comment fields for registered users
- ✅ Guest users see standard responses without insights
- ✅ Bookmarks endpoint shows insights for authenticated users

## Performance Characteristics

- **Cron Jobs**: Process all HN sources, generate insights for posts with ≥10 comments
- **API Responses**: Fast database lookups, no real-time AI generation
- **5-Minute Rolling Cache**: Prevents redundant processing of recently updated sources
- **Batch Database Operations**: Efficient bulk queries and inserts reduce transaction overhead
- **Parallel Processing**: Up to 5 concurrent HN API requests with controlled concurrency
- **Smart Caching**: Only updates when meaningful new discussion appears (≥10 new comments)
- **No Rate Limiting**: Efficient processing without artificial delays

## Cache Behavior

### Module-Level Caching
- **Implementation**: Simple in-memory dictionary with timestamp tracking
- **TTL Management**: 5-minute rolling window, automatic cleanup of expired entries
- **Thread Safety**: Module-level cache shared across all requests
- **Memory Efficient**: Only stores link and timestamp, not the actual insights

### Cache Integration
- **Pipeline Integration**: Cache checked before processing HN sources
- **Cache Hits Logging**: Tracks and logs cache optimization statistics
- **Consistent Pattern**: Follows same caching approach as content summaries
- **Performance Gain**: Significantly reduces HN API calls during active periods

## Future Enhancements

- Could extend to other discussion platforms (Reddit, etc.)
- Could add insight quality scoring and filtering
- Could implement user feedback on insight relevance
- Could add insight categories (technical, business, etc.)