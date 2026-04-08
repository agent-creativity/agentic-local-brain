/**
 * Agentic Local Brain Documentation Layout
 * Shared JavaScript for all documentation pages
 * 
 * Features:
 * - Language toggle (EN/ZH)
 * - Right outline generation with scroll-spy
 * - Sidebar navigation with collapsible sections
 * - Mobile hamburger menu
 * - Code block copy buttons
 * - Smooth scrolling
 */

(function() {
    'use strict';

    // ==========================================================================
    // Configuration
    // ==========================================================================
    
    const CONFIG = {
        STORAGE_KEY_LOCALE: 'doc-locale',
        DEFAULT_LOCALE: 'en',
        SCROLL_OFFSET: 80, // Header height + padding
        SCROLL_SPY_DEBOUNCE: 50,
        ANIMATION_DURATION: 300
    };

    // Navigation translations
    const NAV_TRANSLATIONS = {
        'index.html': { en: 'Home', zh: '首页' },
        'getting-started.html': { en: 'Getting Started', zh: '快速开始' },
        'skill-install.html': { en: 'Skill Installation', zh: 'Skill 安装' },
        'core-concepts.html': { en: 'Core Concepts', zh: '核心概念' },
        'architecture.html': { en: 'Architecture', zh: '系统架构' },
        'configuration.html': { en: 'Configuration', zh: '配置指南' },
        'cli-reference.html': { en: 'CLI Reference', zh: 'CLI 参考' },
        'api-reference.html': { en: 'API Reference', zh: 'API 参考' },
        'roadmap.html': { en: 'Roadmap', zh: '发展路线' },
        'faq.html': { en: 'FAQ', zh: '常见问题' },
        'contact.html': { en: 'Contact', zh: '联系合作' }
    };

    // Static text translations
    const STATIC_TRANSLATIONS = {
        backToApp: { en: '← Back to App', zh: '← 返回应用' },
        outlineTitle: { en: 'On this page', zh: '本页目录' }
    };

    // ==========================================================================
    // DOM Element Cache
    // ==========================================================================

    const DOM = {
        hamburgerBtn: null,
        sidebar: null,
        langToggle: null,
        outlineLinks: null,
        content: null,
        overlay: null
    };

    // ==========================================================================
    // State
    // ==========================================================================

    let state = {
        currentLocale: CONFIG.DEFAULT_LOCALE,
        isSidebarOpen: false,
        headings: []
    };

    // ==========================================================================
    // Initialization
    // ==========================================================================

    /**
     * Initialize the documentation layout
     */
    function init() {
        cacheDOM();
        initLocale();
        initSidebar();
        initOutline();
        initCodeCopy();
        initSmoothScroll();
        initMobileMenu();
        
        // Mark page as initialized
        document.body.classList.add('doc-initialized');
    }

    /**
     * Cache DOM element references
     */
    function cacheDOM() {
        DOM.hamburgerBtn = document.getElementById('hamburgerBtn');
        DOM.sidebar = document.getElementById('docSidebar');
        DOM.langToggle = document.getElementById('langToggle');
        DOM.outlineLinks = document.getElementById('outlineLinks');
        DOM.content = document.querySelector('.doc-content');
        
        // Create sidebar overlay if it doesn't exist
        if (!document.querySelector('.sidebar-overlay')) {
            const overlay = document.createElement('div');
            overlay.className = 'sidebar-overlay';
            overlay.id = 'sidebarOverlay';
            document.body.appendChild(overlay);
            DOM.overlay = overlay;
        } else {
            DOM.overlay = document.querySelector('.sidebar-overlay');
        }
    }

    // ==========================================================================
    // Language Toggle
    // ==========================================================================

    /**
     * Initialize language toggle functionality
     */
    function initLocale() {
        // Load saved locale or use default
        const savedLocale = localStorage.getItem(CONFIG.STORAGE_KEY_LOCALE);
        state.currentLocale = savedLocale || CONFIG.DEFAULT_LOCALE;
        
        // Apply locale
        setLocale(state.currentLocale);
        
        // Bind toggle button
        if (DOM.langToggle) {
            DOM.langToggle.addEventListener('click', toggleLocale);
        }
    }

    /**
     * Set the current locale and update UI
     * @param {string} locale - 'en' or 'zh'
     */
    function setLocale(locale) {
        state.currentLocale = locale;
        
        // Update body class
        document.body.classList.remove('lang-en', 'lang-zh');
        document.body.classList.add(`lang-${locale}`);
        
        // Update toggle button text
        if (DOM.langToggle) {
            DOM.langToggle.textContent = locale === 'en' ? 'EN' : '中文';
        }
        
        // Update html lang attribute
        document.documentElement.lang = locale === 'zh' ? 'zh-CN' : 'en';
        
        // Save preference
        localStorage.setItem(CONFIG.STORAGE_KEY_LOCALE, locale);
        
        // Update navigation language
        updateNavLanguage(locale);
        
        // Update static text
        updateStaticText(locale);
        
        // Rebuild outline for current language
        rebuildOutline();
    }

    /**
     * Update sidebar navigation labels based on locale
     * @param {string} locale - 'en' or 'zh'
     */
    function updateNavLanguage(locale) {
        const navLinks = document.querySelectorAll('.sidebar-nav .nav-link');
        navLinks.forEach(link => {
            const href = link.getAttribute('href');
            // Extract filename from href
            const filename = href.split('/').pop();
            const translation = NAV_TRANSLATIONS[filename];
            if (translation) {
                link.textContent = translation[locale] || translation.en;
            }
        });
    }

    /**
     * Update static text elements based on locale
     * @param {string} locale - 'en' or 'zh'
     */
    function updateStaticText(locale) {
        // Update "Back to App" link
        const backToAppLinks = document.querySelectorAll('.back-to-app');
        backToAppLinks.forEach(link => {
            link.textContent = STATIC_TRANSLATIONS.backToApp[locale];
        });
        
        // Update outline title
        const outlineTitle = document.querySelector('.outline-title');
        if (outlineTitle) {
            outlineTitle.textContent = STATIC_TRANSLATIONS.outlineTitle[locale];
        }
    }

    /**
     * Toggle between English and Chinese
     */
    function toggleLocale() {
        const newLocale = state.currentLocale === 'en' ? 'zh' : 'en';
        setLocale(newLocale);
    }

    // ==========================================================================
    // Sidebar Navigation
    // ==========================================================================

    /**
     * Initialize sidebar navigation
     */
    function initSidebar() {
        // Highlight current page
        highlightCurrentPage();
        
        // Initialize collapsible sections
        initCollapsibleSections();
        
        // Apply initial navigation language
        updateNavLanguage(state.currentLocale);
        
        // Apply initial static text
        updateStaticText(state.currentLocale);
    }

    /**
     * Highlight the current page in the sidebar
     */
    function highlightCurrentPage() {
        const currentPath = window.location.pathname.split('/').pop() || 'index.html';
        const navLinks = document.querySelectorAll('.nav-link');
        
        navLinks.forEach(link => {
            const href = link.getAttribute('href');
            if (href === currentPath || href === `./${currentPath}`) {
                link.classList.add('active');
            }
        });
    }

    /**
     * Initialize collapsible navigation sections
     */
    function initCollapsibleSections() {
        const sections = document.querySelectorAll('.nav-section');
        
        sections.forEach(section => {
            const header = section.querySelector('.nav-section-header');
            
            if (header) {
                // Restore collapsed state from localStorage
                const sectionId = header.textContent.trim();
                const isCollapsed = localStorage.getItem(`nav-section-${sectionId}`) === 'collapsed';
                
                if (isCollapsed) {
                    section.classList.add('collapsed');
                }
                
                // Toggle on click
                header.addEventListener('click', () => {
                    section.classList.toggle('collapsed');
                    
                    // Save state
                    const collapsed = section.classList.contains('collapsed');
                    localStorage.setItem(`nav-section-${sectionId}`, collapsed ? 'collapsed' : 'expanded');
                });
            }
        });
    }

    // ==========================================================================
    // Right Outline Panel
    // ==========================================================================

    /**
     * Initialize the right outline panel
     */
    function initOutline() {
        if (!DOM.outlineLinks) return;
        
        // Build initial outline
        rebuildOutline();
        
        // Setup scroll spy
        initScrollSpy();
    }

    /**
     * Rebuild outline for current language content
     */
    function rebuildOutline() {
        if (!DOM.outlineLinks) return;
        
        // Clear existing outline
        DOM.outlineLinks.innerHTML = '';
        
        // Find active language content
        const langContent = document.querySelector(`[data-lang="${state.currentLocale}"]`);
        if (!langContent) return;
        
        // Get h2 and h3 headings
        const headings = langContent.querySelectorAll('h2, h3');
        state.headings = [];
        
        headings.forEach((heading, index) => {
            // Generate ID if not present
            if (!heading.id) {
                heading.id = generateHeadingId(heading.textContent, index);
            }
            
            // Store heading reference
            state.headings.push({
                id: heading.id,
                level: heading.tagName.toLowerCase(),
                element: heading,
                text: heading.textContent.trim()
            });
            
            // Create outline link
            const link = document.createElement('a');
            link.href = `#${heading.id}`;
            link.className = `outline-link outline-${heading.tagName.toLowerCase()}`;
            link.textContent = heading.textContent.trim();
            link.dataset.target = heading.id;
            
            // Smooth scroll on click
            link.addEventListener('click', (e) => {
                e.preventDefault();
                smoothScrollTo(heading.id);
            });
            
            DOM.outlineLinks.appendChild(link);
        });
        
        // Update scroll spy
        updateScrollSpy();
    }

    /**
     * Generate a heading ID from text
     * @param {string} text - Heading text
     * @param {number} index - Index for uniqueness
     * @returns {string} Generated ID
     */
    function generateHeadingId(text, index) {
        const slug = text
            .toLowerCase()
            .replace(/[^\w\s-]/g, '')
            .replace(/\s+/g, '-')
            .replace(/-+/g, '-')
            .trim();
        return `${slug}-${index}`;
    }

    /**
     * Initialize scroll spy for outline
     */
    function initScrollSpy() {
        let scrollTimeout;
        
        window.addEventListener('scroll', () => {
            clearTimeout(scrollTimeout);
            scrollTimeout = setTimeout(updateScrollSpy, CONFIG.SCROLL_SPY_DEBOUNCE);
        }, { passive: true });
        
        // Initial update
        updateScrollSpy();
    }

    /**
     * Update the active outline link based on scroll position
     */
    function updateScrollSpy() {
        if (!state.headings.length) return;
        
        const scrollPosition = window.scrollY + CONFIG.SCROLL_OFFSET;
        
        // Find the current heading
        let currentHeading = null;
        
        for (let i = state.headings.length - 1; i >= 0; i--) {
            const heading = state.headings[i];
            if (heading.element.offsetTop <= scrollPosition) {
                currentHeading = heading;
                break;
            }
        }
        
        // Update active state
        const outlineLinks = document.querySelectorAll('.outline-link');
        outlineLinks.forEach(link => link.classList.remove('active'));
        
        if (currentHeading) {
            const activeLink = document.querySelector(`.outline-link[data-target="${currentHeading.id}"]`);
            if (activeLink) {
                activeLink.classList.add('active');
            }
        }
    }

    // ==========================================================================
    // Code Block Copy Button
    // ==========================================================================

    /**
     * Initialize copy buttons for code blocks
     */
    function initCodeCopy() {
        const codeBlocks = document.querySelectorAll('pre code');
        
        codeBlocks.forEach(codeBlock => {
            const pre = codeBlock.parentElement;
            
            // Create copy button
            const copyBtn = document.createElement('button');
            copyBtn.className = 'code-copy-btn';
            copyBtn.textContent = 'Copy';
            copyBtn.type = 'button';
            
            // Copy on click
            copyBtn.addEventListener('click', async () => {
                try {
                    await navigator.clipboard.writeText(codeBlock.textContent);
                    
                    // Show feedback
                    copyBtn.textContent = 'Copied!';
                    copyBtn.classList.add('copied');
                    
                    setTimeout(() => {
                        copyBtn.textContent = 'Copy';
                        copyBtn.classList.remove('copied');
                    }, 2000);
                } catch (err) {
                    // Fallback for older browsers
                    const textArea = document.createElement('textarea');
                    textArea.value = codeBlock.textContent;
                    textArea.style.position = 'fixed';
                    textArea.style.left = '-9999px';
                    document.body.appendChild(textArea);
                    textArea.select();
                    
                    try {
                        document.execCommand('copy');
                        copyBtn.textContent = 'Copied!';
                        copyBtn.classList.add('copied');
                        
                        setTimeout(() => {
                            copyBtn.textContent = 'Copy';
                            copyBtn.classList.remove('copied');
                        }, 2000);
                    } catch (e) {
                        copyBtn.textContent = 'Failed';
                        setTimeout(() => {
                            copyBtn.textContent = 'Copy';
                        }, 2000);
                    }
                    
                    document.body.removeChild(textArea);
                }
            });
            
            pre.appendChild(copyBtn);
        });
    }

    // ==========================================================================
    // Smooth Scrolling
    // ==========================================================================

    /**
     * Initialize smooth scrolling for anchor links
     */
    function initSmoothScroll() {
        document.addEventListener('click', (e) => {
            const link = e.target.closest('a[href^="#"]');
            
            if (link) {
                const targetId = link.getAttribute('href').slice(1);
                if (targetId) {
                    e.preventDefault();
                    smoothScrollTo(targetId);
                }
            }
        });
    }

    /**
     * Smooth scroll to an element by ID
     * @param {string} targetId - Target element ID
     */
    function smoothScrollTo(targetId) {
        const target = document.getElementById(targetId);
        
        if (target) {
            const targetPosition = target.offsetTop - CONFIG.SCROLL_OFFSET + 10;
            
            window.scrollTo({
                top: targetPosition,
                behavior: 'smooth'
            });
            
            // Update URL hash without jumping
            history.pushState(null, null, `#${targetId}`);
        }
    }

    // ==========================================================================
    // Mobile Menu
    // ==========================================================================

    /**
     * Initialize mobile hamburger menu
     */
    function initMobileMenu() {
        if (!DOM.hamburgerBtn || !DOM.sidebar) return;
        
        // Toggle sidebar on hamburger click
        DOM.hamburgerBtn.addEventListener('click', toggleSidebar);
        
        // Close sidebar on overlay click
        if (DOM.overlay) {
            DOM.overlay.addEventListener('click', closeSidebar);
        }
        
        // Close sidebar on escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && state.isSidebarOpen) {
                closeSidebar();
            }
        });
        
        // Close sidebar when clicking a link (mobile)
        DOM.sidebar.addEventListener('click', (e) => {
            const link = e.target.closest('a');
            if (link && !link.classList.contains('nav-section-header')) {
                closeSidebar();
            }
        });
    }

    /**
     * Toggle sidebar visibility
     */
    function toggleSidebar() {
        state.isSidebarOpen ? closeSidebar() : openSidebar();
    }

    /**
     * Open the sidebar
     */
    function openSidebar() {
        state.isSidebarOpen = true;
        DOM.sidebar.classList.add('open');
        if (DOM.overlay) DOM.overlay.classList.add('visible');
        document.body.style.overflow = 'hidden';
        
        // Update hamburger icon
        DOM.hamburgerBtn.textContent = '✕';
        DOM.hamburgerBtn.setAttribute('aria-expanded', 'true');
    }

    /**
     * Close the sidebar
     */
    function closeSidebar() {
        state.isSidebarOpen = false;
        DOM.sidebar.classList.remove('open');
        if (DOM.overlay) DOM.overlay.classList.remove('visible');
        document.body.style.overflow = '';
        
        // Update hamburger icon
        DOM.hamburgerBtn.textContent = '☰';
        DOM.hamburgerBtn.setAttribute('aria-expanded', 'false');
    }

    // ==========================================================================
    // Utility Functions
    // ==========================================================================

    /**
     * Debounce a function
     * @param {Function} func - Function to debounce
     * @param {number} wait - Wait time in ms
     * @returns {Function} Debounced function
     */
    function debounce(func, wait) {
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

    // ==========================================================================
    // Keyboard Navigation
    // ==========================================================================

    /**
     * Setup keyboard shortcuts
     */
    function initKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            // Toggle language with Ctrl/Cmd + Shift + L
            if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key.toLowerCase() === 'l') {
                e.preventDefault();
                toggleLocale();
            }
            
            // Toggle sidebar with Ctrl/Cmd + B
            if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'b') {
                e.preventDefault();
                toggleSidebar();
            }
        });
    }

    // ==========================================================================
    // Public API (for external use if needed)
    // ==========================================================================

    window.DocLayout = {
        setLocale,
        toggleLocale,
        openSidebar,
        closeSidebar,
        rebuildOutline
    };

    // ==========================================================================
    // Initialize on DOMContentLoaded
    // ==========================================================================

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
