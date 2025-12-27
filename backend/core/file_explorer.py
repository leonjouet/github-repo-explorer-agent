"""
File system exploration tool for repository navigation.
Provides capabilities to explore directory structure, read files, and search for files.
"""

import os
import logging
from pathlib import Path
from typing import List, Dict, Any
import subprocess

logger = logging.getLogger(__name__)


class FileExplorer:
    """Tool for exploring and navigating repository file systems."""

    def __init__(self, base_path: str = "/app/data/repos"):
        """
        Initialize FileExplorer with a base path for repositories.

        Args:
            base_path: Base directory containing repositories
        """
        self.base_path = Path(base_path)
        self.current_path = self.base_path

    def list_repos(self) -> str:
        """List all available repositories in the base path."""
        try:
            if not self.base_path.exists():
                return f"Base path does not exist: {self.base_path}"

            repos = [
                d.name
                for d in self.base_path.iterdir()
                if d.is_dir() and not d.name.startswith(".")
            ]

            if not repos:
                return f"No repositories found in {self.base_path}"

            output = f"Available repositories in {self.base_path}:\n"
            for repo in sorted(repos):
                output += f"  - {repo}\n"

            logger.debug(f"[TOOL FUNC] list_repos: Found {len(repos)} repositories")
            return output
        except Exception as e:
            logger.exception("list_repos tool error")
            return f"Error listing repositories: {str(e)}"

    def tree_structure(self, repo_name: str, max_depth: int = 3) -> str:
        """
        Get the tree structure of a repository.

        Args:
            repo_name: Name of the repository
            max_depth: Maximum depth to traverse (prevents huge outputs)

        Returns:
            Tree structure as formatted string
        """
        try:
            repo_path = self.base_path / repo_name

            if not repo_path.exists():
                return f"Repository '{repo_name}' not found at {repo_path}"

            logger.debug(
                f"[TOOL FUNC] tree_structure: repo_name='{repo_name}', max_depth={max_depth}"
            )

            output = f"Tree structure of {repo_name}:\n"
            output += self._build_tree(repo_path, "", 0, max_depth)

            logger.debug(f"[TOOL FUNC] tree_structure: Completed")
            return output
        except Exception as e:
            logger.exception("tree_structure tool error")
            return f"Error getting tree structure: {str(e)}"

    def _build_tree(
        self, path: Path, prefix: str = "", current_depth: int = 0, max_depth: int = 3
    ) -> str:
        """Recursively build tree structure representation."""
        if current_depth >= max_depth:
            return ""

        output = ""

        try:
            # Get all items and sort them (directories first, then files)
            items = sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name))

            # Filter out common directories to ignore
            ignore_dirs = {
                ".git",
                "__pycache__",
                ".venv",
                "venv",
                "node_modules",
                ".env",
                ".pytest_cache",
                ".egg-info",
            }
            items = [item for item in items if item.name not in ignore_dirs]

            for i, item in enumerate(items):
                is_last = i == len(items) - 1
                current_prefix = "└── " if is_last else "├── "
                output += f"{prefix}{current_prefix}{item.name}\n"

                if item.is_dir():
                    next_prefix = prefix + ("    " if is_last else "│   ")
                    output += self._build_tree(
                        item, next_prefix, current_depth + 1, max_depth
                    )
        except PermissionError:
            pass

        return output

    def read_file(self, repo_name: str, file_path: str) -> str:
        """
        Read the contents of a file in a repository.

        Args:
            repo_name: Name of the repository
            file_path: Relative path to the file within the repository

        Returns:
            File contents or error message
        """
        try:
            full_path = self.base_path / repo_name / file_path

            # Security check: prevent path traversal attacks
            try:
                full_path.resolve().relative_to((self.base_path / repo_name).resolve())
            except ValueError:
                return f"Access denied: Path traversal attempt detected"

            if not full_path.exists():
                return f"File not found: {file_path}"

            if not full_path.is_file():
                return f"Path is not a file: {file_path}"

            logger.debug(
                f"[TOOL FUNC] read_file: repo_name='{repo_name}', file_path='{file_path}'"
            )

            with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            # Limit output size to prevent excessive content
            max_chars = 10000
            if len(content) > max_chars:
                output = f"File: {file_path}\n"
                output += (
                    f"(Showing first {max_chars} characters of {len(content)} total)\n"
                )
                output += "---\n"
                output += content[:max_chars]
                output += f"\n... (truncated)"
                logger.debug(
                    f"[TOOL FUNC] read_file: Content truncated (original length: {len(content)})"
                )
            else:
                output = f"File: {file_path}\n---\n{content}"
                logger.debug(f"[TOOL FUNC] read_file: Read {len(content)} characters")

            return output
        except Exception as e:
            logger.exception("read_file tool error")
            return f"Error reading file: {str(e)}"

    def search_files(self, repo_name: str, query: str, file_pattern: str = "*") -> str:
        """
        Search for files in a repository by name or pattern.

        Args:
            repo_name: Name of the repository
            query: Search query (case-insensitive substring match)
            file_pattern: File pattern to match (e.g., "*.py")

        Returns:
            List of matching files
        """
        try:
            repo_path = self.base_path / repo_name

            if not repo_path.exists():
                return f"Repository '{repo_name}' not found"

            logger.debug(
                f"[TOOL FUNC] search_files: repo_name='{repo_name}', query='{query}', pattern='{file_pattern}'"
            )

            matching_files = []
            query_lower = query.lower()

            # Ignore certain directories
            ignore_dirs = {
                ".git",
                "__pycache__",
                ".venv",
                "venv",
                "node_modules",
                ".egg-info",
            }

            for root, dirs, files in os.walk(repo_path):
                # Remove ignored directories from dirs in-place to prevent traversal
                dirs[:] = [d for d in dirs if d not in ignore_dirs]

                for file in files:
                    # Check if file matches pattern
                    if not self._matches_pattern(file, file_pattern):
                        continue

                    # Check if file matches query
                    if query_lower in file.lower():
                        full_path = Path(root) / file
                        relative_path = full_path.relative_to(repo_path)
                        matching_files.append(str(relative_path))

            # Limit results
            max_results = 50
            if len(matching_files) > max_results:
                output = f"Found {len(matching_files)} files matching '{query}' in {repo_name}.\n"
                output += f"Showing first {max_results} results:\n"
                output += "\n".join(matching_files[:max_results])
                output += f"\n... and {len(matching_files) - max_results} more"
                logger.debug(
                    f"[TOOL FUNC] search_files: Found {len(matching_files)} files (showing {max_results})"
                )
            else:
                if matching_files:
                    output = f"Found {len(matching_files)} files matching '{query}' in {repo_name}:\n"
                    output += "\n".join(matching_files)
                    logger.debug(
                        f"[TOOL FUNC] search_files: Found {len(matching_files)} files"
                    )
                else:
                    output = f"No files found matching '{query}' in {repo_name}"
                    logger.debug(f"[TOOL FUNC] search_files: No matches found")

            return output
        except Exception as e:
            logger.exception("search_files tool error")
            return f"Error searching files: {str(e)}"

    def _matches_pattern(self, filename: str, pattern: str) -> bool:
        """Check if a filename matches a pattern (simple implementation)."""
        import fnmatch

        return fnmatch.fnmatch(filename, pattern)

    def file_exists(self, repo_name: str, file_path: str) -> str:
        """Check if a file exists in a repository."""
        try:
            full_path = self.base_path / repo_name / file_path

            if full_path.exists():
                if full_path.is_file():
                    size = full_path.stat().st_size
                    return f"File exists: {file_path} ({size} bytes)"
                else:
                    return f"Path exists but is a directory: {file_path}"
            else:
                return f"File does not exist: {file_path}"
        except Exception as e:
            logger.exception("file_exists tool error")
            return f"Error checking file: {str(e)}"

    def list_directory(self, repo_name: str, dir_path: str = ".") -> str:
        """
        List files and directories in a specific directory.

        Args:
            repo_name: Name of the repository
            dir_path: Path to the directory (relative to repo root)

        Returns:
            List of items in the directory
        """
        try:
            repo_path = self.base_path / repo_name
            target_path = repo_path / dir_path

            # Security check
            try:
                target_path.resolve().relative_to(repo_path.resolve())
            except ValueError:
                return f"Access denied: Path traversal attempt detected"

            if not target_path.exists():
                return f"Directory not found: {dir_path}"

            if not target_path.is_dir():
                return f"Path is not a directory: {dir_path}"

            logger.debug(
                f"[TOOL FUNC] list_directory: repo_name='{repo_name}', dir_path='{dir_path}'"
            )

            items = sorted(
                target_path.iterdir(), key=lambda p: (not p.is_dir(), p.name)
            )

            output = f"Contents of {dir_path}:\n"
            for item in items:
                if item.is_dir():
                    output += f"  [DIR]  {item.name}/\n"
                else:
                    size = item.stat().st_size
                    output += f"  [FILE] {item.name} ({size} bytes)\n"

            logger.debug(f"[TOOL FUNC] list_directory: Found {len(items)} items")
            return output
        except Exception as e:
            logger.exception("list_directory tool error")
            return f"Error listing directory: {str(e)}"
