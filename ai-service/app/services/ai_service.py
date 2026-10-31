
import logging
import os
import sqlite3

from pathlib import Path
from datetime import datetime, timezone

from dotenv import load_dotenv
from google import genai
from google.genai import types
from google.genai.errors import APIError


load_dotenv()
logger = logging.getLogger(__name__)


# --------------------------------------------------
# Gemini configuration
# --------------------------------------------------

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise RuntimeError(
        "GEMINI_API_KEY is missing. Check ai-service/.env."
    )

client = genai.Client(
    api_key=GEMINI_API_KEY,
    http_options=types.HttpOptions(
        timeout=15000,
        retry_options=types.HttpRetryOptions(attempts=1),
    ),
)

MODEL_NAME = "gemini-3.1-flash-lite"

EVA_SYSTEM_PROMPT = """
You are EVA, an AI virtual human assistant.

You are friendly, helpful, clear, and conversational.
You explain technical concepts step by step when needed.
You adapt explanations to the user's level of knowledge.
You are transparent that you are an AI, not a human.
Never claim to have performed actions you have not performed.
"""


# --------------------------------------------------
# SQLite database configuration
# --------------------------------------------------

# Store the database in the ai-service project folder.
BASE_DIR = Path(__file__).resolve().parents[2]
DATABASE_PATH = BASE_DIR / "eva_chat.db"

MAX_HISTORY_MESSAGES = 20


class AIServiceUnavailable(Exception):
    """Raised when EVA cannot get a response from the AI provider."""


def get_db_connection():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database():
    """Create conversation tables if they do not exist."""

    with get_db_connection() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                conversation_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        connection.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (conversation_id)
                    REFERENCES conversations(conversation_id)
            )
        """)

        connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_conversation
            ON messages(conversation_id, id)
        """)


def current_timestamp():
    return datetime.now(timezone.utc).isoformat()


# Initialize database when the service module loads.
initialize_database()


# --------------------------------------------------
# Conversation history
# --------------------------------------------------

def get_conversation_history(conversation_id: str):
    """
    Load recent conversation messages from SQLite
    and convert them into Gemini Content objects.
    """

    with get_db_connection() as connection:
        rows = connection.execute("""
            SELECT role, content
            FROM messages
            WHERE conversation_id = ?
            ORDER BY id DESC
            LIMIT ?
        """, (conversation_id, MAX_HISTORY_MESSAGES)).fetchall()

    # The database query returns newest first.
    # Gemini needs chronological order.
    rows = list(reversed(rows))

    history = []

    for row in rows:
        history.append(
            types.Content(
                role=row["role"],
                parts=[
                    types.Part(text=row["content"])
                ],
            )
        )

    return history


def save_conversation_exchange(
    conversation_id: str,
    user_message: str,
    eva_response: str,
):
    """Save a successful user/EVA exchange."""

    timestamp = current_timestamp()

    with get_db_connection() as connection:
        connection.execute("""
            INSERT INTO conversations (
                conversation_id,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?)
            ON CONFLICT(conversation_id)
            DO UPDATE SET updated_at = excluded.updated_at
        """, (
            conversation_id,
            timestamp,
            timestamp,
        ))

        connection.execute("""
            INSERT INTO messages (
                conversation_id,
                role,
                content,
                created_at
            )
            VALUES (?, ?, ?, ?)
        """, (
            conversation_id,
            "user",
            user_message,
            timestamp,
        ))

        connection.execute("""
            INSERT INTO messages (
                conversation_id,
                role,
                content,
                created_at
            )
            VALUES (?, ?, ?, ?)
        """, (
            conversation_id,
            "model",
            eva_response,
            timestamp,
        ))


# --------------------------------------------------
# Gemini response generation
# --------------------------------------------------

def generate_response(message: str, conversation_id: str) -> str:

    if not isinstance(message, str) or not message.strip():
        raise ValueError("Message cannot be empty.")

    if not conversation_id or not conversation_id.strip():
        raise ValueError("Conversation ID cannot be empty.")

    clean_message = message.strip()
    clean_conversation_id = conversation_id.strip()

    # Load previous messages from SQLite.
    history = get_conversation_history(
        clean_conversation_id
    )

    # Add the current user message.
    contents = history + [
        types.Content(
            role="user",
            parts=[
                types.Part(text=clean_message)
            ],
        )
    ]

    try:
        logger.info(
            "Sending request to Gemini model %s",
            MODEL_NAME,
        )

        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=EVA_SYSTEM_PROMPT,
            ),
        )

        answer = response.text

        if not answer or not answer.strip():
            raise AIServiceUnavailable(
                "Gemini returned an empty response."
            )

        answer = answer.strip()

        # Save the exchange only after Gemini succeeds.
        save_conversation_exchange(
            conversation_id=clean_conversation_id,
            user_message=clean_message,
            eva_response=answer,
        )

        logger.info("Gemini response received successfully")

        return answer

    except APIError as exc:
        logger.error(
            "Gemini API request failed: %s",
            exc,
        )

        raise AIServiceUnavailable(
            "EVA's AI provider is temporarily unavailable. "
            "Please try again."
        ) from exc

    except AIServiceUnavailable:
        raise

    except Exception as exc:
        logger.exception(
            "Unexpected error in EVA AI service"
        )

        raise AIServiceUnavailable(
            "EVA could not complete the request. Please try again."
        ) from exc
