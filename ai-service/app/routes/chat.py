
from fastapi import APIRouter, HTTPException, Query

from app.models.chat_models import (
    ChatRequest,
    ChatResponse,
    ConversationSummary,
    ConversationDetail,
    ConversationMessage,
)

from app.services.ai_service import (
    AIServiceUnavailable,
    generate_response,
    get_db_connection,
)


router = APIRouter()


# --------------------------------------------------
# Send a message to EVA
# --------------------------------------------------

@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):

    message = request.message.strip()
    conversation_id = request.conversation_id.strip()

    if not message:
        raise HTTPException(
            status_code=400,
            detail="Message cannot be empty.",
        )

    if not conversation_id:
        raise HTTPException(
            status_code=400,
            detail="Conversation ID cannot be empty.",
        )

    try:
        answer = generate_response(
            message=message,
            conversation_id=conversation_id,
        )

        return ChatResponse(response=answer)

    except AIServiceUnavailable as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc


# --------------------------------------------------
# Get all saved conversations
# --------------------------------------------------

@router.get(
    "/conversations",
    response_model=list[ConversationSummary],
)
def list_conversations(
    limit: int = Query(default=50, ge=1, le=100),
):

    with get_db_connection() as connection:
        rows = connection.execute("""
            SELECT conversation_id, created_at, updated_at
            FROM conversations
            ORDER BY updated_at DESC
            LIMIT ?
        """, (limit,)).fetchall()

    return [
        ConversationSummary(
            conversation_id=row["conversation_id"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
        for row in rows
    ]


# --------------------------------------------------
# Get a conversation and its messages
# --------------------------------------------------

@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationDetail,
)
def get_conversation(conversation_id: str):

    clean_id = conversation_id.strip()

    if not clean_id:
        raise HTTPException(
            status_code=400,
            detail="Conversation ID cannot be empty.",
        )

    with get_db_connection() as connection:

        conversation = connection.execute("""
            SELECT conversation_id, created_at, updated_at
            FROM conversations
            WHERE conversation_id = ?
        """, (clean_id,)).fetchone()

        if conversation is None:
            raise HTTPException(
                status_code=404,
                detail="Conversation not found.",
            )

        rows = connection.execute("""
            SELECT role, content, created_at
            FROM messages
            WHERE conversation_id = ?
            ORDER BY id ASC
        """, (clean_id,)).fetchall()

    return ConversationDetail(
        conversation_id=conversation["conversation_id"],
        created_at=conversation["created_at"],
        updated_at=conversation["updated_at"],
        messages=[
            ConversationMessage(
                role=row["role"],
                content=row["content"],
                created_at=row["created_at"],
            )
            for row in rows
        ],
    )
