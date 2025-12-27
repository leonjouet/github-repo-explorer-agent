"""
Dynamic Neo4j query tool.
Generates and executes Cypher queries based on the graph database schema.
Allows the LLM to dynamically query the knowledge graph without hardcoded queries.
"""

import logging
from typing import Dict, Any, List
import re
import os

from .neo4j_client import Neo4jClient

logger = logging.getLogger(__name__)


class DynamicGraphQueryTool:
    """Tool for generating and executing dynamic Cypher queries against Neo4j."""

    # Graph schema description for the LLM
    SCHEMA_DESCRIPTION = """
Neo4j Graph Database Schema:

NODES:
- Repository: name (unique), path, total_files, total_functions, total_classes
  Properties: name, path, total_files, total_functions, total_classes
  
- File: full_path (unique), path, lines
  Properties: full_path, path, lines
  
- Function: id (unique), name, line, args, docstring
  Properties: id, name, line, args (list), docstring
  
- Class: id (unique), name, line, methods, docstring
  Properties: id, name, line, methods (list), docstring
  
- Module: name (unique)
  Properties: name (external dependency)
  
- Commit: sha (unique), author, date, message
  Properties: sha, author, date, message

RELATIONSHIPS:
- Repository -[:CONTAINS]-> File: Repository contains files
- File -[:DEFINES]-> Function: File defines functions
- File -[:DEFINES]-> Class: File defines classes
- Function -[:CALLS]-> Function: Function calls another function
- Class -[:DEFINES]-> Function: Class defines methods
- File -[:IMPORTS]-> Module: File imports dependencies
- Repository -[:HAS_COMMIT]-> Commit: Repository has commits

COMMON QUERIES YOU CAN GENERATE:
1. Find all files in a repository:
   MATCH (r:Repository {name: 'repo_name'})-[:CONTAINS]->(f:File) RETURN f.path

2. Find functions in a file:
   MATCH (f:File {full_path: 'path/to/file.py'})-[:DEFINES]->(fn:Function) RETURN fn.name, fn.line

3. Find all functions in a repository:
   MATCH (r:Repository {name: 'repo_name'})-[:CONTAINS]->(f:File)-[:DEFINES]->(fn:Function) RETURN fn.name, f.path

4. Find functions that call a specific function:
   MATCH (caller:Function)-[:CALLS]->(callee:Function {name: 'function_name'}) RETURN caller.name

5. Find dependencies of a repository:
   MATCH (r:Repository {name: 'repo_name'})-[:CONTAINS]->(f:File)-[:IMPORTS]->(dep:Module) RETURN DISTINCT dep.name

6. Find commits in a repository:
   MATCH (r:Repository {name: 'repo_name'})-[:HAS_COMMIT]->(c:Commit) RETURN c.message, c.author, c.date

You MUST use the actual Cypher query language syntax and ensure the query is valid Neo4j Cypher code.
Return only the Cypher query without any markdown formatting or code blocks.
"""

    def __init__(self, neo4j_client: Neo4jClient):
        """
        Initialize the dynamic query tool with optional LLM for query generation.

        Args:
            neo4j_client: Neo4jClient instance for executing queries
        """
        self.neo4j = neo4j_client

        # Initialize LLM for query generation
        try:
            from langchain_openai import ChatOpenAI

            self.llm = ChatOpenAI(
                model="gpt-4.1",
                temperature=0,
                api_key=os.environ.get("OPENAI_API_KEY"),
                base_url=os.environ.get("OPENAI_API_BASE_URL"),
            )
        except Exception as e:
            logger.warning(f"Failed to initialize LLM for query generation: {e}")
            self.llm = None

    # Query are generated in the tool itself to guarantee execution
    # Otherwise the agent may generate queries and return queries that are not executed
    def query_from_natural_language(
        self, natural_language_question: str, max_results: int = 100
    ) -> str:
        """
        High-level method: Takes a natural language question and returns results.
        This GUARANTEES execution because it generates the query internally.

        Args:
            natural_language_question: Natural language question about the codebase
            max_results: Maximum number of results to return

        Returns:
            Query results formatted as a string
        """
        if not self.llm:
            return "Error: LLM not initialized. Cannot generate Cypher queries."

        try:
            logger.info(
                f"[GRAPH TOOL] Generating Cypher query from: {natural_language_question[:100]}"
            )

            # Step 1: Generate Cypher query using LLM
            schema = self.get_schema_info()
            prompt = f"""You are a Neo4j Cypher query expert. Based on the schema provided, generate a valid Cypher query to answer the user's question.
            SCHEMA:
            {schema}

            USER QUESTION: {natural_language_question}

            INSTRUCTIONS:
            - Generate ONLY a valid Cypher query
            - Do NOT include explanations, markdown formatting, or code blocks
            - Ensure the query is syntactically correct Neo4j Cypher
            - Return the raw query only

            Cypher query:"""

            query_response = self.llm.invoke(prompt)
            cypher_query = query_response.content.strip()

            # Clean the query
            cypher_query = self._clean_query(cypher_query)
            logger.info(f"[GRAPH TOOL] Generated query: {cypher_query[:200]}")

            # Step 2: Execute the query
            results = self.execute_query(cypher_query, max_results)
            logger.info(
                f"[GRAPH TOOL] Query execution complete. Result length: {len(results)}"
            )

            return results

        except Exception as e:
            error_msg = str(e)
            logger.exception(
                f"[GRAPH TOOL] Error in query_from_natural_language: {error_msg}"
            )
            return f"Error generating and executing query: {error_msg}"

    def get_schema_info(self) -> str:
        """
        Get the schema description for the LLM.
        This should be provided to the agent to help it generate valid queries.
        """
        return self.SCHEMA_DESCRIPTION

    def execute_query(self, cypher_query: str, max_results: int = 100) -> str:
        """
        Execute a Cypher query against the Neo4j database.

        Args:
            cypher_query: The Cypher query to execute (should be generated by LLM)
            max_results: Maximum number of results to return

        Returns:
            Query results formatted as a string
        """
        try:
            # Validate and sanitize the query
            if not cypher_query or not isinstance(cypher_query, str):
                return "Error: Invalid query. Query must be a non-empty string."

            # Clean up the query (remove markdown code blocks if present)
            cypher_query = self._clean_query(cypher_query)

            logger.debug(f"[TOOL FUNC] execute_query: Executing Cypher query")
            logger.debug(
                f"Query: {cypher_query[:300]}{'...' if len(cypher_query) > 300 else ''}"
            )

            # Execute the query
            results = self.neo4j.run(cypher_query)

            if not results:
                logger.debug("[TOOL FUNC] execute_query: No results found")
                return "Query executed successfully but returned no results."

            # Format results
            output = self._format_results(results, max_results)
            logger.debug(f"[TOOL FUNC] execute_query: Found {len(results)} results")

            return output
        except Exception as e:
            error_msg = str(e)
            logger.exception("execute_query tool error")
            logger.error(f"[TOOL FUNC] execute_query: Error - {error_msg}")
            return f"Error executing query: {error_msg}"

    def _clean_query(self, query: str) -> str:
        """
        Clean up the query by removing markdown code blocks and extra whitespace.

        Args:
            query: Raw query string potentially with markdown formatting

        Returns:
            Cleaned query string
        """
        # Remove markdown code blocks
        query = re.sub(r"^```(?:cypher)?\s*", "", query)
        query = re.sub(r"\s*```$", "", query)

        # Strip whitespace
        query = query.strip()

        return query

    def _format_results(
        self, results: List[Dict[str, Any]], max_results: int = 100
    ) -> str:
        """
        Format query results for display.

        Args:
            results: List of result dictionaries from Neo4j
            max_results: Maximum results to display

        Returns:
            Formatted string representation of results
        """
        if not results:
            return "No results found."

        output = f"Query returned {len(results)} result(s):\n"
        output += "=" * 80 + "\n"

        # Limit results
        displayed_results = results[:max_results]

        for i, record in enumerate(displayed_results, 1):
            output += f"\nResult {i}:\n"
            for key, value in record.items():
                # Format the value
                if isinstance(value, list):
                    value_str = f"[{', '.join(str(v) for v in value)}]"
                elif isinstance(value, dict):
                    value_str = str(value)
                else:
                    value_str = str(value)

                output += f"  {key}: {value_str}\n"

        if len(results) > max_results:
            output += f"\n... and {len(results) - max_results} more results (limited to {max_results})"

        return output

    def validate_query(self, cypher_query: str) -> str:
        """
        Validate a Cypher query without executing it.
        Note: This is a basic validation. Full validation requires execution.

        Args:
            cypher_query: The Cypher query to validate

        Returns:
            Validation result message
        """
        try:
            cypher_query = self._clean_query(cypher_query)

            # Basic checks
            if not cypher_query:
                return "Error: Empty query"

            if not any(
                keyword in cypher_query.upper()
                for keyword in ["MATCH", "CREATE", "MERGE", "DELETE"]
            ):
                return "Error: Query must start with a Cypher operation keyword (MATCH, CREATE, MERGE, DELETE)"

            # Try to execute with EXPLAIN to validate syntax
            explain_query = f"EXPLAIN {cypher_query}"
            try:
                self.neo4j.run(explain_query)
                return "Query syntax is valid."
            except Exception as e:
                # If EXPLAIN fails, try direct execution to get better error
                try:
                    self.neo4j.run(cypher_query)
                    return "Query syntax is valid."
                except Exception as exec_error:
                    return f"Query validation error: {str(exec_error)}"
        except Exception as e:
            return f"Validation error: {str(e)}"

    def list_repositories(self) -> str:
        """List all repositories in the graph database."""
        try:
            logger.debug("[TOOL FUNC] list_repositories: Querying all repositories")

            query = "MATCH (r:Repository) RETURN r.name as name, r.total_files as files, r.total_functions as functions, r.total_classes as classes"
            results = self.neo4j.run(query)

            if not results:
                return "No repositories found in the database."

            output = f"Found {len(results)} repository(ies):\n"
            for record in results:
                output += f"  - {record['name']}: {record['files']} files, {record['functions']} functions, {record['classes']} classes\n"

            logger.debug(
                f"[TOOL FUNC] list_repositories: Found {len(results)} repositories"
            )
            return output
        except Exception as e:
            logger.exception("list_repositories tool error")
            return f"Error listing repositories: {str(e)}"

    def get_repository_info(self, repo_name: str) -> str:
        """Get detailed information about a specific repository."""
        try:
            logger.debug(f"[TOOL FUNC] get_repository_info: repo_name='{repo_name}'")

            query = f"""
            MATCH (r:Repository {{name: '{repo_name}'}})
            OPTIONAL MATCH (r)-[:CONTAINS]->(f:File)
            OPTIONAL MATCH (r)-[:HAS_COMMIT]->(c:Commit)
            RETURN 
              r.name as name,
              r.path as path,
              r.total_files as total_files,
              r.total_functions as total_functions,
              r.total_classes as total_classes,
              count(DISTINCT f) as actual_files,
              count(DISTINCT c) as commits
            """

            results = self.neo4j.run(query)

            if not results:
                return f"Repository '{repo_name}' not found."

            record = results[0]
            output = f"Repository: {record['name']}\n"
            output += f"  Path: {record['path']}\n"
            output += f"  Total Files: {record['total_files']}\n"
            output += f"  Total Functions: {record['total_functions']}\n"
            output += f"  Total Classes: {record['total_classes']}\n"
            output += f"  Commits: {record['commits']}\n"

            logger.debug(
                f"[TOOL FUNC] get_repository_info: Retrieved info for '{repo_name}'"
            )
            return output
        except Exception as e:
            logger.exception("get_repository_info tool error")
            return f"Error getting repository info: {str(e)}"
