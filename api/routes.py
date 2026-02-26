from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, HttpUrl
import logging

from services.orchestrator import process_github_repo
from services.github import GitHubClientError

logger = logging.getLogger(__name__)

router = APIRouter()

class SummarizeRequest(BaseModel):
    """
    Pydantic model representing the expected JSON body for the POST /summarize request.
    Strictly validates that the provided string is a valid HTTP URL before execution.
    """
    github_url: HttpUrl

class SummarizeResponse(BaseModel):
    """
    Pydantic model representing the successful JSON response according to task requirements.
    Ensures the response always contains exactly 'summary', 'technologies', and 'structure'.
    """
    summary: str
    technologies: list[str]
    structure: str

class ErrorResponse(BaseModel):
    """
    Standardized payload for error responses as requested by the task criteria.
    """
    status: str
    message: str

@router.post("/summarize", response_model=SummarizeResponse, responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}})
async def summarize_repo(request: SummarizeRequest):
    """
    Main API endpoint to summarize a GitHub repository.
    
    Expects a JSON body containing {"github_url": "https://..."}.
    Delegates all business logic (fetching, filtering, LLM summary) to the orchestrator service.
    Translates local Python exceptions into proper JSON HTTP error responses.
    """
    try:
        # Convert HttpUrl type back to string before passing to orchestrator
        summary_data = await process_github_repo(str(request.github_url))
        
        # Ensure the response exactly matches the required Pydantic model
        return SummarizeResponse(
            summary=summary_data.get("summary", "No summary provided."),
            technologies=summary_data.get("technologies", []),
            structure=summary_data.get("structure", "No structure provided.")
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"status": "error", "message": str(e)})
    except GitHubClientError as e:
        raise HTTPException(status_code=400, detail={"status": "error", "message": str(e)})
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail={"status": "error", "message": "An internal server error occurred."})
