"""
Neo4j graph loader for repository metadata.
Creates nodes and relationships for files, functions, classes, commits.
"""

import json
from pathlib import Path
from typing import Dict, Any, List
import logging
from core.neo4j_client import Neo4jClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GraphLoader:
    """Load repository metadata into Neo4j graph."""

    def __init__(self, neo4j_client: Neo4jClient):
        self.neo4j = neo4j_client
        self._create_constraints()

    def _create_constraints(self):
        """Create uniqueness constraints and indexes to prevent duplicate nodes."""
        constraints = [
            "CREATE CONSTRAINT repo_name IF NOT EXISTS FOR (r:Repository) REQUIRE r.name IS UNIQUE",
            "CREATE CONSTRAINT file_path IF NOT EXISTS FOR (f:File) REQUIRE f.full_path IS UNIQUE",
            "CREATE CONSTRAINT func_id IF NOT EXISTS FOR (fn:Function) REQUIRE fn.id IS UNIQUE",
            "CREATE CONSTRAINT class_id IF NOT EXISTS FOR (c:Class) REQUIRE c.id IS UNIQUE",
            "CREATE CONSTRAINT commit_sha IF NOT EXISTS FOR (cm:Commit) REQUIRE cm.sha IS UNIQUE",
        ]

        for constraint in constraints:
            try:
                self.neo4j.run(constraint)
            except Exception as e:
                logger.debug(f"Constraint may already exist: {e}")

    def load_repository(self, metadata: Dict[str, Any]):
        """Load complete repository into graph."""
        repo_name = metadata["name"]
        logger.info(f"Loading repository {repo_name} into graph")

        # Create repository node
        self.neo4j.run(
            "MERGE (r:Repository {name: $name}) "
            "SET r.path = $path, r.total_files = $files, "
            "r.total_functions = $funcs, r.total_classes = $classes",
            {
                "name": repo_name,
                "path": metadata["path"],
                "files": metadata["total_files"],
                "funcs": metadata["total_functions"],
                "classes": metadata["total_classes"],
            },
        )

        # Load files, functions, classes
        for file_info in metadata["files"]:
            self._load_file(repo_name, file_info)

        # Load commits
        for commit in metadata.get("commits", []):
            self._load_commit(repo_name, commit)

        logger.info(f"Successfully loaded {repo_name} into graph")

    def _load_file(self, repo_name: str, file_info: Dict[str, Any]):
        """Load file node and its functions/classes."""
        file_path = file_info["path"]
        full_path = file_info["full_path"]

        # Create file node
        self.neo4j.run(
            "MATCH (r:Repository {name: $repo}) "
            "MERGE (f:File {full_path: $full_path}) "
            "SET f.path = $path, f.lines = $lines "
            "MERGE (r)-[:CONTAINS]->(f)",
            {
                "repo": repo_name,
                "path": file_path,
                "full_path": full_path,
                "lines": file_info.get("lines", 0),
            },
        )

        # Load functions
        for func in file_info.get("functions", []):
            self._load_function(full_path, func)

        # Load classes
        for cls in file_info.get("classes", []):
            self._load_class(full_path, cls)

        # Load imports
        for imp in file_info.get("imports", []):
            self._load_import(full_path, imp)

    def _load_function(self, file_path: str, func: Dict[str, Any]):
        """Load function node."""
        func_id = f"{file_path}::{func['name']}::{func['line']}"

        self.neo4j.run(
            "MATCH (f:File {full_path: $file}) "
            "MERGE (fn:Function {id: $id}) "
            "SET fn.name = $name, fn.line = $line, "
            "fn.args = $args, fn.docstring = $doc "
            "MERGE (f)-[:DEFINES]->(fn)",
            {
                "file": file_path,
                "id": func_id,
                "name": func["name"],
                "line": func["line"],
                "args": func.get("args", []),
                "doc": func.get("docstring", ""),
            },
        )

    def _load_class(self, file_path: str, cls: Dict[str, Any]):
        """Load class node and its methods."""
        class_id = f"{file_path}::{cls['name']}::{cls['line']}"

        self.neo4j.run(
            "MATCH (f:File {full_path: $file}) "
            "MERGE (c:Class {id: $id}) "
            "SET c.name = $name, c.line = $line, "
            "c.methods = $methods, c.docstring = $doc "
            "MERGE (f)-[:DEFINES]->(c)",
            {
                "file": file_path,
                "id": class_id,
                "name": cls["name"],
                "line": cls["line"],
                "methods": cls.get("methods", []),
                "doc": cls.get("docstring", ""),
            },
        )

    def _load_import(self, file_path: str, import_name: str):
        """Load import relationship."""
        self.neo4j.run(
            "MATCH (f:File {full_path: $file}) "
            "MERGE (dep:Module {name: $import}) "
            "MERGE (f)-[:IMPORTS]->(dep)",
            {"file": file_path, "import": import_name},
        )

    def _load_commit(self, repo_name: str, commit: Dict[str, Any]):
        """Load commit node."""
        self.neo4j.run(
            "MATCH (r:Repository {name: $repo}) "
            "MERGE (c:Commit {sha: $sha}) "
            "SET c.author = $author, c.date = $date, c.message = $msg "
            "MERGE (r)-[:HAS_COMMIT]->(c)",
            {
                "repo": repo_name,
                "sha": commit["sha"],
                "author": commit["author"],
                "date": commit["date"],
                "msg": commit["message"],
            },
        )

    def load_from_metadata_dir(self, metadata_dir: str = "./data/metadata"):
        """Load all repositories from metadata directory."""
        metadata_path = Path(metadata_dir)

        for json_file in metadata_path.glob("*.json"):
            logger.info(f"Loading {json_file.name}")
            with open(json_file, "r") as f:
                metadata = json.load(f)
            self.load_repository(metadata)


def main():
    """Load all ingested repos into Neo4j."""
    from .neo4j_client import Neo4jClient

    client = Neo4jClient()
    loader = GraphLoader(client)
    loader.load_from_metadata_dir()
    client.close()
    logger.info("Graph loading complete")


if __name__ == "__main__":
    main()
