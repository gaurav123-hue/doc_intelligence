
"""API routes for submitting questions about uploaded documents."""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from backend.database import (
    get_conversation_history,
    save_conversation_turn,
)
from backend.services.rag import answer_question
from backend.services.sessions import get_authenticated_session

logger = logging.getLogger(__name__)

# The /questions prefix is added in backend/main.py.
router = APIRouter(tags=["Questions"])


class QuestionRequest(BaseModel):
    """Validate questions submitted by the client."""

    question: str = Field(
        min_length=3,
        max_length=2000,
        description="Question to ask about uploaded documents",
    )


@router.post("/preview")
def preview_question(
    request: QuestionRequest,
    session: dict = Depends(get_authenticated_session),
):
    """Preview a question after verifying the active session."""

    return {
        "received_question": request.question,
        "session_id": session["id"],
        "message": "Question received successfully",
    }


@router.post("/ask")
def ask_question(
    request: QuestionRequest,
    session: dict = Depends(get_authenticated_session),
):
    """Generate an answer and persist the conversation."""

    try:
        # Generate an answer using documents from the authenticated session.
        result = answer_question(
            request.question,
            session_id=session["id"],
        )

        # Save the completed question, answer, and citation metadata.
        conversation = save_conversation_turn(
            session_id=session["id"],
            question=result["question"],
            answer=result["answer"],
            sources=result["sources"],
            cited_source_details=result["cited_source_details"],
            citation_validation=result["citation_validation"],
            result_count=result["result_count"],
        )

        # Include the persistent conversation ID and timestamp in the response.
        result["conversation_id"] = conversation["id"]
        result["created_at"] = conversation["created_at"]

        return result

    except Exception:
        # Log technical details without exposing them to the API client.
        logger.exception("Failed to generate or save conversation")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to process your question at this time.",
        )


@router.get("/history")
def get_question_history(
    session: dict = Depends(get_authenticated_session),
):
    """Retrieve conversation history belonging to the active session."""

    try:
        # Fetch only conversations associated with the authenticated session.
        history = get_conversation_history(session["id"])

        # Return the records and their total count.
        return {
            "history": history,
            "count": len(history),
        }

    except Exception:
        # Keep internal database errors out of the API response.
        logger.exception("Failed to retrieve conversation history")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to retrieve conversation history at this time.",
        )
