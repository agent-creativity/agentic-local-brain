"""
FastAPI web application for Knowledge Base.

Main application module that sets up the FastAPI app with all routes,
middleware, and static file serving.
"""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    # Startup: Initialize backup scheduler
    try:
        from kb.scheduler.backup_scheduler import init_scheduler
        from kb.config import Config
        config = Config()
        init_scheduler(config)
        import logging
        logging.getLogger(__name__).info("Backup scheduler initialized")
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Failed to initialize backup scheduler: {e}")

    yield

    # Shutdown: Stop scheduler and cleanup
    try:
        from kb.scheduler.backup_scheduler import stop_scheduler
        stop_scheduler()
        import logging
        logging.getLogger(__name__).info("Backup scheduler stopped")
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Failed to stop backup scheduler: {e}")

    from kb.web import dependencies
    if dependencies._sqlite_storage_instance is not None:
        try:
            dependencies._sqlite_storage_instance.close()
            dependencies._sqlite_storage_instance = None
        except Exception:
            pass
    if dependencies._chroma_storage_instance is not None:
        try:
            dependencies._chroma_storage_instance.close()
            dependencies._chroma_storage_instance = None
        except Exception:
            pass
    if dependencies._pipeline_instance is not None:
        dependencies._pipeline_instance = None
    if dependencies._conversation_manager_instance is not None:
        dependencies._conversation_manager_instance = None


app = FastAPI(
    title="Knowledge Base",
    description="Knowledge Base Management API",
    version="1.0.0",
    docs_url="/api/docs",  # Swagger UI moved to /api/docs to free /docs for documentation site
    redoc_url="/api/redoc",  # ReDoc moved to /api/redoc
    lifespan=lifespan
)

# CORS middleware for cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
from kb.web.routes import backup, dashboard, graph, items, mining, recommendations, search, settings, tags, topics, wiki

app.include_router(backup.router, prefix="/api", tags=["Backup"])
app.include_router(dashboard.router, prefix="/api", tags=["Dashboard"])
app.include_router(graph.router, prefix="/api", tags=["Graph"])
app.include_router(items.router, prefix="/api", tags=["Items"])
app.include_router(mining.router, prefix="/api", tags=["Mining"])
app.include_router(search.router, prefix="/api", tags=["Search"])
app.include_router(settings.router, prefix="/api", tags=["Settings"])
app.include_router(tags.router, prefix="/api", tags=["Tags"])
app.include_router(topics.router, prefix="/api", tags=["Topics"])
app.include_router(recommendations.router, prefix="/api", tags=["Recommendations"])
app.include_router(wiki.router, prefix="/api", tags=["Wiki"])

# Static files directory
static_dir = Path(__file__).parent / "static"

# Cache index.html content at module load
_index_html_cache = None


def _get_index_html():
    """Get cached index.html content."""
    global _index_html_cache
    if _index_html_cache is None:
        index_file = static_dir / "index.html"
        if index_file.exists():
            _index_html_cache = index_file.read_text(encoding="utf-8")
    return _index_html_cache

# Mount docs static files first (before /static) so /docs route is captured here
# The html=True enables serving index.html automatically for directory requests
docs_dir = static_dir / "docs"
if docs_dir.exists():
    from fastapi.staticfiles import StaticFiles
    app.mount("/docs", StaticFiles(directory=str(docs_dir), html=True), name="docs")

# Mount static files if directory exists
if static_dir.exists():
    from fastapi.staticfiles import StaticFiles
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/", response_class=HTMLResponse)
async def root():
    """
    Root route serves the frontend index.html or API welcome page.
    
    Returns:
        HTML content - either the frontend index.html or a simple welcome page.
    """
    html_content = _get_index_html()
    if html_content:
        return html_content
    
    return """<!DOCTYPE html>
<html>
<head>
    <title>Knowledge Base API</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 800px;
            margin: 50px auto;
            padding: 20px;
            background: #f5f5f5;
        }
        .container {
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        h1 { color: #333; }
        a { color: #0066cc; }
        .endpoint { 
            background: #f8f9fa; 
            padding: 10px; 
            margin: 5px 0; 
            border-radius: 4px;
            font-family: monospace;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Knowledge Base API</h1>
        <p>Welcome to the Knowledge Base Management API.</p>
        <h2>Documentation</h2>
        <p>
            <a href="/api/docs">Interactive API Documentation (Swagger UI)</a><br>
            <a href="/api/redoc">Alternative API Documentation (ReDoc)</a>
        </p>
        <h2>Available Endpoints</h2>
        <div class="endpoint">GET /api/stats - Knowledge base statistics</div>
        <div class="endpoint">GET /api/recent - Recent items</div>
        <div class="endpoint">GET /api/items - List items</div>
        <div class="endpoint">GET /api/items/{id} - Get item</div>
        <div class="endpoint">PUT /api/items/{id} - Update item</div>
        <div class="endpoint">DELETE /api/items/{id} - Delete item</div>
        <div class="endpoint">GET /api/tags - List tags</div>
        <div class="endpoint">GET /api/tags/{name}/items - Get items by tag</div>
        <div class="endpoint">POST /api/tags/merge - Merge tags</div>
        <div class="endpoint">DELETE /api/tags/{name} - Delete tag</div>
        <div class="endpoint">GET /api/search?q=... - Keyword search</div>
        <div class="endpoint">POST /api/search/semantic - Semantic search</div>
        <div class="endpoint">POST /api/rag - RAG query</div>
    </div>
</body>
</html>"""


@app.get("/health")
async def health_check():
    """
    Health check endpoint.
    
    Returns:
        Dict with status "ok".
    """
    return {"status": "ok"}
