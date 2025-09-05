# Hacker News Comment Insights Feature

## Overview

This feature automatically generates AI-powered insights from Hacker News discussions and displays them to registered users in a two-section format.

## Architecture

### Content Enrichment Pipeline
- **Location**: `src/backend/merger.py` - `enrich_hackernews_comments()`
- **Trigger**: During cron jobs via `enrich_sources_with_summaries_and_embeddings()`
- **Smart Updates**: Only regenerates insights when ≥10 new comments since last update
- **Rate Limiting**: No artificial delays (HN API has no rate limits)

### Database Storage
- **Table**: `comment_insights` (already existed)
- **Fields**: `source_id`, `link`, `title`, `comment_count`, `insights`, `generated_at`
- **Methods**: `save_comment_insight()`, `get_comment_insights()`

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

### Endpoints Modified
1. **Search Pipeline** (`src/backend/pipeline.py:510-522`)
   - Conditionally shows insights based on `user_id`
   - Creates combined two-section summary for registered users

2. **Bookmarks** (`src/backend/app.py:696-708`) 
   - Always shows insights (authentication required)
   - Preserves user-edited summaries in content section

### Smart Update Logic
- **Minimum Threshold**: 10 comments required (`MIN_COMMENTS_FOR_INSIGHTS`)
- **Update Trigger**: Only when ≥10 new comments since last processing
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
- **Smart Caching**: Only updates when meaningful new discussion appears
- **No Rate Limiting**: Efficient processing without artificial delays

## Future Enhancements

- Could extend to other discussion platforms (Reddit, etc.)
- Could add insight quality scoring and filtering
- Could implement user feedback on insight relevance
- Could add insight categories (technical, business, etc.)