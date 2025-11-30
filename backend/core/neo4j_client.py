from neo4j import GraphDatabase
import os
import time
import logging

logger = logging.getLogger(__name__)


class Neo4jClient:
    def __init__(
        self,
        uri: str = None,
        user: str = None,
        password: str = None,
        max_retries: int = 5,
    ):
        uri = uri or os.environ.get("NEO4J_URI", "bolt://localhost:7687")
        user = user or os.environ.get("NEO4J_USER", "neo4j")
        password = password or os.environ.get("NEO4J_PASSWORD", "test")

        # Retry connection with exponential backoff
        for attempt in range(max_retries):
            try:
                self.driver = GraphDatabase.driver(uri, auth=(user, password))
                # Verify connectivity
                self.driver.verify_connectivity()
                logger.info(f"Successfully connected to Neo4j at {uri}")
                break
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = 2**attempt
                    logger.warning(
                        f"Failed to connect to Neo4j "
                        f"(attempt {attempt + 1}/{max_retries}): {e}. "
                        f"Retrying in {wait_time}s..."
                    )
                    time.sleep(wait_time)
                else:
                    logger.error(
                        f"Failed to connect to Neo4j " f"after {max_retries} attempts"
                    )
                    raise

    def close(self):
        self.driver.close()

    def run(self, cypher: str, params: dict | None = None):
        with self.driver.session() as session:
            result = session.run(cypher, params or {})
            return result.data()
