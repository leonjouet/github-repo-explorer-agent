"""
LangGraph agent with RAG + Graph + Git tools.
Orchestrates retrieval and reasoning over GitHub repositories.
"""

from typing import Any, Dict, List, Optional
import os
import logging
from datetime import datetime

from langchain_core.tools import Tool, StructuredTool
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.callbacks import BaseCallbackHandler
from langgraph.prebuilt import create_react_agent

from .retriever import VectorRetriever
from .neo4j_client import Neo4jClient
from .graph_query_tool import DynamicGraphQueryTool
from .file_explorer import FileExplorer

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logging.getLogger("langgraph").setLevel(logging.DEBUG)
logger = logging.getLogger(__name__)


class AgentDebugCallbackHandler(BaseCallbackHandler):
    """Callback handler for logging LLM and tool interactions."""

    def on_llm_start(
        self, serialized: Dict[str, Any], prompts: List[str], **kwargs: Any
    ) -> None:
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
            if hasattr(response, "generations"):
                for i, gen_list in enumerate(response.generations, 1):
                    for j, gen in enumerate(gen_list, 1):
                        content = gen.text if hasattr(gen, "text") else str(gen)
                        logger.info(f"--- Generation {i}.{j} ---")
                        # Use larger truncation for better readability
                        max_chars = 1000
                        if len(content) > max_chars:
                            logger.info(
                                content[:max_chars]
                                + f"\n... (truncated, total length: {len(content)} chars)"
                            )
                        else:
                            logger.info(content)
        except Exception as e:
            logger.error(f"Error logging LLM response: {e}")
        logger.info("=" * 80)

    def on_llm_error(self, error: Exception, **kwargs: Any) -> None:
        """Log LLM errors."""
        logger.error(f"[LLM ERROR] {str(error)}")

    def on_tool_start(
        self, serialized: Dict[str, Any], input_str: str, **kwargs: Any
    ) -> None:
        """Log when a tool is called."""
        logger.info("+" * 80)
        logger.info(f"[TOOL CALL] {datetime.now().isoformat()}")
        logger.info(f"Tool: {serialized.get('name', 'unknown')}")
        logger.info(f"Description: {serialized.get('description', 'N/A')}")
        logger.info(
            f"Input: {input_str[:500] + ('...' if len(input_str) > 500 else '')}"
        )

    def on_tool_end(self, output: str, **kwargs: Any) -> None:
        """Log tool results."""
        logger.info("[TOOL RESULT]")
        # Use larger truncation for readability (20KB limit)
        max_chars = 20000
        if len(output) > max_chars:
            logger.info(output[:max_chars])
            logger.info(f"... (truncated, total length: {len(output)} chars)")
        else:
            logger.info(output)
        logger.info("+" * 80)

    def on_tool_error(self, error: Exception, **kwargs: Any) -> None:
        """Log tool errors."""
        logger.error(f"[TOOL ERROR] {str(error)}")


# Tool argument schemas
class SearchCodeArgs(BaseModel):
    query: str = Field(..., description="Search query for the code index")


class DynamicCypherQueryArgs(BaseModel):
    cypher_query: str = Field(
        ...,
        description="Cypher query to execute against the Neo4j database. Use the schema provided to generate valid queries.",
    )


class FileExplorerArgs(BaseModel):
    action: str = Field(
        ...,
        description="Action to perform: 'list_repos', 'tree', 'read_file', 'search_files', 'list_directory'",
    )
    repo_name: str = Field(
        "",
        description="Name of the repository (required for all actions except 'list_repos')",
    )
    file_path: str = Field(
        "",
        description="Path to file or directory (required for 'read_file', 'search_files', 'list_directory')",
    )
    query: str = Field("", description="Search query (required for 'search_files')")
    file_pattern: str = Field(
        "*", description="File pattern for search (optional, defaults to '*')"
    )
    max_depth: int = Field(
        3, description="Maximum depth for tree structure (optional, defaults to 3)"
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
        self.graph_query_tool = DynamicGraphQueryTool(neo4j_client)
        self.file_explorer = FileExplorer()

        self.llm = ChatOpenAI(
            model=model,
            temperature=0,
            api_key=os.environ.get("OPENAI_API_KEY"),
            base_url=os.environ.get("OPENAI_API_BASE_URL"),
        )
        self.tools = self._create_tools()
        self.agent_app = self._create_agent()

    def _create_tools(self) -> List[Tool]:
        """Create agent tools for RAG, dynamic graph queries, and file exploration."""

        def search_code(query: str) -> str:
            """Search for code snippets in the vector database."""
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

                # Log the full result
                logger.info(f"\n[SEARCH_CODE OUTPUT]")
                logger.info(f"Query: {query}")
                logger.info(f"Results:")
                max_log_chars = 30000
                if len(output) > max_log_chars:
                    logger.info(output[:max_log_chars])
                    logger.info(f"\n... (truncated, total length: {len(output)} chars)")
                else:
                    logger.info(output)
                logger.info("[END SEARCH_CODE OUTPUT]\n")

                return output
            except Exception as e:
                logger.exception("search_code tool error")
                return f"Error in search_code: {str(e)}"

        def dynamic_cypher_query(cypher_query: str) -> str:
            """
            Execute a dynamic Cypher query against the Neo4j graph database.

            The Neo4j graph contains nodes for Repository, File, Function, Class, Module, and Commit,
            with relationships for CONTAINS, DEFINES, CALLS, IMPORTS, and HAS_COMMIT.

            Use this tool when you need to query the knowledge graph. Generate Cypher queries
            based on the graph schema provided by the get_graph_schema tool.
            """
            try:
                logger.debug("[TOOL FUNC] dynamic_cypher_query: Executing")
                result = self.graph_query_tool.execute_query(cypher_query)

                # Log the full result
                logger.info(f"\n[CYPHER QUERY OUTPUT]")
                logger.info(f"Query: {cypher_query}")
                logger.info(f"Result:")
                max_log_chars = 30000
                if len(result) > max_log_chars:
                    logger.info(result[:max_log_chars])
                    logger.info(f"\n... (truncated, total length: {len(result)} chars)")
                else:
                    logger.info(result)
                logger.info("[END CYPHER QUERY OUTPUT]\n")

                return result
            except Exception as e:
                logger.exception("dynamic_cypher_query tool error")
                return f"Error executing query: {str(e)}"

        def get_graph_schema() -> str:
            """
            Get the Neo4j graph database schema and structure.

            Returns a detailed description of nodes, relationships, and properties
            to help generate valid Cypher queries for dynamic_cypher_query tool.
            """
            try:
                logger.debug(
                    "[TOOL FUNC] get_graph_schema: Retrieving schema description"
                )
                schema = self.graph_query_tool.get_schema_info()
                logger.debug("[TOOL FUNC] get_graph_schema: Schema retrieved")
                return schema
            except Exception as e:
                logger.exception("get_graph_schema tool error")
                return f"Error retrieving schema: {str(e)}"

        def list_graph_repositories() -> str:
            """List all repositories available in the Neo4j graph database."""
            try:
                logger.debug(
                    "[TOOL FUNC] list_graph_repositories: Listing repositories"
                )
                return self.graph_query_tool.list_repositories()
            except Exception as e:
                logger.exception("list_graph_repositories tool error")
                return f"Error listing repositories: {str(e)}"

        def file_explorer(
            action: str,
            repo_name: str = "",
            file_path: str = "",
            query: str = "",
            file_pattern: str = "*",
            max_depth: int = 3,
        ) -> str:
            """
            Explore repository file systems. Supports multiple actions:
            - 'list_repos': List all available repositories
            - 'tree': Get directory tree structure of a repository
            - 'read_file': Read contents of a file
            - 'search_files': Search for files by name or pattern
            - 'list_directory': List files in a specific directory
            """
            try:
                action = action.lower().strip()
                result = ""

                if action == "list_repos":
                    logger.debug("[TOOL FUNC] file_explorer: list_repos")
                    result = self.file_explorer.list_repos()

                elif action == "tree":
                    logger.debug(f"[TOOL FUNC] file_explorer: tree for {repo_name}")
                    result = self.file_explorer.tree_structure(repo_name, max_depth)

                elif action == "read_file":
                    logger.debug(
                        f"[TOOL FUNC] file_explorer: read_file {repo_name}/{file_path}"
                    )
                    result = self.file_explorer.read_file(repo_name, file_path)

                elif action == "search_files":
                    logger.debug(
                        f"[TOOL FUNC] file_explorer: search_files in {repo_name}"
                    )
                    result = self.file_explorer.search_files(
                        repo_name, query, file_pattern
                    )

                elif action == "list_directory":
                    logger.debug(
                        f"[TOOL FUNC] file_explorer: list_directory {repo_name}/{file_path}"
                    )
                    result = self.file_explorer.list_directory(repo_name, file_path)

                else:
                    result = f"Unknown action: {action}. Valid actions are: list_repos, tree, read_file, search_files, list_directory"

                # Log the full result
                logger.info(f"\n[FILE_EXPLORER OUTPUT - Action: {action}]")
                max_log_chars = 30000
                if len(result) > max_log_chars:
                    logger.info(result[:max_log_chars])
                    logger.info(f"\n... (truncated, total length: {len(result)} chars)")
                else:
                    logger.info(result)
                logger.info("[END FILE_EXPLORER OUTPUT]\n")

                return result
            except Exception as e:
                logger.exception("file_explorer tool error")
                return f"Error in file_explorer: {str(e)}"

        # Create Tool objects
        search_code_tool = Tool.from_function(
            name="search_code",
            description="Search for code snippets in the vector database by semantic similarity.",
            func=search_code,
            args_schema=SearchCodeArgs,
            return_direct=False,
        )

        dynamic_cypher_tool = Tool.from_function(
            name="dynamic_cypher_query",
            description="Execute a dynamic Cypher query against the Neo4j graph database. Use get_graph_schema tool first to understand the graph structure.",
            func=dynamic_cypher_query,
            args_schema=DynamicCypherQueryArgs,
            return_direct=False,
        )

        get_schema_tool = Tool.from_function(
            name="get_graph_schema",
            description="Get the Neo4j graph database schema including node types, properties, and relationships. Use this before dynamic_cypher_query.",
            func=get_graph_schema,
            return_direct=False,
        )

        list_repos_tool = Tool.from_function(
            name="list_graph_repositories",
            description="List all repositories available in the Neo4j graph database with their statistics.",
            func=list_graph_repositories,
            return_direct=False,
        )

        file_explorer_tool = StructuredTool.from_function(
            name="file_explorer",
            description="Explore repository file systems. Can list repositories, show directory trees, read files, search for files, or list directory contents.",
            func=file_explorer,
            args_schema=FileExplorerArgs,
        )

        return [
            search_code_tool,
            dynamic_cypher_tool,
            get_schema_tool,
            list_repos_tool,
            file_explorer_tool,
        ]

    def _create_agent(self):
        """
        Create a LangGraph agent using the prebuilt ReAct-style tool-using agent.
        This agent can loop LLM <-> tools multiple times until a final answer.
        """
        self.system_prompt = (
            "You are a GitHub code analysis assistant. "
            "You have tools to search a codebase via RAG, execute dynamic Cypher queries against a Neo4j graph database, "
            "and explore repository file systems. "
            "\n\nWhen answering questions about code structure or relationships, use the dynamic_cypher_query tool with queries "
            "that you generate based on the graph schema (get the schema with get_graph_schema tool first). "
            "For file exploration and reading, use the file_explorer tool. "
            "For semantic code search, use search_code. "
            "\n\nBe concise and focus on what is most relevant for understanding the repository."
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

            logger.info(
                f"[AGENT RESPONSE] Generated answer (length: {len(str(answer))} chars)"
            )
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
