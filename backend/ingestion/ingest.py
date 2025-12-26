"""
Ingestion pipeline for GitHub repositories.
Fetches repos, parses code structure, extracts metadata.
"""

import os
import ast
import json
from pathlib import Path
from typing import List, Dict, Any
from git import Repo
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RepoIngester:
    """Handles cloning and parsing GitHub repositories."""

    def __init__(self, data_dir: str = "./data"):
        self.data_dir = Path(data_dir)
        self.repos_dir = self.data_dir / "repos"
        self.metadata_dir = self.data_dir / "metadata"
        self.repos_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_dir.mkdir(parents=True, exist_ok=True)

    def clone_repo(self, repo_url: str, repo_name: str) -> Path:
        """Clone a GitHub repository."""
        repo_path = self.repos_dir / repo_name

        if repo_path.exists():
            logger.info(f"Repository {repo_name} already exists at {repo_path}")
            return repo_path

        logger.info(f"Cloning {repo_url} to {repo_path}")
        Repo.clone_from(repo_url, repo_path)
        return repo_path

    def extract_python_metadata(self, file_path: Path) -> Dict[str, Any]:
        """Extract functions, classes, imports from Python file using abstract syntax tree."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            tree = ast.parse(content)

            functions = []
            classes = []
            imports = []

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    functions.append(
                        {
                            "name": node.name,
                            "line": node.lineno,
                            "args": [arg.arg for arg in node.args.args],
                            "docstring": ast.get_docstring(node),
                        }
                    )
                elif isinstance(node, ast.ClassDef):
                    methods = [
                        n.name for n in node.body if isinstance(n, ast.FunctionDef)
                    ]
                    classes.append(
                        {
                            "name": node.name,
                            "line": node.lineno,
                            "methods": methods,
                            "docstring": ast.get_docstring(node),
                        }
                    )
                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            imports.append(alias.name)
                    else:
                        module = node.module or ""
                        imports.append(module)

            return {
                "functions": functions,
                "classes": classes,
                "imports": list(set(imports)),
                "lines": len(content.splitlines()),
            }
        except Exception as e:
            logger.warning(f"Failed to parse {file_path}: {e}")
            return {"functions": [], "classes": [], "imports": [], "lines": 0}

    def scan_repository(self, repo_path: Path, repo_name: str) -> Dict[str, Any]:
        """Scan repository and extract all metadata."""
        logger.info(f"Scanning repository {repo_name}")

        files_metadata = []

        # Walk through Python files
        for py_file in repo_path.rglob("*.py"):
            if ".git" in str(py_file) or "venv" in str(py_file):
                continue

            relative_path = py_file.relative_to(repo_path)
            metadata = self.extract_python_metadata(py_file)

            files_metadata.append(
                {"path": str(relative_path), "full_path": str(py_file), **metadata}
            )

        # Extract git metadata
        try:
            repo = Repo(repo_path)
            commits = []
            for commit in list(repo.iter_commits())[:10]:  # Last 10 commits
                commits.append(
                    {
                        "sha": commit.hexsha,
                        "author": str(commit.author),
                        "date": commit.committed_datetime.isoformat(),
                        "message": commit.message.strip(),
                    }
                )
        except Exception as e:
            logger.warning(f"Failed to extract git history: {e}")
            commits = []

        repo_metadata = {
            "name": repo_name,
            "path": str(repo_path),
            "files": files_metadata,
            "commits": commits,
            "total_files": len(files_metadata),
            "total_functions": sum(len(f["functions"]) for f in files_metadata),
            "total_classes": sum(len(f["classes"]) for f in files_metadata),
        }

        # Save metadata
        metadata_file = self.metadata_dir / f"{repo_name}.json"
        with open(metadata_file, "w") as f:
            json.dump(repo_metadata, f, indent=2)

        logger.info(f"Saved metadata to {metadata_file}")
        return repo_metadata

    def ingest_repos(self, repo_urls: List[str]) -> List[Dict[str, Any]]:
        """Ingest multiple repositories."""
        results = []

        for url in repo_urls:
            repo_name = url.rstrip("/").split("/")[-1].replace(".git", "")
            try:
                repo_path = self.clone_repo(url, repo_name)
                metadata = self.scan_repository(repo_path, repo_name)
                results.append(metadata)
            except Exception as e:
                logger.error(f"Failed to ingest {url}: {e}")

        return results


def main():
    """Main ingestion script."""
    # Example repos to ingest
    repos = [
        "https://github.com/karpathy/nanochat"
    ]

    ingester = RepoIngester()
    results = ingester.ingest_repos(repos)

    logger.info(f"\n{'='*50}")
    logger.info(f"Ingestion complete. Processed {len(results)} repositories")
    for repo in results:
        logger.info(
            f"  - {repo['name']}: {repo['total_files']} files, "
            f"{repo['total_functions']} functions, {repo['total_classes']} classes"
        )


if __name__ == "__main__":
    main()
