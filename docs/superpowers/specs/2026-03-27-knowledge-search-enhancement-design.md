# Knowledge Search Enhancement Design

**Date**: 2026-03-27  
**Status**: Approved  
**Author**: AI Assistant  

## Overview

This design document outlines the enhancement of search functionality for the Knowledge Base Web UI. The goal is to add search inputs to the Note and File pages, matching the existing search capability already present on Bookmark, Webpage, and Email pages.

## Requirements

1. **Note Page**: Add search functionality supporting content and tag filtering
2. **File Page**: Add search functionality supporting title, summary, and tag filtering
3. **Verify Existing Pages**: Confirm Bookmark/WebPage/Email search covers tags, title, summary, or content

## Current State Analysis

### Page Search Capabilities

| Page | Has Search Input | Search Fields | Tag Filter |
|------|-----------------|---------------|------------|
| Bookmark | Yes | title, source, summary | Yes |
| Webpage | Yes | title, source, summary | Yes |
| Email | Yes | title, source, summary | Yes |
| File | No | N/A | Yes |
| Note | No | N/A | Yes |

### Backend Search Implementation

The `/api/items` endpoint supports:
- `search` parameter: Searches in **title, source, summary** (LIKE pattern matching)
- `tag` parameter: Filters by tag name
- `content_type` parameter: Filters by type

The search is implemented in `sqlite_storage.py` using SQL LIKE queries:
```python
if search:
    search_pattern = f"%{search}%"
    where_conditions.append("(k.title LIKE ? OR k.source LIKE ? OR k.summary LIKE ?)")
    params.extend([search_pattern, search_pattern, search_pattern])
```

## Design Decision

### Selected Approach: Minimal Change (Approach 1)

Add search inputs to Note and File pages only, following the exact same pattern as Webpage.

**Rationale**:
- Minimal code changes (~20 lines)
- Consistent UX across all content type pages
- Uses existing backend API (`/api/items?search=...`)
- Fast to implement
- Low risk

## Implementation Details

### 1. Note Page Changes

**Location**: `kb/web/static/index.html`, around line 2157 (after page-header, before tag-filter-bar)

**Addition**:
```html
<!-- Search and Filter -->
<div style="display: flex; gap: 12px; margin-bottom: 20px; flex-wrap: wrap;">
    <input type="text" class="search-input" style="flex: 1; min-width: 200px;" 
           v-model="itemsFilter.search" :placeholder="t('note.searchPlaceholder')" @keyup.enter="fetchItems">
    <button class="btn btn-secondary" @click="fetchItems">{{ t('nav.search') }}</button>
</div>
```

**i18n Addition**:
```javascript
note: {
    // ... existing translations
    searchPlaceholder: 'Search notes...'
}
```

**Search Scope**: title, source, summary (via existing backend)

### 2. File Page Changes

**Location**: `kb/web/static/index.html`, around line 2498 (after page-header, before tag-filter-bar)

**Addition**:
```html
<!-- Search and Filter -->
<div style="display: flex; gap: 12px; margin-bottom: 20px; flex-wrap: wrap;">
    <input type="text" class="search-input" style="flex: 1; min-width: 200px;" 
           v-model="itemsFilter.search" :placeholder="t('file.searchPlaceholder')" @keyup.enter="fetchItems">
    <button class="btn btn-secondary" @click="fetchItems">{{ t('nav.search') }}</button>
</div>
```

**i18n Addition**:
```javascript
file: {
    // ... existing translations
    searchPlaceholder: 'Search files...'
}
```

**Search Scope**: title, source, summary (via existing backend)

### 3. Verification of Existing Pages

**Bookmark Page** (line ~2219):
- Has search input: Yes
- Search placeholder: "Search bookmarks..."
- Searches in: title, source, summary
- Tag filter: Yes
- **Status**: Complete

**Webpage Page** (line ~2309):
- Has search input: Yes
- Search placeholder: "Search title or content..."
- Searches in: title, source, summary
- Tag filter: Yes
- **Status**: Complete

**Email Page** (line ~2405):
- Has search input: Yes
- Search placeholder: "Search emails..."
- Searches in: title, source, summary
- Tag filter: Yes
- **Status**: Complete

## Files to Modify

1. `kb/web/static/index.html` - Add search inputs to Note and File pages, add i18n translations

## No Backend Changes Required

The existing `/api/items` endpoint already supports the search parameter. No backend modifications are needed.

## Testing Checklist

- [ ] Note page displays search input
- [ ] Note search filters results by title/source/summary
- [ ] Note search works with tag filters combined
- [ ] File page displays search input
- [ ] File search filters results by title/source/summary
- [ ] File search works with tag filters combined
- [ ] Bookmark search still works (regression test)
- [ ] Webpage search still works (regression test)
- [ ] Email search still works (regression test)

## Future Considerations

If full-content search is needed in the future, consider:
1. Adding content to the FTS5 virtual table in SQLite
2. Creating a new endpoint `/api/items/search-content` that reads file contents
3. Implementing client-side search for smaller datasets

## References

- Existing Webpage search implementation: `kb/web/static/index.html` line ~2309
- Backend search API: `kb/web/routes/items.py` line ~34-79
- Storage search method: `kb/storage/sqlite_storage.py` line ~270-345
