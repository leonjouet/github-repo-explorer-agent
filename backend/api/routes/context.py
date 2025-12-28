"""
Context management routes for dynamic user navigation.
Stores and retrieves context about the current file and selected code.
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

router = APIRouter()

# In-memory context storage (session-based, keyed by repo)
_context_store = {}


class ContextData(BaseModel):
    """User context for code navigation and selections."""

    current_file: Optional[str] = None  # e.g., "src/core/agent.py"
    current_file_content: Optional[str] = None  # Full file content
    selected_code: Optional[str] = None  # Selected code snippet
    selected_code_file: Optional[str] = None  # File containing selected code


class SetContextRequest(BaseModel):
    """Request to set context for a repository."""

    repo: str
    context: ContextData


@router.post("/set")
async def set_context(req: SetContextRequest):
    """Store context for a repository."""
    _context_store[req.repo] = req.context.dict()
    return {"success": True, "repo": req.repo, "message": "Context updated"}


@router.get("/{repo}")
async def get_context(repo: str):
    """Retrieve context for a repository."""
    context = _context_store.get(repo)
    if not context:
        return {"success": False, "repo": repo, "message": "No context found"}
    return {"success": True, "repo": repo, "context": context}


@router.delete("/{repo}")
async def clear_context(repo: str):
    """Clear context for a repository."""
    if repo in _context_store:
        del _context_store[repo]
    return {"success": True, "repo": repo, "message": "Context cleared"}
