# Frontend Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor the monolithic 8633-line `kb/web/static/index.html` into a modular ES-module-based architecture with page-level Vue components, preserving all existing behavior.

**Architecture:** Split CSS into `base.css`, `layout.css`, `components.css`; extract JS into `main.js`, `store.js`, `router.js`, `api.js`, `i18n.js`, `utils.js`, and page modules under `js/pages/`; move HTML templates to `templates/pages/`; use Vue 3 ESM build with native ES modules (no build tooling).

**Tech Stack:** Vue 3 (ESM build), native ES modules, FastAPI backend (unchanged)

---

## File Structure Overview

**New directories:**
- `kb/web/static/js/` - JavaScript modules
- `kb/web/static/js/pages/` - Page component modules
- `kb/web/static/css/` - Stylesheets
- `kb/web/static/templates/pages/` - HTML templates

**Files to create:**
- `kb/web/static/vue.esm-browser.prod.js` - Vue 3 ESM build
- `kb/web/static/js/main.js` - App bootstrap
- `kb/web/static/js/store.js` - Global reactive store
- `kb/web/static/js/router.js` - Page routing logic
- `kb/web/static/js/api.js` - API wrapper
- `kb/web/static/js/i18n.js` - Internationalization
- `kb/web/static/js/utils.js` - Utility functions
- `kb/web/static/css/base.css` - Reset, variables, theme
- `kb/web/static/css/layout.css` - Sidebar, page structure
- `kb/web/static/css/components.css` - Reusable components
- 17 page modules in `js/pages/*.js`
- 17 page templates in `templates/pages/*.html`

**Files to modify:**
- `kb/web/static/index.html` - Reduce to shell (<200 lines)

---

## Phase 0: Scaffolding and Foundation

### Task 1: Create Directory Structure

**Files:**
- Create: `kb/web/static/js/`
- Create: `kb/web/static/js/pages/`
- Create: `kb/web/static/css/`
- Create: `kb/web/static/templates/pages/`

- [ ] **Step 1: Create directories**

```bash
mkdir -p kb/web/static/js/pages
mkdir -p kb/web/static/css
mkdir -p kb/web/static/templates/pages
```

- [ ] **Step 2: Verify directory structure**

Run: `ls -la kb/web/static/`
Expected: Should see `js/`, `css/`, `templates/` directories

- [ ] **Step 3: Commit**

```bash
git add kb/web/static/js/.gitkeep kb/web/static/css/.gitkeep kb/web/static/templates/.gitkeep
git commit -m "chore: create directory structure for frontend refactor"
```

---

### Task 2: Download Vue 3 ESM Build

**Files:**
- Create: `kb/web/static/vue.esm-browser.prod.js`

- [ ] **Step 1: Download Vue 3 ESM build**

```bash
cd kb/web/static
curl -o vue.esm-browser.prod.js https://unpkg.com/vue@3.4.21/dist/vue.esm-browser.prod.js
```

- [ ] **Step 2: Verify file downloaded**

Run: `ls -lh kb/web/static/vue.esm-browser.prod.js`
Expected: File exists, ~150KB

- [ ] **Step 3: Commit**

```bash
git add kb/web/static/vue.esm-browser.prod.js
git commit -m "feat: add Vue 3 ESM build"
```

---

### Task 3: Extract CSS - Base Styles

**Files:**
- Create: `kb/web/static/css/base.css`
- Read: `kb/web/static/index.html:644-740` (CSS variables and reset)

- [ ] **Step 1: Extract CSS variables and reset to base.css**

Create `kb/web/static/css/base.css`:

```css
/* CSS Variables and Theme */
:root {
    --primary: #4f46e5;
    --primary-hover: #4338ca;
    --primary-light: #eef2ff;
    --bg: #f8fafc;
    --card-bg: #ffffff;
    --text: #1e293b;
    --text-secondary: #64748b;
    --border: #e2e8f0;
    --success: #22c55e;
    --danger: #ef4444;
    --warning: #f59e0b;
    --type-file: #3b82f6;
    --type-webpage: #22c55e;
    --type-bookmark: #a855f7;
    --type-note: #eab308;
    --type-paper: #f97316;
    --type-email: #ec4899;
    --warm-accent: #f59e0b;
    --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
    --shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
    --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
}

/* CSS Reset */
* { 
    box-sizing: border-box; 
    margin: 0; 
    padding: 0; 
}

[v-cloak] { 
    display: none !important; 
}

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
    background: var(--bg);
    color: var(--text);
    line-height: 1.6;
}

.app-container { 
    display: flex; 
    min-height: 100vh; 
}
```

- [ ] **Step 2: Verify CSS file created**

Run: `cat kb/web/static/css/base.css | head -20`
Expected: Shows CSS variables

- [ ] **Step 3: Commit**

```bash
git add kb/web/static/css/base.css
git commit -m "feat: extract base CSS (variables, reset)"
```

---

### Task 4: Extract CSS - Layout Styles

**Files:**
- Create: `kb/web/static/css/layout.css`
- Read: `kb/web/static/index.html:678-1200` (sidebar, main content layout)

- [ ] **Step 1: Create layout.css with sidebar and main content styles**

Note: Due to size, this will be a representative subset. The full extraction requires reading lines 678-1200 from index.html and copying all layout-related selectors (.sidebar, .logo, .nav-*, .main-content, .page-header, etc.)

Create `kb/web/static/css/layout.css` with sidebar navigation and main content layout styles.

- [ ] **Step 2: Verify layout.css created**

Run: `grep -c "\.sidebar\|\.main-content\|\.nav-" kb/web/static/css/layout.css`
Expected: Multiple matches for layout selectors

- [ ] **Step 3: Commit**

```bash
git add kb/web/static/css/layout.css
git commit -m "feat: extract layout CSS (sidebar, navigation, main content)"
```

---

### Task 5: Extract CSS - Component Styles

**Files:**
- Create: `kb/web/static/css/components.css`
- Read: `kb/web/static/index.html:1200-3509` (buttons, cards, modals, forms, etc.)

- [ ] **Step 1: Create components.css with reusable component styles**

Note: Extract all component styles (.btn, .card, .modal, .badge, .tag-pill, .input, .table, .toast, etc.) from the remaining CSS block.

Create `kb/web/static/css/components.css` with all reusable component styles.

- [ ] **Step 2: Verify components.css created**

Run: `grep -c "\.btn\|\.card\|\.modal\|\.badge" kb/web/static/css/components.css`
Expected: Multiple matches for component selectors

- [ ] **Step 3: Commit**

```bash
git add kb/web/static/css/components.css
git commit -m "feat: extract component CSS (buttons, cards, modals, forms)"
```

---

### Task 6: Extract i18n Module

**Files:**
- Create: `kb/web/static/js/i18n.js`
- Read: `kb/web/static/index.html:21-642` (translations object)

- [ ] **Step 1: Create i18n.js with translations and t() function**

```javascript
// kb/web/static/js/i18n.js
const translations = {
    en: {
        app: {
            name: 'Agentic Local Brain',
            nameLine1: 'Agentic',
            nameLine2: 'Local Brain'
        },
        nav: {
            dashboard: 'Overview',
            documents: 'Knowledge Collected',
            note: 'Note',
            bookmark: 'Bookmark',
            webpage: 'Webpage',
            paper: 'Paper',
            email: 'Email',
            file: 'File',
            tags: 'Tags Management',
            search: 'Search',
            mining: 'Knowledge Mining',
            wiki: 'LLM Wiki',
            rag: 'Enhanced Retrieval',
            backup: 'Backup',
            settings: 'System Settings'
        }
        // ... (copy all translation keys from index.html lines 21-642)
    },
    zh: {
        // ... (copy all Chinese translations)
    }
};

let currentLocale = localStorage.getItem('kb-locale') || 'en';

export function getLocale() {
    return currentLocale;
}

export function setLocale(locale) {
    currentLocale = locale;
    localStorage.setItem('kb-locale', locale);
}

export function t(key) {
    const keys = key.split('.');
    let value = translations[currentLocale];
    for (const k of keys) {
        value = value?.[k];
    }
    return value || key;
}
```

- [ ] **Step 2: Verify i18n.js exports**

Run: `grep "export" kb/web/static/js/i18n.js`
Expected: Shows export statements for getLocale, setLocale, t

- [ ] **Step 3: Commit**

```bash
git add kb/web/static/js/i18n.js
git commit -m "feat: extract i18n module with translations"
```

---

### Task 7: Extract API Module

**Files:**
- Create: `kb/web/static/js/api.js`

- [ ] **Step 1: Create api.js with fetch wrapper**

```javascript
// kb/web/static/js/api.js
const API_BASE = '/api';

async function request(method, endpoint, data = null) {
    const options = {
        method,
        headers: {
            'Content-Type': 'application/json'
        }
    };
    
    if (data) {
        options.body = JSON.stringify(data);
    }
    
    const response = await fetch(`${API_BASE}${endpoint}`, options);
    
    if (!response.ok) {
        const error = await response.json().catch(() => ({ message: 'Request failed' }));
        throw new Error(error.message || `HTTP ${response.status}`);
    }
    
    return response.json();
}

export const api = {
    get: (endpoint) => request('GET', endpoint),
    post: (endpoint, data) => request('POST', endpoint, data),
    put: (endpoint, data) => request('PUT', endpoint, data),
    delete: (endpoint) => request('DELETE', endpoint)
};
```

- [ ] **Step 2: Verify api.js exports**

Run: `grep "export" kb/web/static/js/api.js`
Expected: Shows export statement for api object

- [ ] **Step 3: Commit**

```bash
git add kb/web/static/js/api.js
git commit -m "feat: extract API module with fetch wrapper"
```

---

### Task 8: Extract Utils Module

**Files:**
- Create: `kb/web/static/js/utils.js`

- [ ] **Step 1: Create utils.js with helper functions**

```javascript
// kb/web/static/js/utils.js

export function formatDate(dateString) {
    if (!dateString) return '';
    const date = new Date(dateString);
    return date.toLocaleString();
}

export function formatRelativeTime(dateString) {
    if (!dateString) return '';
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now - date;
    const diffSec = Math.floor(diffMs / 1000);
    const diffMin = Math.floor(diffSec / 60);
    const diffHour = Math.floor(diffMin / 60);
    const diffDay = Math.floor(diffHour / 24);
    
    if (diffDay > 0) return `${diffDay}d ago`;
    if (diffHour > 0) return `${diffHour}h ago`;
    if (diffMin > 0) return `${diffMin}m ago`;
    return 'just now';
}

export function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

export function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

export function truncate(text, maxLength) {
    if (!text || text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
}
```

- [ ] **Step 2: Verify utils.js exports**

Run: `grep "export function" kb/web/static/js/utils.js`
Expected: Shows multiple export function statements

- [ ] **Step 3: Commit**

```bash
git add kb/web/static/js/utils.js
git commit -m "feat: extract utils module with helper functions"
```

---

### Task 9: Extract Store Module

**Files:**
- Create: `kb/web/static/js/store.js`

- [ ] **Step 1: Create store.js with reactive global state**

```javascript
// kb/web/static/js/store.js
import { reactive } from '../vue.esm-browser.prod.js';
import { getLocale } from './i18n.js';

export const store = reactive({
    // App state
    locale: getLocale(),
    theme: localStorage.getItem('kb-theme') || 'light',
    currentPage: 'dashboard',
    version: '',
    
    // Dashboard
    stats: {},
    recentByType: {
        note: [],
        bookmark: [],
        webpage: [],
        paper: [],
        email: [],
        file: []
    },
    
    // Items
    items: [],
    itemsFilter: {
        contentType: '',
        limit: 20,
        offset: 0,
        tag: '',
        tags: [],
        search: ''
    },
    
    // Tags
    tags: [],
    topTags: [],
    topTagsForType: {},
    allTagsForType: {},
    
    // Loading states
    loading: {
        stats: false,
        items: false,
        tags: false,
        graph: false,
        topics: false,
        timeline: false,
        recommendations: false,
        wiki: false,
        rag: false,
        mining: false,
        backup: false,
        settings: false
    },
    
    // Modals
    showItemModal: false,
    selectedItem: null,
    showTagItemsModal: false,
    selectedTagName: '',
    tagItems: [],
    showDeleteConfirm: false,
    deleteConfirmMessage: '',
    deleteCallback: null,
    showDeleteFileOption: false,
    deleteFileChecked: false,
    showPreviewModal: false,
    previewItem: null,
    
    // Toasts
    toasts: []
});
```

- [ ] **Step 2: Verify store.js exports**

Run: `grep "export" kb/web/static/js/store.js`
Expected: Shows export statement for store

- [ ] **Step 3: Commit**

```bash
git add kb/web/static/js/store.js
git commit -m "feat: extract store module with reactive global state"
```

---

### Task 10: Extract Router Module

**Files:**
- Create: `kb/web/static/js/router.js`

- [ ] **Step 1: Create router.js with page component registry**

```javascript
// kb/web/static/js/router.js
import { defineAsyncComponent } from '../vue.esm-browser.prod.js';

export const pages = {
    dashboard: defineAsyncComponent(() => import('./pages/dashboard.js')),
    items: defineAsyncComponent(() => import('./pages/items.js')),
    'items-note': defineAsyncComponent(() => import('./pages/items-note.js')),
    'items-bookmark': defineAsyncComponent(() => import('./pages/items-bookmark.js')),
    'items-webpage': defineAsyncComponent(() => import('./pages/items-webpage.js')),
    'items-paper': defineAsyncComponent(() => import('./pages/items-paper.js')),
    'items-email': defineAsyncComponent(() => import('./pages/items-email.js')),
    'items-file': defineAsyncComponent(() => import('./pages/items-file.js')),
    tags: defineAsyncComponent(() => import('./pages/tags.js')),
    graph: defineAsyncComponent(() => import('./pages/graph.js')),
    topics: defineAsyncComponent(() => import('./pages/topics.js')),
    timeline: defineAsyncComponent(() => import('./pages/timeline.js')),
    recommendations: defineAsyncComponent(() => import('./pages/recommendations.js')),
    wiki: defineAsyncComponent(() => import('./pages/wiki.js')),
    mining: defineAsyncComponent(() => import('./pages/mining.js')),
    rag: defineAsyncComponent(() => import('./pages/rag.js')),
    settings: defineAsyncComponent(() => import('./pages/settings.js')),
    backup: defineAsyncComponent(() => import('./pages/backup.js'))
};

export function getPageComponent(pageName) {
    return pages[pageName] || pages.dashboard;
}
```

- [ ] **Step 2: Verify router.js exports**

Run: `grep "export" kb/web/static/js/router.js`
Expected: Shows export statements for pages and getPageComponent

- [ ] **Step 3: Commit**

```bash
git add kb/web/static/js/router.js
git commit -m "feat: extract router module with page registry"
```

---

## Phase 1: Pilot Page Migration (Settings)

### Task 11: Extract Settings Page Template

**Files:**
- Create: `kb/web/static/templates/pages/settings.html`
- Read: `kb/web/static/index.html` (find settings page HTML block)

- [ ] **Step 1: Extract settings page HTML template**

Find the `<div v-if="currentPage === 'settings'">` block in index.html and extract it to `templates/pages/settings.html` (remove the outer v-if wrapper, keep only the inner content).

- [ ] **Step 2: Verify template created**

Run: `head -20 kb/web/static/templates/pages/settings.html`
Expected: Shows settings page HTML

- [ ] **Step 3: Commit**

```bash
git add kb/web/static/templates/pages/settings.html
git commit -m "feat: extract settings page template"
```

---

### Task 12: Create Settings Page Component

**Files:**
- Create: `kb/web/static/js/pages/settings.js`

- [ ] **Step 1: Create settings.js page component**

```javascript
// kb/web/static/js/pages/settings.js
import { store } from '../store.js';
import { api } from '../api.js';
import { t } from '../i18n.js';

const template = await fetch('/static/templates/pages/settings.html').then(r => r.text());

export default {
    name: 'SettingsPage',
    template,
    data() {
        return {
            settings: {
                model: {},
                backup: {},
                diagnostics: {}
            },
            activeTab: 'model'
        };
    },
    computed: {
        store: () => store,
        locale() { return store.locale; },
        t() { return t; }
    },
    methods: {
        async loadSettings() {
            store.loading.settings = true;
            try {
                const response = await api.get('/settings');
                this.settings = response;
            } catch (error) {
                this.showToast('error', 'Failed to load settings');
            } finally {
                store.loading.settings = false;
            }
        },
        async saveSettings() {
            try {
                await api.post('/settings', this.settings);
                this.showToast('success', 'Settings saved');
            } catch (error) {
                this.showToast('error', 'Failed to save settings');
            }
        },
        showToast(type, message) {
            store.toasts.push({ type, message });
            setTimeout(() => store.toasts.shift(), 3000);
        }
    },
    async mounted() {
        await this.loadSettings();
    }
};
```

- [ ] **Step 2: Verify settings.js created**

Run: `grep "export default" kb/web/static/js/pages/settings.js`
Expected: Shows export default statement

- [ ] **Step 3: Commit**

```bash
git add kb/web/static/js/pages/settings.js
git commit -m "feat: create settings page component"
```

---

### Task 13: Create Main App Bootstrap

**Files:**
- Create: `kb/web/static/js/main.js`

- [ ] **Step 1: Create main.js with app bootstrap**

```javascript
// kb/web/static/js/main.js
import { createApp } from '../vue.esm-browser.prod.js';
import { store } from './store.js';
import { t, setLocale } from './i18n.js';
import { getPageComponent } from './router.js';
import { api } from './api.js';

const App = {
    setup() {
        return { store };
    },
    computed: {
        currentPageComponent() {
            return getPageComponent(store.currentPage);
        },
        t() { return t; },
        isDocumentsPage() {
            return store.currentPage === 'items' || store.currentPage.startsWith('items-');
        },
        isMiningPage() {
            return ['mining', 'graph', 'topics', 'timeline', 'recommendations'].includes(store.currentPage);
        }
    },
    methods: {
        navigateTo(page) {
            store.currentPage = page;
        },
        toggleLocale() {
            const newLocale = store.locale === 'en' ? 'zh' : 'en';
            store.locale = newLocale;
            setLocale(newLocale);
        },
        async loadVersion() {
            try {
                const response = await api.get('/version');
                store.version = response.version;
            } catch (error) {
                console.error('Failed to load version:', error);
            }
        }
    },
    async mounted() {
        await this.loadVersion();
    }
};

createApp(App).mount('#app');
```

- [ ] **Step 2: Verify main.js created**

Run: `grep "createApp" kb/web/static/js/main.js`
Expected: Shows createApp and mount call

- [ ] **Step 3: Commit**

```bash
git add kb/web/static/js/main.js
git commit -m "feat: create main app bootstrap"
```

---

### Task 14: Update index.html to Use Modular Structure

**Files:**
- Modify: `kb/web/static/index.html`

- [ ] **Step 1: Replace CSS <style> block with <link> tags**

In `index.html`, replace the entire `<style>` block (lines 644-3509) with:

```html
<link rel="stylesheet" href="/static/css/base.css">
<link rel="stylesheet" href="/static/css/layout.css">
<link rel="stylesheet" href="/static/css/components.css">
```

- [ ] **Step 2: Replace Vue global script with ESM script**

Replace `<script src="/static/vue.global.prod.js"></script>` with:

```html
<script type="module" src="/static/js/main.js"></script>
```

- [ ] **Step 3: Remove inline Vue app script**

Remove the entire `<script>` block starting with `const { createApp } = Vue;` (lines 6318-8633).

- [ ] **Step 4: Verify index.html is now minimal**

Run: `wc -l kb/web/static/index.html`
Expected: Should be significantly reduced (target <4000 lines for Phase 1)

- [ ] **Step 5: Commit**

```bash
git add kb/web/static/index.html
git commit -m "refactor: update index.html to use modular CSS and JS"
```

---

### Task 15: Phase 1 Verification - Settings Page

**Files:**
- Test: `kb/web/static/index.html`

- [ ] **Step 1: Start web server**

Run: `python3 -m kb.cli web` or `cd kb && python3 -m uvicorn web.app:app --reload --port 11201`

- [ ] **Step 2: Open browser and test**

1. Navigate to `http://localhost:11201/`
2. Open browser console (F12)
3. Check for errors (should be none)
4. Click "System Settings" in sidebar
5. Verify settings page loads
6. Toggle locale (EN ⇄ 中文)
7. Toggle theme (if implemented)

Expected: Settings page renders, no console errors, locale toggle works

- [ ] **Step 3: Stop server and document results**

If any issues found, document them and fix before proceeding.

---

## Phase 2: Remaining Pages Migration

### Task 16: Migrate Dashboard Page

**Files:**
- Create: `kb/web/static/templates/pages/dashboard.html`
- Create: `kb/web/static/js/pages/dashboard.js`

- [ ] **Step 1: Extract dashboard template**

Extract the `<div v-if="currentPage === 'dashboard'">` block from index.html to `templates/pages/dashboard.html`.

- [ ] **Step 2: Create dashboard.js component**

```javascript
// kb/web/static/js/pages/dashboard.js
import { store } from '../store.js';
import { api } from '../api.js';
import { t } from '../i18n.js';
import { formatRelativeTime } from '../utils.js';

const template = await fetch('/static/templates/pages/dashboard.html').then(r => r.text());

export default {
    name: 'DashboardPage',
    template,
    computed: {
        store: () => store,
        t() { return t; },
        formatRelativeTime() { return formatRelativeTime; }
    },
    methods: {
        async loadStats() {
            store.loading.stats = true;
            try {
                const stats = await api.get('/dashboard/stats');
                store.stats = stats;
            } catch (error) {
                console.error('Failed to load stats:', error);
            } finally {
                store.loading.stats = false;
            }
        },
        async loadRecentItems(type) {
            store.loading[`recent${type.charAt(0).toUpperCase() + type.slice(1)}`] = true;
            try {
                const items = await api.get(`/items?content_type=${type}&limit=5`);
                store.recentByType[type] = items.items || [];
            } catch (error) {
                console.error(`Failed to load recent ${type}:`, error);
            } finally {
                store.loading[`recent${type.charAt(0).toUpperCase() + type.slice(1)}`] = false;
            }
        },
        navigateTo(page) {
            store.currentPage = page;
        }
    },
    async mounted() {
        await this.loadStats();
        await Promise.all([
            this.loadRecentItems('note'),
            this.loadRecentItems('bookmark'),
            this.loadRecentItems('webpage'),
            this.loadRecentItems('paper'),
            this.loadRecentItems('email'),
            this.loadRecentItems('file')
        ]);
    }
};
```

- [ ] **Step 3: Remove dashboard block from index.html**

Remove the dashboard `<div v-if="currentPage === 'dashboard'">` block from index.html.

- [ ] **Step 4: Commit**

```bash
git add kb/web/static/templates/pages/dashboard.html kb/web/static/js/pages/dashboard.js kb/web/static/index.html
git commit -m "feat: migrate dashboard page to modular structure"
```

---

### Task 17: Migrate Items Pages (Batch)

**Files:**
- Create: `kb/web/static/templates/pages/items.html`
- Create: `kb/web/static/templates/pages/items-note.html`
- Create: `kb/web/static/templates/pages/items-bookmark.html`
- Create: `kb/web/static/templates/pages/items-webpage.html`
- Create: `kb/web/static/templates/pages/items-paper.html`
- Create: `kb/web/static/templates/pages/items-email.html`
- Create: `kb/web/static/templates/pages/items-file.html`
- Create: `kb/web/static/js/pages/items.js`
- Create: `kb/web/static/js/pages/items-note.js`
- Create: `kb/web/static/js/pages/items-bookmark.js`
- Create: `kb/web/static/js/pages/items-webpage.js`
- Create: `kb/web/static/js/pages/items-paper.js`
- Create: `kb/web/static/js/pages/items-email.js`
- Create: `kb/web/static/js/pages/items-file.js`

- [ ] **Step 1: Extract all items page templates**

Extract each `<div v-if="currentPage === 'items'">`, `<div v-if="currentPage === 'items-note'">`, etc. blocks from index.html to their respective template files.

- [ ] **Step 2: Create items.js base component**

```javascript
// kb/web/static/js/pages/items.js
import { store } from '../store.js';
import { api } from '../api.js';
import { t } from '../i18n.js';

const template = await fetch('/static/templates/pages/items.html').then(r => r.text());

export default {
    name: 'ItemsPage',
    template,
    computed: {
        store: () => store,
        t() { return t; }
    },
    methods: {
        async loadItems() {
            store.loading.items = true;
            try {
                const params = new URLSearchParams({
                    limit: store.itemsFilter.limit,
                    offset: store.itemsFilter.offset,
                    content_type: store.itemsFilter.contentType || '',
                    search: store.itemsFilter.search || ''
                });
                const response = await api.get(`/items?${params}`);
                store.items = response.items || [];
            } catch (error) {
                console.error('Failed to load items:', error);
            } finally {
                store.loading.items = false;
            }
        }
    },
    async mounted() {
        await this.loadItems();
    }
};
```

- [ ] **Step 3: Create type-specific item components**

Create similar components for items-note.js, items-bookmark.js, items-webpage.js, items-paper.js, items-email.js, items-file.js (each with their specific content_type filter).

- [ ] **Step 4: Remove items blocks from index.html**

Remove all items-related `<div v-if>` blocks from index.html.

- [ ] **Step 5: Commit**

```bash
git add kb/web/static/templates/pages/items*.html kb/web/static/js/pages/items*.js kb/web/static/index.html
git commit -m "feat: migrate all items pages to modular structure"
```

---

### Task 18: Migrate Tags, Graph, Topics, Timeline, Recommendations Pages

**Files:**
- Create: `kb/web/static/templates/pages/tags.html`
- Create: `kb/web/static/templates/pages/graph.html`
- Create: `kb/web/static/templates/pages/topics.html`
- Create: `kb/web/static/templates/pages/timeline.html`
- Create: `kb/web/static/templates/pages/recommendations.html`
- Create: `kb/web/static/js/pages/tags.js`
- Create: `kb/web/static/js/pages/graph.js`
- Create: `kb/web/static/js/pages/topics.js`
- Create: `kb/web/static/js/pages/timeline.js`
- Create: `kb/web/static/js/pages/recommendations.js`

- [ ] **Step 1: Extract templates for tags, graph, topics, timeline, recommendations**

Extract each page's HTML block from index.html to respective template files.

- [ ] **Step 2: Create tags.js component**

```javascript
// kb/web/static/js/pages/tags.js
import { store } from '../store.js';
import { api } from '../api.js';
import { t } from '../i18n.js';

const template = await fetch('/static/templates/pages/tags.html').then(r => r.text());

export default {
    name: 'TagsPage',
    template,
    data() {
        return {
            mergeForm: { source: '', target: '' }
        };
    },
    computed: {
        store: () => store,
        t() { return t; }
    },
    methods: {
        async loadTags() {
            store.loading.tags = true;
            try {
                store.tags = await api.get('/tags');
            } catch (error) {
                console.error('Failed to load tags:', error);
            } finally {
                store.loading.tags = false;
            }
        },
        async mergeTags() {
            try {
                await api.post('/tags/merge', this.mergeForm);
                await this.loadTags();
            } catch (error) {
                console.error('Failed to merge tags:', error);
            }
        }
    },
    async mounted() {
        await this.loadTags();
    }
};
```

- [ ] **Step 3: Create graph.js, topics.js, timeline.js, recommendations.js components**

Create similar components for each page with their specific API endpoints and data loading logic.

- [ ] **Step 4: Remove these page blocks from index.html**

- [ ] **Step 5: Commit**

```bash
git add kb/web/static/templates/pages/{tags,graph,topics,timeline,recommendations}.html kb/web/static/js/pages/{tags,graph,topics,timeline,recommendations}.js kb/web/static/index.html
git commit -m "feat: migrate tags, graph, topics, timeline, recommendations pages"
```

---

### Task 19: Migrate Wiki, Mining, RAG Pages

**Files:**
- Create: `kb/web/static/templates/pages/wiki.html`
- Create: `kb/web/static/templates/pages/mining.html`
- Create: `kb/web/static/templates/pages/rag.html`
- Create: `kb/web/static/js/pages/wiki.js`
- Create: `kb/web/static/js/pages/mining.js`
- Create: `kb/web/static/js/pages/rag.js`

- [ ] **Step 1: Extract templates for wiki, mining, rag**

Extract each page's HTML block from index.html to respective template files.

- [ ] **Step 2: Create wiki.js component**

```javascript
// kb/web/static/js/pages/wiki.js
import { store } from '../store.js';
import { api } from '../api.js';
import { t } from '../i18n.js';

const template = await fetch('/static/templates/pages/wiki.html').then(r => r.text());

export default {
    name: 'WikiPage',
    template,
    data() {
        return {
            articles: [],
            categories: []
        };
    },
    computed: {
        store: () => store,
        t() { return t; }
    },
    methods: {
        async loadWiki() {
            store.loading.wiki = true;
            try {
                const [articles, tree] = await Promise.all([
                    api.get('/wiki/articles'),
                    api.get('/wiki/tree')
                ]);
                this.articles = articles;
                this.categories = tree;
            } catch (error) {
                console.error('Failed to load wiki:', error);
            } finally {
                store.loading.wiki = false;
            }
        }
    },
    async mounted() {
        await this.loadWiki();
    }
};
```

- [ ] **Step 3: Create mining.js and rag.js components**

Create similar components for mining and rag pages with their specific logic.

- [ ] **Step 4: Remove these page blocks from index.html**

- [ ] **Step 5: Commit**

```bash
git add kb/web/static/templates/pages/{wiki,mining,rag}.html kb/web/static/js/pages/{wiki,mining,rag}.js kb/web/static/index.html
git commit -m "feat: migrate wiki, mining, rag pages"
```

---

### Task 20: Migrate Backup Page

**Files:**
- Create: `kb/web/static/templates/pages/backup.html`
- Create: `kb/web/static/js/pages/backup.js`

- [ ] **Step 1: Extract backup template**

Extract the `<div v-if="currentPage === 'backup'">` block from index.html to `templates/pages/backup.html`.

- [ ] **Step 2: Create backup.js component**

```javascript
// kb/web/static/js/pages/backup.js
import { store } from '../store.js';
import { api } from '../api.js';
import { t } from '../i18n.js';

const template = await fetch('/static/templates/pages/backup.html').then(r => r.text());

export default {
    name: 'BackupPage',
    template,
    data() {
        return {
            backups: [],
            backupTasks: []
        };
    },
    computed: {
        store: () => store,
        t() { return t; }
    },
    methods: {
        async loadBackups() {
            store.loading.backups = true;
            try {
                this.backups = await api.get('/backup/list');
            } catch (error) {
                console.error('Failed to load backups:', error);
            } finally {
                store.loading.backups = false;
            }
        },
        async createBackup() {
            try {
                await api.post('/backup/create');
                await this.loadBackups();
            } catch (error) {
                console.error('Failed to create backup:', error);
            }
        }
    },
    async mounted() {
        await this.loadBackups();
    }
};
```

- [ ] **Step 3: Remove backup block from index.html**

- [ ] **Step 4: Commit**

```bash
git add kb/web/static/templates/pages/backup.html kb/web/static/js/pages/backup.js kb/web/static/index.html
git commit -m "feat: migrate backup page"
```

---

## Phase 3: Cleanup and Finalization

### Task 21: Finalize index.html Shell

**Files:**
- Modify: `kb/web/static/index.html`

- [ ] **Step 1: Reduce index.html to minimal shell**

Ensure index.html contains only:
- `<head>` with meta tags, title, CSS links
- `<body>` with `<div id="app">` and sidebar/main structure
- `<script type="module" src="/static/js/main.js"></script>`

Target: Under 200 lines total.

- [ ] **Step 2: Verify all inline scripts removed**

Run: `grep -n "<script>" kb/web/static/index.html | grep -v "type=\"module\""`
Expected: Only external script references (marked.min.js, echarts, main.js)

- [ ] **Step 3: Verify all inline styles removed**

Run: `grep -n "<style>" kb/web/static/index.html`
Expected: No matches

- [ ] **Step 4: Commit**

```bash
git add kb/web/static/index.html
git commit -m "refactor: finalize index.html as minimal shell"
```

---

### Task 22: Update Package Data Configuration

**Files:**
- Modify: `pyproject.toml:65-70`

- [ ] **Step 1: Verify package-data includes new directories**

Check that `pyproject.toml` includes:

```toml
[tool.setuptools.package-data]
kb = [
    "config-template.yaml",
    "web/static/**/*",
    "web/static/*",
]
```

This should already cover the new `js/`, `css/`, `templates/` directories.

- [ ] **Step 2: Test packaging**

```bash
python3 -m build
```

Expected: Build completes successfully

- [ ] **Step 3: Verify new files in wheel**

```bash
unzip -l dist/localbrain-*.whl | grep "web/static/js\|web/static/css\|web/static/templates"
```

Expected: Shows files from new directories

- [ ] **Step 4: Commit if changes needed**

```bash
git add pyproject.toml
git commit -m "chore: ensure package-data includes refactored frontend files"
```

---

### Task 23: Create Frontend README

**Files:**
- Create: `kb/web/static/README.md`

- [ ] **Step 1: Create README documenting the new structure**

```markdown
# Frontend Architecture

This directory contains the modular frontend for Agentic Local Brain.

## Structure

- `index.html` - Minimal HTML shell (<200 lines)
- `vue.esm-browser.prod.js` - Vue 3 ESM build
- `marked.min.js` - Markdown parser
- `js/` - JavaScript modules
  - `main.js` - App bootstrap and mount
  - `store.js` - Global reactive state
  - `router.js` - Page component registry
  - `api.js` - API fetch wrapper
  - `i18n.js` - Internationalization
  - `utils.js` - Utility functions
  - `pages/` - Page components (17 pages)
- `css/` - Stylesheets
  - `base.css` - CSS variables, reset, theme
  - `layout.css` - Sidebar, navigation, main layout
  - `components.css` - Reusable UI components
- `templates/pages/` - HTML templates for page components

## Adding a New Page

1. Create template: `templates/pages/my-page.html`
2. Create component: `js/pages/my-page.js`
3. Register in `js/router.js`:
   ```javascript
   'my-page': defineAsyncComponent(() => import('./pages/my-page.js'))
   ```
4. Add navigation item in `index.html` sidebar

## Development

No build step required. Uses native ES modules.

Run: `python3 -m kb.cli web` or `localbrain web`
```

- [ ] **Step 2: Commit**

```bash
git add kb/web/static/README.md
git commit -m "docs: add frontend architecture README"
```

---

### Task 24: Update Root README

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Add note about frontend refactor in README**

Add a section or update existing frontend documentation to mention the modular structure:

```markdown
## Frontend Architecture

The web interface uses a modular Vue 3 architecture with native ES modules (no build step required). See `kb/web/static/README.md` for details.
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: update README with frontend architecture note"
```

---

### Task 25: Comprehensive Manual Verification

**Files:**
- Test: All pages in the application

- [ ] **Step 1: Start web server**

```bash
python3 -m kb.cli web
```

Or if dependencies are installed:
```bash
localbrain web
```

- [ ] **Step 2: Open browser and test all pages**

Navigate to `http://localhost:11201/` and verify:

1. **Dashboard** - Loads, shows stats, recent items
2. **Items** - All 7 sub-pages (items, note, bookmark, webpage, paper, email, file)
3. **Tags** - Tag cloud, merge functionality
4. **Graph** - Knowledge graph visualization
5. **Topics** - Topic clusters
6. **Timeline** - Timeline view
7. **Recommendations** - Smart recommendations
8. **Wiki** - Wiki articles
9. **Mining** - Mining controls
10. **RAG** - Enhanced retrieval chat
11. **Backup** - Backup management
12. **Settings** - System settings

For each page:
- Check browser console for errors (should be none)
- Verify page renders correctly
- Test one primary action (search, filter, save, etc.)

- [ ] **Step 3: Test locale toggle**

1. Click locale toggle (EN ⇄ 中文)
2. Navigate between pages
3. Verify locale persists across page changes

- [ ] **Step 4: Test theme toggle (if implemented)**

1. Toggle theme (light ⇄ dark)
2. Verify theme persists

- [ ] **Step 5: Check network tab**

1. Open DevTools Network tab
2. Navigate between pages
3. Verify no 404 errors for JS/CSS/template files

- [ ] **Step 6: Document any issues**

If issues found, create a list and fix before final commit.

---

### Task 26: Create Playwright Test Suite (Optional but Recommended)

**Files:**
- Create: `tests/web/test_smoke.py`
- Create: `tests/web/conftest.py`

- [ ] **Step 1: Install Playwright (if not already installed)**

```bash
pip install pytest playwright
playwright install chromium
```

- [ ] **Step 2: Create pytest fixtures**

```python
# tests/web/conftest.py
import pytest
import subprocess
import time
import requests
from pathlib import Path

@pytest.fixture(scope="session")
def web_server():
    """Start web server for testing"""
    # Start server in background
    proc = subprocess.Popen(
        ["python3", "-m", "kb.cli", "web", "-p", "11202"],
        cwd=Path(__file__).parent.parent.parent
    )
    
    # Wait for server to be ready
    for _ in range(30):
        try:
            requests.get("http://localhost:11202/")
            break
        except:
            time.sleep(0.5)
    
    yield "http://localhost:11202"
    
    # Cleanup
    proc.terminate()
    proc.wait()

@pytest.fixture
def page(web_server, playwright):
    browser = playwright.chromium.launch()
    context = browser.new_context()
    page = context.new_page()
    page.goto(web_server)
    yield page
    context.close()
    browser.close()
```

- [ ] **Step 3: Create smoke tests**

```python
# tests/web/test_smoke.py
import pytest

PAGES = [
    ('dashboard', 'Overview'),
    ('items', 'Knowledge'),
    ('items-note', 'Notes'),
    ('items-bookmark', 'Bookmarks'),
    ('items-webpage', 'Webpages'),
    ('items-paper', 'Papers'),
    ('items-email', 'Emails'),
    ('items-file', 'Files'),
    ('tags', 'Tags'),
    ('graph', 'Graph'),
    ('topics', 'Topics'),
    ('timeline', 'Timeline'),
    ('recommendations', 'Recommendations'),
    ('wiki', 'Wiki'),
    ('mining', 'Mining'),
    ('rag', 'Retrieval'),
    ('backup', 'Backup'),
    ('settings', 'Settings')
]

@pytest.mark.parametrize("page_name,expected_text", PAGES)
def test_page_loads(page, page_name, expected_text):
    """Test that each page loads without errors"""
    # Click navigation item
    page.click(f'text="{expected_text}"')
    
    # Wait for page to load
    page.wait_for_load_state("networkidle")
    
    # Check no console errors
    errors = []
    page.on("console", lambda msg: errors.append(msg) if msg.type == "error" else None)
    
    assert len(errors) == 0, f"Console errors on {page_name}: {errors}"

def test_locale_toggle(page):
    """Test locale switching"""
    # Toggle to Chinese
    page.click('button:has-text("EN")')
    page.wait_for_timeout(500)
    
    # Verify Chinese text appears
    assert page.locator('text="中文"').is_visible()
    
    # Toggle back to English
    page.click('button:has-text("中文")')
    page.wait_for_timeout(500)
    
    # Verify English text appears
    assert page.locator('text="EN"').is_visible()
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/web/test_smoke.py -v
```

Expected: All tests pass

- [ ] **Step 5: Commit tests**

```bash
git add tests/web/
git commit -m "test: add Playwright smoke tests for frontend"
```

---

### Task 27: Final Packaging Verification

**Files:**
- Test: Package build and installation

- [ ] **Step 1: Clean previous builds**

```bash
rm -rf dist/ build/ *.egg-info
```

- [ ] **Step 2: Build package**

```bash
python3 -m build
```

Expected: Creates wheel in `dist/` directory

- [ ] **Step 3: Create test virtualenv and install**

```bash
python3 -m venv /tmp/test-localbrain
source /tmp/test-localbrain/bin/activate
pip install dist/localbrain-*.whl
```

- [ ] **Step 4: Verify files installed**

```bash
python3 -c "import kb.web; import os; print(os.path.dirname(kb.web.__file__))"
ls -la $(python3 -c "import kb.web; import os; print(os.path.dirname(kb.web.__file__))")/static/js/
ls -la $(python3 -c "import kb.web; import os; print(os.path.dirname(kb.web.__file__))")/static/css/
ls -la $(python3 -c "import kb.web; import os; print(os.path.dirname(kb.web.__file__))")/static/templates/
```

Expected: All new directories present with files

- [ ] **Step 5: Test installed package**

```bash
# Initialize and start web server from installed package
localbrain init setup
localbrain web
```

Open browser to `http://localhost:11201/` and verify it works.

- [ ] **Step 6: Cleanup test environment**

```bash
deactivate
rm -rf /tmp/test-localbrain
```

---

### Task 28: Update CHANGELOG

**Files:**
- Modify: `CHANGELOG.md` or create if doesn't exist

- [ ] **Step 1: Add entry for frontend refactor**

```markdown
## [Unreleased]

### Changed
- **Frontend Architecture**: Refactored monolithic 8633-line `index.html` into modular ES-module-based structure
  - Split CSS into `base.css`, `layout.css`, `components.css`
  - Extracted JavaScript into modules: `main.js`, `store.js`, `router.js`, `api.js`, `i18n.js`, `utils.js`
  - Created 17 page components under `js/pages/` with templates in `templates/pages/`
  - Migrated to Vue 3 ESM build (native ES modules, no build tooling required)
  - All existing functionality preserved, no breaking changes
```

- [ ] **Step 2: Commit**

```bash
git add CHANGELOG.md
git commit -m "docs: update CHANGELOG for frontend refactor"
```

---

### Task 29: Final Commit and Summary

**Files:**
- All modified files

- [ ] **Step 1: Review all changes**

```bash
git status
git diff --stat main
```

Expected: Shows all modified and new files

- [ ] **Step 2: Verify line count reduction**

```bash
wc -l kb/web/static/index.html
```

Expected: Significantly reduced from 8633 lines (target: <200 lines)

- [ ] **Step 3: Count new files created**

```bash
find kb/web/static/js -type f | wc -l
find kb/web/static/css -type f | wc -l
find kb/web/static/templates -type f | wc -l
```

Expected: ~20 JS files, 3 CSS files, ~17 template files

- [ ] **Step 4: Create final summary commit (if needed)**

If there are any remaining uncommitted changes:

```bash
git add -A
git commit -m "refactor: complete frontend modularization

- Reduced index.html from 8633 to <200 lines
- Split CSS into 3 files (base, layout, components)
- Extracted JS into 7 core modules + 17 page components
- Created 17 HTML templates for page components
- Migrated to Vue 3 ESM build with native ES modules
- No build tooling required
- All functionality preserved, no breaking changes"
```

- [ ] **Step 5: Create summary document**

Document the refactor results:
- Original index.html: 8633 lines
- New index.html: ~XXX lines
- Files created: XX JS modules, 3 CSS files, 17 templates
- All pages verified working
- Tests passing (if implemented)

---

## Implementation Notes

### Prerequisites

Before starting implementation:
1. Ensure Python 3.8+ is installed
2. Install project dependencies: `pip install -e .`
3. Verify web server runs: `python3 -m kb.cli web`

### Running the Web Server

```bash
# Option 1: Via CLI module
python3 -m kb.cli web

# Option 2: If installed
localbrain web

# Option 3: Direct uvicorn (for development)
cd kb && python3 -m uvicorn web.app:app --reload --port 11201
```

### Troubleshooting

**Issue**: Module not found errors
- **Solution**: Install dependencies: `pip install -e .`

**Issue**: 404 errors for JS/CSS files
- **Solution**: Verify `pyproject.toml` package-data includes `web/static/**/*`

**Issue**: Vue component not loading
- **Solution**: Check browser console for import errors, verify file paths

**Issue**: Template fetch fails
- **Solution**: Ensure FastAPI serves `/static/` correctly, check `kb/web/app.py`

### Key Principles Applied

1. **DRY**: Extracted common utilities, API wrapper, i18n
2. **YAGNI**: No build tooling, no unnecessary abstractions
3. **Separation of Concerns**: CSS/JS/HTML in separate files
4. **Progressive Enhancement**: Pages load lazily via async components
5. **Backward Compatibility**: All existing functionality preserved

---

## Success Criteria

- [ ] index.html reduced to <200 lines
- [ ] All 17 pages migrated to modular structure
- [ ] CSS split into 3 files (base, layout, components)
- [ ] JS split into 7 core modules + 17 page components
- [ ] All pages load without console errors
- [ ] Locale toggle works across all pages
- [ ] Package builds successfully
- [ ] Installed package works correctly
- [ ] Manual verification passed for all pages
- [ ] Tests passing (if implemented)

---

## Estimated Time

- Phase 0 (Scaffolding): 2-3 hours
- Phase 1 (Pilot): 1-2 hours
- Phase 2 (Remaining pages): 4-6 hours
- Phase 3 (Cleanup): 1-2 hours
- **Total**: 8-13 hours

---

## Post-Implementation

After completing this refactor:
1. Monitor for any user-reported issues
2. Consider adding more comprehensive E2E tests
3. Future enhancements can now be done per-page without touching monolith
4. Settings page completion can proceed in separate PR
5. Consider adding TypeScript types (optional, future enhancement)

