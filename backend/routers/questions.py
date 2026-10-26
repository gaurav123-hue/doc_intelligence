from fastapi import APIRouter
from pydantic import BaseModel, Field 

router = APIRouter()


class QuestionRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2000)


@router.post("/questions/preview")
def preview_question(request: QuestionRequest):
    return {
        "received_question": request.question,
        "message": "Question received successfully"
    }