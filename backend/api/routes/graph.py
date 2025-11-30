from fastapi import APIRouter
from pydantic import BaseModel
from core.neo4j_client import Neo4jClient

router = APIRouter()

# Neo4j client singleton
_neo4j_client = None


def get_neo4j():
    global _neo4j_client
    if _neo4j_client is None:
        _neo4j_client = Neo4jClient()
    return _neo4j_client


class CypherQuery(BaseModel):
    query: str


@router.get("/schema")
async def graph_schema():
    """Get graph schema summary."""
    return {
        "nodes": ["Repository", "File", "Function", "Class",
                  "Module", "Commit"],
        "relationships": [
            "CONTAINS (Repository->File)",
            "DEFINES (File->Function)",
            "DEFINES (File->Class)",
            "IMPORTS (File->Module)",
            "CALLS (Function->Function)",
            "HAS_COMMIT (Repository->Commit)"
        ]
    }


@router.post("/query")
async def execute_cypher(req: CypherQuery):
    """Execute a Cypher query on the graph."""
    neo4j = get_neo4j()

    try:
        result = neo4j.run(req.query)
        records = [dict(record) for record in result]
        return {"results": records, "count": len(records)}
    except Exception as e:
        return {"error": str(e), "results": []}


@router.get("/stats")
async def graph_stats():
    """Get graph database statistics."""
    neo4j = get_neo4j()

    stats_query = """
    MATCH (r:Repository)
    OPTIONAL MATCH (r)-[:CONTAINS]->(f:File)
    OPTIONAL MATCH (f)-[:DEFINES]->(fn:Function)
    OPTIONAL MATCH (f)-[:DEFINES]->(c:Class)
    RETURN
        count(DISTINCT r) as repositories,
        count(DISTINCT f) as files,
        count(DISTINCT fn) as functions,
        count(DISTINCT c) as classes
    """

    result = neo4j.run(stats_query)
    record = next(result)

    return dict(record)
