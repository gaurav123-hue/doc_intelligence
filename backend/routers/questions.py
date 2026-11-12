
"""API endpoints for asking questions about uploaded documents."""

from fastapi import APIRouter
from pydantic import BaseModel, Field

# Reuse the existing embedding and vector-search implementations.
from backend.database import search_similar_chunks
from backend.services.embedding import generate_embedding

# Import the RAG orchestration function for document-based answers.
from backend.services.rag import answer_question

router = APIRouter()


class QuestionRequest(BaseModel):
    """Validate the question submitted by the client."""

    question: str = Field(min_length=3, max_length=2000)


@router.post("/preview")
def preview_question(request: QuestionRequest):
    """Confirm that a question was received."""

    return {
        "received_question": request.question,
        "message": "Question received successfully",
    }


@router.post("/search")
def search_question(request: QuestionRequest):
    """Find document chunks semantically related to a question."""

    # Convert the user's question into the same vector space as stored chunks.
    query_embedding = generate_embedding(request.question)

    # Retrieve the five closest matching chunks from PostgreSQL using pgvector.
    results = search_similar_chunks(query_embedding, limit=5)

    # Return the original question and source text for inspection.
    return {
        "question": request.question,
        "results_count": len(results),
        "results": results,
    }



@router.post("/ask")
def ask_question(request: QuestionRequest):
    """Answer a question using retrieved document context and the Groq LLM."""

    # Run the complete RAG pipeline: embedding, retrieval, prompt construction,
    # and language model response generation.
    result = answer_question(request.question, limit=5)

    # Return the generated answer along with its supporting source references.
    return result
