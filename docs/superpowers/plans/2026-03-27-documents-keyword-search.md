# Documents Keyword Search Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a keyword search input to the "Knowledge Collected" (Documents) page that searches through title, source, and summary fields.

**Architecture:** The backend already supports search via `/api/items?search=keyword` parameter. This implementation only requires frontend changes: adding a search input to the Documents page filter controls, binding it to the existing `itemsFilter.search` property, and triggering `fetchItems()` on user input.

**Tech Stack:** Vue.js 3 (Options API), vanilla JavaScript, existing i18n translation system

---

## File Structure

| File | Action | Purpose |
|------|--------|---------|
| `/Users/xudonglai/AliDrive/Work/agentic-second-brain/kb/web/static/index.html` | Modify | Add search input to Documents page filter controls, add translations |

---

## Prerequisites

- [ ] Ensure the web server is not running (to avoid file lock issues)
- [ ] Verify the current page structure by viewing the Documents page HTML section

---

## Task 1: Add Search Input to Documents Page Filter Controls

**Files:**
- Modify: `/Users/xudonglai/AliDrive/Work/agentic-second-brain/kb/web/static/index.html:~2330` (tag-filter-controls section in Documents page)

**Context:** The Documents page has a filter controls section with a type dropdown. We need to add a search input next to it.

Current structure (around line 2330-2343):
```html
<div class="tag-filter-controls">
    <div class="content-type-filter">
        <span class="tag-filter-label">{{ t('documents.filterByType') }}</span>
        <select class="content-type-select" v-model="itemsFilter.contentType" @change="fetchItems">
            ...
        </select>
    </div>
</div>
```

- [ ] **Step 1: Add search input HTML next to type filter**

Add a new `.search-filter` div inside `tag-filter-controls`, after the `content-type-filter` div:

```html
<div class="tag-filter-controls">
    <div class="content-type-filter">
        <span class="tag-filter-label">{{ t('documents.filterByType') }}</span>
        <select class="content-type-select" v-model="itemsFilter.contentType" @change="fetchItems">
            <option value="">{{ t('documents.allTypes') }}</option>
            <option value="note">{{ t('nav.note') }}</option>
            <option value="bookmark">{{ t('nav.bookmark') }}</option>
            <option value="webpage">{{ t('nav.webpage') }}</option>
            <option value="paper">{{ t('nav.paper') }}</option>
            <option value="email">{{ t('nav.email') }}</option>
            <option value="file">{{ t('nav.file') }}</option>
        </select>
    </div>
    <div class="search-filter">
        <span class="tag-filter-label">{{ t('documents.search') }}</span>
        <input 
            type="text" 
            class="search-input" 
            v-model="itemsFilter.search"
            :placeholder="t('documents.searchPlaceholder')"
            @keyup.enter="fetchItems"
        />
        <button class="btn btn-secondary btn-small" @click="fetchItems">
            {{ t('documents.searchButton') }}
        </button>
    </div>
</div>
```

- [ ] **Step 2: Add CSS styles for the search filter**

Add these styles in the `<style>` section (around line 3100-3200 where other filter styles are defined):

```css
.search-filter {
    display: flex;
    align-items: center;
    gap: 8px;
}

.search-input {
    padding: 6px 12px;
    border: 1px solid #ddd;
    border-radius: 4px;
    font-size: 14px;
    min-width: 250px;
}

.search-input:focus {
    outline: none;
    border-color: #4a90e2;
}

.btn-small {
    padding: 6px 12px;
    font-size: 14px;
}
```

- [ ] **Step 3: Verify the tag-filter-controls CSS supports horizontal layout**

Ensure the `.tag-filter-controls` class uses flex layout to place filters side by side:

```css
.tag-filter-controls {
    display: flex;
    align-items: center;
    gap: 20px;
    flex-wrap: wrap;
}
```

---

## Task 2: Add Translations for Search Feature

**Files:**
- Modify: `/Users/xudonglai/AliDrive/Work/agentic-second-brain/kb/web/static/index.html:~264` (documents section in English translations)
- Modify: `/Users/xudonglai/AliDrive/Work/agentic-second-brain/kb/web/static/index.html:~322` (documents section in Chinese translations)

- [ ] **Step 4: Add English translations**

In the `en` translations object, within the `documents` section (around line 264), add:

```javascript
documents: {
    // ... existing translations ...
    filterByType: 'Filter by Type:',
    allTypes: 'All Types',
    search: 'Search:',
    searchPlaceholder: 'Search in title, source, summary...',
    searchButton: 'Search',
    // ... rest of translations ...
}
```

- [ ] **Step 5: Add Chinese translations**

In the `zh` translations object, within the `documents` section (around line 322), add:

```javascript
documents: {
    // ... existing translations ...
    filterByType: '按类型筛选：',
    allTypes: '全部类型',
    search: '搜索：',
    searchPlaceholder: '在标题、来源、摘要中搜索...',
    searchButton: '搜索',
    // ... rest of translations ...
}
```

---

## Task 3: Test the Implementation

- [ ] **Step 6: Start the web server**

```bash
cd /Users/xudonglai/AliDrive/Work/agentic-second-brain
kb web
```

- [ ] **Step 7: Open browser and navigate to Documents page**

URL: `http://localhost:11201`
Click on "Knowledge Collected" / "知识收集" in the sidebar

- [ ] **Step 8: Verify search input appears**

Check that:
1. The search input is visible next to the type filter dropdown
2. The placeholder text is displayed correctly
3. The search button is visible

- [ ] **Step 9: Test search functionality**

1. Type a keyword in the search input (e.g., a word from a document title)
2. Press Enter or click the Search button
3. Verify the results are filtered to show only matching items
4. Verify the search works together with type filter (e.g., select "note" type and search)
5. Verify the search works together with tag filters

- [ ] **Step 10: Test edge cases**

1. Empty search (should show all results)
2. Search with no matches (should show empty state)
3. Clear search and verify all results return
4. Switch between English and Chinese to verify translations

---

## Task 4: Commit Changes

- [ ] **Step 11: Stop the web server**

Press `Ctrl+C` in the terminal running the server

- [ ] **Step 12: Commit the changes**

```bash
cd /Users/xudonglai/AliDrive/Work/agentic-second-brain
git add kb/web/static/index.html
git commit -m "feat: add keyword search to Documents page

- Add search input next to type filter on Knowledge Collected page
- Search queries title, source, and summary fields via existing API
- Support Enter key and button click to trigger search
- Add English and Chinese translations for search UI"
```

---

## Verification Checklist

- [ ] Search input is visible on Documents page
- [ ] Placeholder text displays correctly in both languages
- [ ] Search button is clickable and triggers search
- [ ] Enter key triggers search
- [ ] Search works with type filter (AND logic)
- [ ] Search works with tag filters (AND logic)
- [ ] Empty search shows all results
- [ ] No matches shows appropriate empty state
- [ ] Translations switch correctly between EN/ZH
