"""
LangGraph agent with RAG + Graph + Git tools.
Orchestrates retrieval and reasoning over GitHub repositories.
"""

from typing import Any, Dict, List, Optional
import os
import logging
import json
from datetime import datetime

from langchain_core.tools import Tool
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.callbacks import BaseCallbackHandler
from langgraph.prebuilt import create_react_agent

from .retriever import VectorRetriever
from .neo4j_client import Neo4jClient

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logging.getLogger("langgraph").setLevel(logging.DEBUG)
logger = logging.getLogger(__name__)


class AgentDebugCallbackHandler(BaseCallbackHandler):
    """Callback handler for logging LLM and tool interactions."""

    def on_llm_start(self, serialized: Dict[str, Any], prompts: List[str], **kwargs: Any) -> None:
        """Log when LLM is called."""
        logger.info("=" * 80)
        logger.info(f"[LLM CALL] {datetime.now().isoformat()}")
        logger.info(f"Model: {serialized.get('name', 'unknown')}")
        logger.info(f"Number of prompts: {len(prompts)}")
        for i, prompt in enumerate(prompts, 1):
            logger.info(f"--- Prompt {i} ---")
            logger.info(prompt[:500] + ("..." if len(prompt) > 500 else ""))

    def on_llm_end(self, response: Any, **kwargs: Any) -> None:
        """Log when LLM returns a response."""
        logger.info("[LLM RESPONSE]")
        try:
            if hasattr(response, 'generations'):
                for i, gen_list in enumerate(response.generations, 1):
                    for j, gen in enumerate(gen_list, 1):
                        content = gen.text if hasattr(gen, 'text') else str(gen)
                        logger.info(f"--- Generation {i}.{j} ---")
                        # Use larger truncation for better readability
                        max_chars = 1000
                        if len(content) > max_chars:
                            logger.info(content[:max_chars] + f"\n... (truncated, total length: {len(content)} chars)")
                        else:
                            logger.info(content)
        except Exception as e:
            logger.error(f"Error logging LLM response: {e}")
        logger.info("=" * 80)

    def on_llm_error(self, error: Exception, **kwargs: Any) -> None:
        """Log LLM errors."""
        logger.error(f"[LLM ERROR] {str(error)}")

    def on_tool_start(self, serialized: Dict[str, Any], input_str: str, **kwargs: Any) -> None:
        """Log when a tool is called."""
        logger.info("+" * 80)
        logger.info(f"[TOOL CALL] {datetime.now().isoformat()}")
        logger.info(f"Tool: {serialized.get('name', 'unknown')}")
        logger.info(f"Description: {serialized.get('description', 'N/A')}")
        logger.info(f"Input: {input_str[:500] + ('...' if len(input_str) > 500 else '')}")

    def on_tool_end(self, output: str, **kwargs: Any) -> None:
        """Log tool results."""
        logger.info("[TOOL RESULT]")
        # Use larger truncation for readability
        max_chars = 5000
        if len(output) > max_chars:
            logger.info(output[:max_chars] + f"\n... (truncated, total length: {len(output)} chars)")
        else:
            logger.info(output)
        logger.info("+" * 80)

    def on_tool_error(self, error: Exception, **kwargs: Any) -> None:
        """Log tool errors."""
        logger.error(f"[TOOL ERROR] {str(error)}")


# Tool argument schemas
class SearchCodeArgs(BaseModel):
    query: str = Field(..., description="Search query for the code index")


class GetRepoInfoArgs(BaseModel):
    repo_name: str = Field(..., description="Name of the repository")


class FindFunctionCallsArgs(BaseModel):
    function_name: str = Field(
        ..., description="Name of the function to inspect callers for"
    )


# GitHub Agent
class GitHubAgent:
    """LangGraph-based agent for answering questions about GitHub repos."""

    def __init__(
        self,
        retriever: VectorRetriever,
        neo4j_client: Neo4jClient,
        model: str = "gpt-4.1",
    ):
        self.retriever = retriever
        self.neo4j = neo4j_client

        self.llm = ChatOpenAI(
            model=model,
            temperature=0,
            api_key=os.environ.get("OPENAI_API_KEY"),
            base_url=os.environ.get("OPENAI_API_BASE_URL"),
        )
        self.tools = self._create_tools()
        self.agent_app = self._create_agent()

    def _create_tools(self) -> List[Tool]:
        """Create agent tools for RAG and graph operations."""

        def search_code(query: str) -> str:
            """Search for code snippets."""
            try:
                logger.debug(f"[TOOL FUNC] search_code: query='{query}'")
                results = self.retriever.query(query, k=3)
                if not results:
                    logger.debug("[TOOL FUNC] search_code: No results found")
                    return "No relevant code found."

                output = ""
                for i, result in enumerate(results, 1):
                    meta = result["metadata"]
                    output += f"File: {meta.get('repo')}/{meta.get('file')}\n"
                    output += f"{result['text'][:200]}\n---\n"

                logger.debug(f"[TOOL FUNC] search_code: Found {len(results)} results")
                return output
            except Exception as e:
                logger.exception("search_code tool error")
                return f"Error in search_code: {str(e)}"

        def get_repo_info(repo_name: str) -> str:
            """Get repository file structure."""
            try:
                logger.debug(f"[TOOL FUNC] get_repo_info: repo_name='{repo_name}'")
                cypher = f"""
                MATCH (r:Repository {{name: '{repo_name}'}})-[:CONTAINS]->(f:File)
                RETURN f.path as file
                """
                records = self.neo4j.run(cypher)

                if not records:
                    logger.debug(f"[TOOL FUNC] get_repo_info: Repository '{repo_name}' not found")
                    return f"Repository '{repo_name}' not found."

                files = [r["file"] for r in records]
                logger.debug(f"[TOOL FUNC] get_repo_info: Found {len(files)} files")
                return f"Files in {repo_name}:\n" + "\n".join(files)
            except Exception as e:
                logger.exception("get_repo_info tool error")
                return f"Error in get_repo_info: {str(e)}"

        def find_functions(repo_name: str) -> str:
            """Find functions defined in a repository."""
            try:
                logger.debug(f"[TOOL FUNC] find_functions: repo_name='{repo_name}'")
                cypher = f"""
                MATCH (r:Repository {{name: '{repo_name}'}})-[:CONTAINS]->(f:File)
                MATCH (f)-[:DEFINES]->(func:Function)
                RETURN f.path as file, func.name as function
                """
                records = self.neo4j.run(cypher)

                if not records:
                    logger.debug(f"[TOOL FUNC] find_functions: No functions found in '{repo_name}'")
                    return f"No functions found in '{repo_name}'."

                output = f"Functions in {repo_name}:\n"
                for r in records:
                    output += f"  - {r['function']} in {r['file']}\n"
                logger.debug(f"[TOOL FUNC] find_functions: Found {len(records)} functions")
                return output
            except Exception as e:
                logger.exception("find_functions tool error")
                return f"Error in find_functions: {str(e)}"

        def find_function_calls(function_name: str) -> str:
            """Find what functions call a specific function."""
            try:
                logger.debug(f"[TOOL FUNC] find_function_calls: function_name='{function_name}'")
                cypher = f"""
                MATCH (caller:Function)-[:CALLS]->(callee:Function {{name: '{function_name}'}})
                RETURN caller.name as caller, callee.name as callee
                """
                records = self.neo4j.run(cypher)

                if not records:
                    logger.debug(f"[TOOL FUNC] find_function_calls: No calls to '{function_name}' found")
                    return f"No calls to function '{function_name}' found."

                output = f"Functions calling '{function_name}':\n"
                for r in records:
                    output += f"  - {r['caller']}\n"
                logger.debug(f"[TOOL FUNC] find_function_calls: Found {len(records)} callers")
                return output
            except Exception as e:
                logger.exception("find_function_calls tool error")
                return f"Error in find_function_calls: {str(e)}"

        def find_dependencies(repo_name: str) -> str:
            """Find import dependencies for a repository."""
            try:
                logger.debug(f"[TOOL FUNC] find_dependencies: repo_name='{repo_name}'")
                cypher = f"""
                MATCH (r:Repository {{name: '{repo_name}'}})-[:CONTAINS]->(f:File)
                MATCH (f)-[:IMPORTS]->(dep)
                RETURN DISTINCT dep.name as dependency, count(f) as usage_count
                ORDER BY usage_count DESC
                """
                records = self.neo4j.run(cypher)

                if not records:
                    logger.debug(f"[TOOL FUNC] find_dependencies: No dependencies found for '{repo_name}'")
                    return f"No dependencies found for '{repo_name}'."

                output = f"Dependencies in {repo_name}:\n"
                for r in records:
                    output += f"  - {r['dependency']} (used {r['usage_count']} times)\n"
                logger.debug(f"[TOOL FUNC] find_dependencies: Found {len(records)} dependencies")
                return output
            except Exception as e:
                logger.exception("find_dependencies tool error")
                return f"Error in find_dependencies: {str(e)}"

        search_code_tool = Tool.from_function(
            name="search_code",
            description="Search for code snippets in the vector database.",
            func=search_code,
            args_schema=SearchCodeArgs,
            return_direct=False,
        )
        get_repo_info_tool = Tool.from_function(
            name="get_repo_info",
            description="Get repository file structure.",
            func=get_repo_info,
            args_schema=GetRepoInfoArgs,
            return_direct=False,
        )
        find_functions_tool = Tool.from_function(
            name="find_functions",
            description="Find functions defined in a repository.",
            func=find_functions,
            args_schema=GetRepoInfoArgs,
            return_direct=False,
        )
        find_function_calls_tool = Tool.from_function(
            name="find_function_calls",
            description="Find functions that call a specific function.",
            func=find_function_calls,
            args_schema=FindFunctionCallsArgs,
            return_direct=False,
        )
        find_dependencies_tool = Tool.from_function(
            name="find_dependencies",
            description="Find import dependencies for a repository.",
            func=find_dependencies,
            args_schema=GetRepoInfoArgs,
            return_direct=False,
        )

        return [
            search_code_tool,
            get_repo_info_tool,
            find_functions_tool,
            find_function_calls_tool,
            find_dependencies_tool,
        ]

    def _create_agent(self):
        """
        Create a LangGraph agent using the prebuilt ReAct-style tool-using agent.
        This agent can loop LLM <-> tools multiple times until a final answer.
        """
        self.system_prompt = (
            "You are a GitHub code analysis assistant. "
            "You have tools to search a codebase via RAG and explore a Neo4j graph. "
            "Use the tools when they help you answer the user's question. "
            "If no tool is necessary, answer directly. "
            "Be concise and focus on what is most relevant for understanding the repository."
        )

        # Add debug callback to LLM for detailed logging
        debug_handler = AgentDebugCallbackHandler()
        self.llm.callbacks = [debug_handler]

        app = create_react_agent(self.llm, self.tools)
        return app

    def query(
        self,
        question: str,
        chat_history: Optional[List[Dict[str, str]]] = None,
        system_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Process a question using the LangGraph agent.

        chat_history: list of dicts like:
            [{"role": "user"|"assistant", "content": "..."}]

        system_prompt: string to use as system-level instruction for the agent.
        """
        try:
            logger.info("=" * 100)
            logger.info(f"[AGENT QUERY] Started at {datetime.now().isoformat()}")
            logger.info(f"Question: {question}")
            if chat_history:
                logger.info(f"Chat history: {len(chat_history)} messages")

            messages: List[HumanMessage | AIMessage | Dict[str, str]] = []

            # 1. Inject system prompt if provided
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})

            # 2. Add chat history
            if chat_history:
                for msg in chat_history:
                    role = msg.get("role")
                    content = msg.get("content", "")

                    if role == "user":
                        messages.append(HumanMessage(content=content))
                    else:
                        messages.append(AIMessage(content=content))

            # 3. Add new user question
            messages.append(HumanMessage(content=question))

            # 4. Run through LangGraph workflow
            logger.debug("--- Incoming Messages ---")
            for i, m in enumerate(messages, 1):
                logger.debug(f"Message {i}: {str(m)[:200]}")

            result_state = self.agent_app.invoke({"messages": messages})

            logger.debug("--- Final State ---")
            for i, m in enumerate(result_state["messages"], 1):
                logger.debug(f"Message {i}: {str(m)[:200]}")

            # 5. Last message is the final answer
            final_msg = result_state["messages"][-1]
            answer = getattr(final_msg, "content", final_msg)

            logger.info(f"[AGENT RESPONSE] Generated answer (length: {len(str(answer))} chars)")
            logger.info(f"[AGENT QUERY] Completed at {datetime.now().isoformat()}")
            logger.info("=" * 100)

            return {
                "answer": answer,
                "success": True,
            }

        except Exception as e:
            error_msg = str(e)
            logger.exception("GitHubAgent query error")
            logger.error(f"[AGENT ERROR] {error_msg}")
            logger.info("=" * 100)
            return {
                "answer": f"Error processing question: {error_msg}",
                "success": False,
            }
