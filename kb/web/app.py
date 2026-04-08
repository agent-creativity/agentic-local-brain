"""
FastAPI web application for Knowledge Base.

Main application module that sets up the FastAPI app with all routes,
middleware, and static file serving.
"""
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

app = FastAPI(
    title="Knowledge Base",
    description="Knowledge Base Management API",
    version="1.0.0",
    docs_url="/api/docs",  # Swagger UI moved to /api/docs to free /docs for documentation site
    redoc_url="/api/redoc"  # ReDoc moved to /api/redoc
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
from kb.web.routes import dashboard, graph, items, recommendations, search, settings, tags, topics

app.include_router(dashboard.router, prefix="/api", tags=["Dashboard"])
app.include_router(graph.router, prefix="/api", tags=["Graph"])
app.include_router(items.router, prefix="/api", tags=["Items"])
app.include_router(search.router, prefix="/api", tags=["Search"])
app.include_router(settings.router, prefix="/api", tags=["Settings"])
app.include_router(tags.router, prefix="/api", tags=["Tags"])
app.include_router(topics.router, prefix="/api", tags=["Topics"])
app.include_router(recommendations.router, prefix="/api", tags=["Recommendations"])

# Static files directory
static_dir = Path(__file__).parent / "static"

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
    index_file = static_dir / "index.html"
    if index_file.exists():
        return index_file.read_text(encoding="utf-8")
    
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
