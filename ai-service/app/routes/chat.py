from fastapi import APIRouter

from app.models.chat_models import ChatRequest, ChatResponse
from app.services.ai_service import generate_response


router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):

    response = generate_response(request.message)

    return ChatResponse(
        response=response
    )