from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from pathlib import Path
import json
import subprocess
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


class IngestRequest(BaseModel):
    repo_url: str


@router.get("/")
async def list_repos():
    """List all ingested repositories."""
    metadata_dir = Path("./data/metadata")

    if not metadata_dir.exists():
        return {"repos": []}

    repos = []
    for json_file in metadata_dir.glob("*.json"):
        with open(json_file, 'r') as f:
            metadata = json.load(f)
            repos.append({
                'name': metadata['name'],
                'total_files': metadata['total_files'],
                'total_functions': metadata['total_functions'],
                'total_classes': metadata['total_classes']
            })

    return {"repos": repos}


@router.get("/{repo_name}")
async def get_repo_details(repo_name: str):
    """Get detailed metadata for a specific repository."""
    metadata_file = Path(f"./data/metadata/{repo_name}.json")

    if not metadata_file.exists():
        raise HTTPException(status_code=404, detail="Repository not found")

    with open(metadata_file, 'r') as f:
        metadata = json.load(f)

    return metadata


@router.post("/ingest")
async def ingest_repository(
    request: IngestRequest,
):
    """Ingest a new repository into the system."""
    try:
        logger.info(
            f"Starting ingestion for repository: {request.repo_url}"
        )

        # Run the bootstrap script with the repo URL
        result = subprocess.run(
            ["python", "/app/ingestion/bootstrap.py", request.repo_url],
            capture_output=True,
            text=True,
            timeout=600  # 10 minute timeout for large repos
        )

        if result.returncode != 0:
            logger.error(f"Bootstrap failed: {result.stderr}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to ingest repository: {result.stderr}"
            )

        logger.info(
            f"Successfully ingested repository: {request.repo_url}"
        )

        return {
            "status": "success",
            "message": (
                f"Repository {request.repo_url} has been "
                f"ingested successfully"
            ),
            "output": result.stdout
        }

    except subprocess.TimeoutExpired:
        raise HTTPException(
            status_code=504,
            detail=(
                "Repository ingestion timed out. "
                "Please try again or check repository size."
            )
        )
    except Exception as e:
        logger.error(f"Error during ingestion: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))