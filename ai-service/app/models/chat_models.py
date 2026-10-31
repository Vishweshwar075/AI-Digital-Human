
from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    conversation_id: str


class ChatResponse(BaseModel):
    response: str


class ConversationSummary(BaseModel):
    conversation_id: str
    created_at: str
    updated_at: str


class ConversationMessage(BaseModel):
    role: str
    content: str
    created_at: str


class ConversationDetail(BaseModel):
    conversation_id: str
    created_at: str
    updated_at: str
    messages: list[ConversationMessage]
