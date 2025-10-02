from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

import google.generativeai as genai
from flask import current_app

from ..extensions import db
from ..models import AssistantConversation, AssistantMessage, User


ROLE_USER = "user"
ROLE_ASSISTANT = "assistant"


class AssistantServiceError(RuntimeError):
    """Raised when the assistant cannot process a request."""


@dataclass(frozen=True)
class ConversationSnapshot:
    conversation: AssistantConversation
    messages: Sequence[AssistantMessage]


def get_or_create_conversation(user: User) -> AssistantConversation:
    conversation = AssistantConversation.query.filter_by(user_id=user.id).first()
    if conversation is None:
        conversation = AssistantConversation(user=user)
        db.session.add(conversation)
        db.session.flush()
        greeting = (current_app.config.get("ASSISTANT_GREETING") or "").strip()
        if greeting:
            db.session.add(
                AssistantMessage(
                    conversation=conversation,
                    role=ROLE_ASSISTANT,
                    content=greeting,
                )
            )
            db.session.flush()
    return conversation


def load_history(conversation: AssistantConversation, limit: int) -> list[AssistantMessage]:
    if limit <= 0:
        return []
    query = (
        AssistantMessage.query.filter_by(conversation_id=conversation.id)
        .order_by(AssistantMessage.created_at.desc())
        .limit(limit)
    )
    messages = list(query)
    messages.reverse()
    return messages


def _build_chat_history(messages: Iterable[AssistantMessage], system_prompt: str) -> list[dict]:
    history = [
        {
            "role": "user",
            "parts": [system_prompt],
        }
    ]
    for message in messages:
        role = "model" if message.role == ROLE_ASSISTANT else "user"
        history.append({"role": role, "parts": [message.content]})
    return history


def _extract_text(response) -> str:
    text = getattr(response, "text", None)
    if text:
        return text.strip()
    candidates = getattr(response, "candidates", None) or []
    for candidate in candidates:
        content = getattr(candidate, "content", None)
        parts = getattr(content, "parts", None) if content else None
        if not parts:
            continue
        buffer = []
        for part in parts:
            value = getattr(part, "text", None)
            if value:
                buffer.append(value)
        if buffer:
            return "\n".join(value.strip() for value in buffer if value.strip())
    return ""


def _usage_token_count(response) -> int | None:
    usage = getattr(response, "usage_metadata", None)
    if usage is None:
        return None
    for attribute in ("total_token_count", "total_tokens"):  # compatibility
        value = getattr(usage, attribute, None)
        if value is not None:
            return int(value)
    return None


def send_assistant_message(user: User, content: str) -> ConversationSnapshot:
    if not content or not content.strip():
        raise AssistantServiceError("Mensagem vazia nao pode ser processada.")

    conversation = get_or_create_conversation(user)

    history_limit = max(1, int(current_app.config.get("ASSISTANT_HISTORY_LIMIT", 12)))
    previous_messages = load_history(conversation, history_limit)

    api_key = current_app.config.get("GEMINI_API_KEY")
    model_name = current_app.config.get("GEMINI_MODEL", "models/gemini-2.5-flash")
    system_prompt = current_app.config.get("ASSISTANT_SYSTEM_PROMPT")

    if not api_key:
        raise AssistantServiceError("Gemini API key nao configurada.")

    genai.configure(api_key=api_key)
    history_payload = _build_chat_history(previous_messages, system_prompt)
    model = genai.GenerativeModel(model_name=model_name)
    chat = model.start_chat(history=history_payload)

    try:
        response = chat.send_message(content.strip())
    except Exception as exc:  # pragma: no cover - defensive network wrapper
        raise AssistantServiceError("Falha ao consultar o modelo Gemini.") from exc

    answer_text = _extract_text(response)
    if not answer_text:
        raise AssistantServiceError("Resposta vazia recebida do modelo.")

    user_message = AssistantMessage(conversation=conversation, role=ROLE_USER, content=content.strip())
    db.session.add(user_message)
    assistant_message = AssistantMessage(
        conversation=conversation,
        role=ROLE_ASSISTANT,
        content=answer_text.strip(),
        token_count=_usage_token_count(response),
    )
    db.session.add(assistant_message)

    messages = load_history(conversation, history_limit)
    return ConversationSnapshot(conversation=conversation, messages=messages)


def snapshot_for(user: User) -> ConversationSnapshot:
    conversation = get_or_create_conversation(user)
    history_limit = max(1, int(current_app.config.get("ASSISTANT_HISTORY_LIMIT", 12)))
    messages = load_history(conversation, history_limit)
    return ConversationSnapshot(conversation=conversation, messages=messages)
