from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import os

from core.agent import GitHubAgent
from core.retriever import VectorRetriever
from core.neo4j_client import Neo4jClient
from api.routes.context import _context_store

router = APIRouter()
_agent = None


def get_agent():
    global _agent
    if _agent is None:
        retriever = VectorRetriever()
        neo4j_client = Neo4jClient()
        _agent = GitHubAgent(retriever, neo4j_client)
    return _agent


class QueryRequest(BaseModel):
    repo: Optional[str] = None
    question: str
    chat_history: Optional[List] = None


@router.post("/")
async def query(req: QueryRequest):
    """Query repositories using the RAG agent."""

    agent = get_agent()
    question = req.question
    context_info = ""

    if req.repo:
        question = f"In the {req.repo} repository: {question}"
        context_data = _context_store.get(req.repo)
        if context_data:
            if context_data.get("current_file"):
                context_info += f"\n[Current File]: {context_data.get('current_file')}"
            if context_data.get("selected_code"):
                context_info += (
                    f"\n[Selected Code]:\n{context_data.get('selected_code')}"
                )

    result = agent.query(question, req.chat_history or [], context=context_info)
    return {
        "question": req.question,
        "answer": result["answer"],
        "success": result["success"],
        "repo": req.repo,
        "context_used": context_info,
    }
