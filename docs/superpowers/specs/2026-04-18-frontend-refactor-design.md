# Frontend Refactor Design — `kb/web/static`

**Date**: 2026-04-18
**Status**: Draft for review
**Scope**: Restructure the monolithic `kb/web/static/index.html` (8633 lines) into a modular, ES-module-based layout with page-level Vue components. Behavior MUST be preserved 1:1 — no UI redesign, no new features.

## 1. Background

`kb/web/static/index.html` currently inlines:

- ~640 lines of HTML scaffold (head, sidebar)
- ~2865 lines of CSS in a single `<style>` block (lines 644–3509)
- ~3000 lines of HTML templates for 17 pages (lines 3537–6317)
- ~2315 lines of Vue 3 JS in a single `<script>` block (lines 6318–8633)

There is also a standalone `backup.html` (434 lines) and three doc pages under `docs/`. Backend routes are already split per feature under `kb/web/routes/`.

The file size makes navigation, code review, and conflict resolution painful and prevents Claude Code from holding the whole UI in context. A monolith of this size also blocks the planned settings-page completion and the broader testing initiative.

## 2. Goals

- Split `index.html` into modular files organized by concern (CSS / JS / HTML templates / page components).
- Keep current behavior, routing semantics, locale, theme, API surface, and visual design **identical**.
- No build tooling required (`pip install` remains the only setup step). Use native ES modules via `<script type="module">`.
- Allow page-level isolation: each page can be edited, reviewed, and tested independently.
- Establish a Playwright smoke test baseline as part of the migration so each page-migration commit is self-verifiable.

## 3. Non-Goals

- Visual redesign or UX changes.
- New features (e.g. completing the system-settings page, adding new tabs) — handled in separate follow-up specs.
- Build-toolchain introduction (Vite / SFC / TS) — explicitly ruled out by the user.
- Changes to backend API or `kb/web/routes/*`.
- Refactor of `kb/web/static/docs/*.html` (independent static docs).
- Rewrite of standalone `backup.html` (the in-app `currentPage === 'backup'` view IS in scope; the standalone page stays as-is unless trivially mergeable in Phase 2 batch E).

## 4. Target Architecture

### 4.1 Directory Layout

```
kb/web/static/
  index.html                     # Shell only (<200 lines): <head>, sidebar, <component :is>, module entry
  vue.esm-browser.prod.js        # Vue 3 ESM build (replaces vue.global.prod.js)
  marked.min.js                  # Unchanged
  backup.html                    # Unchanged in this refactor (separate decision)
  docs/                          # Unchanged
  js/
    main.js                      # createApp + page registry + mount('#app')
    store.js                     # `export const store = reactive({...})` — global state
    router.js                    # Minimal: maps store.currentPage -> async component; supports hash sync (optional)
    api.js                       # fetch wrapper: baseURL, JSON parsing, error normalization
    i18n.js                      # `locale` getter + `t(key)` + translation tables (extracted from current code)
    utils.js                     # formatDate, escapeHtml, debounce, etc.
    pages/
      dashboard.js
      items.js
      items-note.js
      items-bookmark.js
      items-webpage.js
      items-paper.js
      items-email.js
      items-file.js
      tags.js
      graph.js
      topics.js
      timeline.js
      recommendations.js
      wiki.js
      mining.js
      rag.js
      settings.js
      backup.js
  templates/pages/
    dashboard.html
    ... (one .html per page above)
  css/
    base.css                     # Reset, CSS variables, theme (light/dark)
    layout.css                   # Sidebar, page header, main container
    components.css               # .card, .btn, .input, .badge, .tag-pill, .nav-item, etc.
    pages/
      <page>.css                 # Only when a page has unique styles that don't generalize
```

### 4.2 Page Component Pattern

Every page uses the same skeleton:

```js
// js/pages/settings.js
import { store } from '../store.js';
import { api } from '../api.js';
import { t } from '../i18n.js';

const template = await fetch('/static/templates/pages/settings.html').then(r => r.text());

export default {
  name: 'SettingsPage',
  template,
  data() {
    return {
      // page-local reactive state
    };
  },
  computed: {
    store: () => store,
    locale() { return store.locale; },
    t() { return t; },
  },
  methods: {
    // page-local methods (moved from the monolithic root instance)
  },
  async mounted() {
    // page initialization
  },
};
```

Notes:

- Top-level `await` inside ES modules is supported by all evergreen browsers (Chrome ≥89, Firefox ≥89, Safari ≥15) — within our target.
- Each `pages/*.js` is loaded lazily via `defineAsyncComponent(() => import('./pages/xxx.js'))`, so initial bundle stays small.

### 4.3 App Bootstrap

```js
// js/main.js
import { createApp, defineAsyncComponent } from './vue.esm-browser.prod.js';
import { store } from './store.js';
import { t } from './i18n.js';

const pages = {
  dashboard: defineAsyncComponent(() => import('./pages/dashboard.js')),
  items: defineAsyncComponent(() => import('./pages/items.js')),
  // ... one entry per page
  settings: defineAsyncComponent(() => import('./pages/settings.js')),
  backup: defineAsyncComponent(() => import('./pages/backup.js')),
};

const App = {
  setup() { return { store }; },
  computed: {
    currentPageComponent() { return pages[store.currentPage] || pages.dashboard; },
    t() { return t; },
  },
  // The shell template (sidebar + <component :is>) is inlined here OR loaded from
  // /static/templates/app.html. Decision: inline in main.js for simplicity, since
  // the shell is small and rarely changes.
};

createApp(App).mount('#app');
```

### 4.4 Global Store Shape

`store.js` is the single source of truth for cross-page state. Initial fields (extracted from current root instance):

- `locale: 'en' | 'zh'`
- `theme: 'light' | 'dark'`
- `currentPage: string`
- `settings: { ... }` (model + backup + diagnostics caches; populated once, refreshed on demand)
- `user`-level preferences currently kept on root

Page-local state (form drafts, list filters, modal visibility) stays inside the page component's `data()`.

### 4.5 HTML Shell

`index.html` after refactor contains roughly:

- `<head>` with title, meta, CSS `<link>`s in order: `base.css` → `layout.css` → `components.css` → page-specific CSS bundle
- `<body>` with `<div id="app"></div>`
- One `<script type="module" src="/static/js/main.js"></script>` at the bottom

No inline `<style>` or `<script>` blocks. Total target: under 200 lines.

## 5. Migration Plan

Each phase is one or more git commits. Verification gate must pass before moving to the next phase. Rollback = `git revert`.

### Phase 0 — Scaffolding (no behavioral change)

1. Create `js/`, `css/`, `templates/pages/` directories.
2. Replace `vue.global.prod.js` reference with `vue.esm-browser.prod.js` (download official build, commit locally).
3. Extract `<style>` block → split into `base.css` / `layout.css` / `components.css` based on selector grouping. Keep `index.html` unchanged otherwise; instead reference these via `<link>`. Verify visual diff = none.
4. Extract pure helpers from the `<script>` block into `i18n.js`, `api.js`, `utils.js`, `store.js`. The root Vue instance stays in `index.html` and imports from these via `<script type="module">`. **No page extraction yet.**
5. **Audit**: grep for `this.$root`, `window.<x>`, and any cross-page references; convert to `store.<x>` or shimmed `window.store = store` if needed.
6. **Verification gate**: open every page in the sidebar, switch locale & theme, perform one main action per page. Console MUST be error-free.

### Phase 1 — Pilot: migrate `settings` page

1. Cut `<div v-if="currentPage === 'settings'">…</div>` block to `templates/pages/settings.html`.
2. Move related `data()` fields, `computed`, and `methods` into `js/pages/settings.js`.
3. Register settings as the first `defineAsyncComponent` in `main.js`.
4. Keep the rest of pages still living in the root instance (transitional duality is fine for one phase).
5. **Verification gate**: settings page renders, all save/load actions work, locale + theme still toggle correctly.

### Phase 2 — Sweep remaining pages (one batch per commit)

- **Batch A**: `dashboard`
- **Batch B**: `items` + `items-note` + `items-bookmark` + `items-webpage` + `items-paper` + `items-email` + `items-file` (share the most state — migrate together)
- **Batch C**: `tags`, `graph`, `topics`, `timeline`, `recommendations`
- **Batch D**: `wiki`, `mining`, `rag`
- **Batch E**: `backup` (in-app view). Decide at this point whether to fold standalone `backup.html` into the SPA — default: leave standalone untouched.

After each batch: run the verification gate from Phase 1, plus regression-check pages from earlier batches and untouched pages.

### Phase 3 — Cleanup

1. Reduce `index.html` to the bare shell described in §4.5.
2. Remove any leftover inline blocks, `window.store` shim, or transitional code.
3. Add `kb/web/static/README.md` describing the directory convention and how to add a new page.
4. Update root `README.md` frontend section.

## 6. Risk Register

| Risk | Mitigation |
|---|---|
| Hidden `this.$root.<x>` calls break after extraction | Phase 0 grep audit; replace with `store.<x>`; smoke-test all pages before Phase 1 |
| `fetch('/static/templates/...')` 404 in deployed packaging | Verify `MANIFEST.in` / `pyproject.toml` package-data includes new dirs; add a Phase 0 packaging dry-run (`python -m build && pip install dist/*.whl`) |
| `vue.esm-browser.prod.js` differs from `vue.global.prod.js` (no global `Vue` symbol) | Bootstrap via ESM imports only; remove any code that references `window.Vue` |
| Top-level `await` unsupported in target browser | Documented requirement: Chrome 89+/Firefox 89+/Safari 15+. Reject older browsers. |
| Page methods cross-call each other | Migrate co-dependent pages in the same batch (Batch B groups `items*`) |
| CSS specificity collapse when split across files | Preserve original selector order via `<link>` ordering: base → layout → components → page |
| Translation table size in `i18n.js` becomes large | Acceptable; can split per-page later if it grows. Out of scope for this refactor. |
| Caching causes stale templates after edit | Add `?v=<git-short-hash>` query string in `<link>` / `import` URLs (Phase 3 polish) |

## 7. Verification & Testing Strategy

### 7.1 Per-batch manual verification (mandatory)

For every migration commit:

1. `python -m kb.web` (or whatever the existing run command is — confirm in plan).
2. Open `http://localhost:<port>/` in browser.
3. Console: zero errors, zero red 404s in network tab.
4. Sidebar: every entry navigates and renders.
5. Locale toggle (en ⇄ zh): persists across page changes.
6. Theme toggle (light ⇄ dark): persists across page changes.
7. For each migrated page: perform one primary action (save, search, open detail, etc.).
8. `git diff` review: confirm only mechanical splits, no semantic edits.

### 7.2 Playwright smoke baseline (in scope)

Add `tests/web/test_smoke.py` using Playwright. Must include:

- **Server fixture**: starts `kb/web` on a free port, tears down after.
- **Per-page smoke test** (parametrized over the 17 pages): navigate via sidebar, assert page header text matches expected i18n key, assert no console errors, assert no failed network requests.
- **Locale switch test**: toggle to `zh`, navigate dashboard, assert Chinese title; toggle back.
- **Theme switch test**: toggle to dark, assert `body` class or CSS var changed; toggle back.

These tests run after each Phase-2 batch and gate the final Phase-3 cleanup. Deeper E2E coverage (form submissions, edit flows, backup save) belongs to the separate "comprehensive web testing" follow-up project — not this spec.

### 7.3 Packaging verification

At the end of Phase 3:

- `python -m build`
- `pip install dist/*.whl` in a clean venv
- Run the installed package and re-run the Playwright smoke suite against it. All new directories (`js/`, `css/`, `templates/`) must be present in the wheel.

## 8. Rollout

- Single PR per phase (or per batch within Phase 2). Each PR independently mergeable.
- No feature flag — refactor is mechanical and verified per phase.
- Version bump: PATCH (no behavior change). Mention in CHANGELOG that frontend layout was modularized.

## 9. Open Questions (to resolve in implementation plan)

1. Confirm the run command for the dev server (best guess: `python -m kb.web` or via an entry script under `scripts/`). The plan must verify and document it.
2. Confirm `pyproject.toml` package-data globs include `kb/web/static/**` recursively (or need explicit additions for new subdirs).
3. Choose whether to fold `backup.html` into the SPA in Batch E (default: no, document the rationale).
4. Decide on cache-busting strategy for module/CSS files (default: `?v=<short-hash>` injected at build/serve time, or rely on FastAPI ETag).

## 10. Follow-up Specs (out of scope for this one)

- **Settings page completion** — implement the Tab redesign already described in `SETTINGS_UI_REDESIGN.md` and add missing config sections (storage paths, search, ingestion, UI preferences). Builds on this refactor.
- **Comprehensive web testing** — full E2E coverage with Playwright across all interactive flows.
