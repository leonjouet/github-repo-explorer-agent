from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import repos, query, health, graph

app = FastAPI(title="GitHub RAG Agent", version="1.0.0")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, tags=["health"])
app.include_router(repos.router, prefix="/repos", tags=["repos"])
app.include_router(query.router, prefix="/query", tags=["query"])
app.include_router(graph.router, prefix="/graph", tags=["graph"])


@app.get("/")
async def root():
    return {
        "name": "GitHub RAG Agent API",
        "version": "1.0.0",
        "docs": "/docs"
    }
