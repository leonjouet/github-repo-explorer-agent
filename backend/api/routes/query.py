from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, List
import os

from core.agent import GitHubAgent
from core.retriever import VectorRetriever
from core.neo4j_client import Neo4jClient

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

    # Add repo context to question if specified
    question = req.question
    if req.repo:
        question = f"In the {req.repo} repository: {question}"

    result = agent.query(question, req.chat_history or [])

    return {
        "question": req.question,
        "answer": result["answer"],
        "success": result["success"],
        "repo": req.repo,
    }
