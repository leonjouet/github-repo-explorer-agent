#!/usr/bin/env python3
"""
Bootstrap script: Ingests repos, builds vector index, and loads graph.
This is not included into the app api to be able to run it separately (e.g., in a Docker container).
"""
import sys
import os
import argparse
import json
import logging

# Add /app to path (for Docker container environment)
sys.path.insert(0, "/app")

from ingest import RepoIngester
from core.retriever import VectorRetriever
from core.graph_loader import GraphLoader
from core.neo4j_client import Neo4jClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    """Run complete bootstrap pipeline."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Bootstrap GitHub RAG Agent with repositories"
    )
    parser.add_argument("repos", nargs="*", help="GitHub repository URLs to ingest")
    args = parser.parse_args()
    logger.info("GitHub RAG Agent - Bootstrap Pipeline")

    if args.repos:
        repos = args.repos
        logger.info(f"Ingesting repositories from command line: {repos}")
    else:
        repos = [
            "https://github.com/karpathy/nanochat",
        ]
        logger.info(f"No repos specified, using defaults: {repos}")

    # Step 1: Ingest repositories
    logger.info("\n[1/3] Ingesting repositories...")

    ingester = RepoIngester(data_dir="/app/data")
    results = ingester.ingest_repos(repos)
    logger.info(f"Ingested {len(results)} repositories")

    # Step 2: Build vector index
    logger.info("\n[2/3] Building vector index...")
    retriever = VectorRetriever(persist_dir="/app/data/chroma")

    for metadata_file in os.listdir("/app/data/metadata"):
        if metadata_file.endswith(".json"):
            with open(f"/app/data/metadata/{metadata_file}", "r") as f:
                metadata = json.load(f)
            retriever.add_repo_to_index(metadata)

    logger.info("Vector index built")

    # Step 3: Load graph database on Neo4j
    logger.info("\n[3/3] Loading Neo4j graph...")
    neo4j = Neo4jClient()
    loader = GraphLoader(neo4j)
    loader.load_from_metadata_dir("/app/data/metadata")
    neo4j.close()
    logger.info("Graph loaded")
    logger.info("Repositories loaded successfully")


if __name__ == "__main__":
    main()
