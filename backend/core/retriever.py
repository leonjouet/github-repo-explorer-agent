"""
Enhanced vector retriever with OpenAI embeddings and ChromaDB.
Handles document chunking, embedding, and semantic search.
"""

import os
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings
from openai import OpenAI
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VectorRetriever:
    """Semantic retrieval using OpenAI embeddings and ChromaDB."""

    def __init__(
        self,
        collection_name: str = "github_code",
        persist_dir: str = "./data/chroma",
        embedding_model: str = "text-embedding-3-large",
    ):
        self.embedding_model = embedding_model
        self.openai_client = OpenAI(
            api_key=os.environ.get("OPENAI_API_KEY"),
            base_url=os.environ.get("OPENAI_API_BASE_URL"),
        )
        self.client = chromadb.Client(
            Settings(persist_directory=persist_dir, anonymized_telemetry=False)
        )
        try:
            self.collection = self.client.get_collection(collection_name)
            logger.info(f"Loaded existing collection '{collection_name}'")
        except Exception:
            self.collection = self.client.create_collection(
                collection_name, metadata={"hnsw:space": "cosine"}
            )
            logger.info(f"Created new collection '{collection_name}'")

    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Get OpenAI embeddings for a list of texts."""
        # Filter out empty strings and ensure valid input
        valid_texts = [text.strip() if text else " " for text in texts]
        # Replace empty strings with a space to avoid API errors
        valid_texts = [text if text else " " for text in valid_texts]

        response = self.openai_client.embeddings.create(
            model=self.embedding_model, input=valid_texts
        )
        return [item.embedding for item in response.data]

    def chunk_code(
        self, content: str, chunk_size: int = 1000, overlap: int = 200
    ) -> List[str]:
        """Chunk code into overlapping segments."""
        lines = content.split("\n")
        chunks = []
        current_chunk = []
        current_size = 0

        for line in lines:
            current_chunk.append(line)
            current_size += len(line) + 1

            if current_size >= chunk_size:
                chunks.append("\n".join(current_chunk))
                # Keep overlap
                overlap_lines = []
                overlap_size = 0
                for l in reversed(current_chunk):
                    overlap_size += len(l) + 1
                    overlap_lines.insert(0, l)
                    if overlap_size >= overlap:
                        break
                current_chunk = overlap_lines
                current_size = overlap_size

        if current_chunk:
            chunks.append("\n".join(current_chunk))

        return chunks

    def add_documents(self, documents: List[Dict[str, Any]], batch_size: int = 50):
        """
        Add documents to vector store.
        Each doc: {"id": str, "text": str, "metadata": dict}
        """
        logger.info(f"Adding {len(documents)} documents to vector store")
        logger.info(f"Batch size: {batch_size}")
        logger.info(
            f"Number iterations: {len(documents) // batch_size + (1 if len(documents) % batch_size != 0 else 0)}"
        )
        # Process in batches
        for i in range(0, len(documents), batch_size):
            batch = documents[i : i + batch_size]

            ids = [doc["id"] for doc in batch]
            texts = [doc["text"] for doc in batch]
            metadatas = [doc.get("metadata", {}) for doc in batch]
            # Compute embeddings for the batch
            batch_embeddings = self.get_embeddings(texts)
            # Add to collection
            self.collection.add(
                ids=ids,
                embeddings=batch_embeddings,
                documents=texts,
                metadatas=metadatas,
            )
            logger.info(f"Added batch {i // batch_size + 1}")

    def query(
        self, query_text: str, k: int = 5, filter_metadata: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        """Query vector store for similar documents."""
        query_embedding = self.get_embeddings([query_text])[0]

        results = self.collection.query(
            query_embeddings=[query_embedding], n_results=k, where=filter_metadata
        )

        # Format results
        formatted = []
        for i in range(len(results["ids"][0])):
            formatted.append(
                {
                    "id": results["ids"][0][i],
                    "text": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "distance": results["distances"][0][i],
                }
            )

        return formatted

    def add_repo_to_index(self, repo_metadata: Dict[str, Any]):
        """Add a complete repository to the index."""
        documents = []

        repo_name = repo_metadata["name"]

        for file_info in repo_metadata["files"]:
            file_path = file_info["path"]

            # Read file content
            try:
                with open(file_info["full_path"], "r", encoding="utf-8") as f:
                    content = f.read()
            except Exception as e:
                logger.warning(f"Failed to read {file_path}: {e}")
                continue

            # Chunk file
            chunks = self.chunk_code(content)

            for idx, chunk in enumerate(chunks):
                doc_id = f"{repo_name}::{file_path}::chunk{idx}"
                documents.append(
                    {
                        "id": doc_id,
                        "text": chunk,
                        "metadata": {
                            "repo": repo_name,
                            "file": file_path,
                            "chunk_index": idx,
                            "functions": ",".join(
                                [f["name"] for f in file_info.get("functions", [])]
                            ),
                            "classes": ",".join(
                                [c["name"] for c in file_info.get("classes", [])]
                            ),
                        },
                    }
                )

        self.add_documents(documents)
        logger.info(f"Indexed {len(documents)} chunks from {repo_name}")
