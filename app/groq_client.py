from __future__ import annotations

from typing import Any

try:
    from groq import APIConnectionError, APIError, APIStatusError, AsyncGroq, RateLimitError
except ImportError:  # pragma: no cover - handled at runtime with a clear error message
    APIConnectionError = APIError = APIStatusError = RateLimitError = Exception
    AsyncGroq = None

from app.config import settings

client = AsyncGroq(api_key=settings.groq_api_key) if AsyncGroq and settings.groq_api_key else None


class ModelDiscoveryError(RuntimeError):
    """Raised when Groq's model catalog cannot be loaded."""


SYSTEM_TEMPLATE = """
You are LumiAI, a friendly multilingual assistant.

Core rules:
- Be helpful, clear, and concise.
- Answer in the user's detected language: Russian, Uzbek, or English.
- Do not invent facts or claim certainty without evidence.
- Prefer practical, structured explanations.
- Help with coding, reasoning, writing, translation, analysis, and general productivity.
- Keep context in mind but avoid repeating greetings or generic introductions in every reply.
- If the user asks for code, provide clean, correct code snippets.
- For math, show reasoning clearly and verify the result.
- If the user's request is unclear, ask a precise clarifying question.
"""


async def get_available_models() -> list[str]:
    if client is None:
        return []
    try:
        models = await client.models.list()
        ids: list[str] = []
        for model in models.data:
            model_id = getattr(model, "id", None)
            if model_id:
                ids.append(model_id)
        return sorted(set(ids))
    except (APIConnectionError, APIStatusError, APIError, TimeoutError) as exc:
        raise ModelDiscoveryError from exc


def detect_language(text: str) -> str:
    lower = text.lower()
    if any(token in lower for token in ("привет", "как дела", "помоги", "рус", "сделай", "пожалуйста")):
        return "ru"
    if any(token in lower for token in ("salom", "qanday", "yordam", "ozbek", "uzbek", "tarjima")):
        return "uz"
    return "en"


def build_system_prompt(user_language: str, persona: str) -> str:
    language_map = {
        "ru": "Отвечай на русском языке. Используй понятный и профессиональный стиль.",
        "uz": "O'zbek tilida javob bering. Sodda va qulay uslubdan foydalaning.",
        "en": "Respond in English. Keep the tone clear, polished, and helpful.",
    }
    persona_hint = persona or "friendly and practical"
    return f"{SYSTEM_TEMPLATE}\n\n{language_map.get(user_language, language_map['en'])}\nPersona: {persona_hint}"


async def chat_with_groq(history: list[dict[str, str]], user_message: str, model: str, language: str, persona: str) -> str:
    if client is None:
        if AsyncGroq is None:
            return (
                "⚠️ Groq SDK не установлен. Запустите бота через виртуальное окружение и выполните:\n"
                "C:\\LumiAI\\.venv\\Scripts\\python.exe -m pip install -r requirements.txt\n"
                "После этого запускайте: C:\\LumiAI\\.venv\\Scripts\\python.exe -m app"
            )
        return "⚠️ API key is not configured. Please set GROQ_API_KEY in your .env file."

    messages: list[dict[str, str]] = [{"role": "system", "content": build_system_prompt(language, persona)}]
    for entry in history:
        if entry.get("role") in {"user", "assistant"}:
            messages.append({"role": entry["role"], "content": str(entry["content"])})
    messages.append({"role": "user", "content": user_message})

    try:
        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.7,
            max_tokens=1024,
            timeout=30,
        )
        content = response.choices[0].message.content
        return content or "Я не смог получить ответ. Попробуй ещё раз."
    except RateLimitError:
        return "⏳ Groq API временно перегружен. Пожалуйста, попробуйте снова через несколько секунд."
    except APIStatusError as exc:
        if "model_not_found" in str(getattr(exc, "body", "")).lower() or "model_not_found" in str(exc).lower():
            return (
                f"⚠️ Модель «{model}» недоступна для вашего аккаунта Groq. "
                "Откройте /model и выберите доступную модель."
            )
        return f"⚠️ Ошибка соединения с Groq API: {exc}"
    except (APIConnectionError, APIError, TimeoutError) as exc:
        return f"⚠️ Ошибка соединения с Groq API: {exc}"
    except Exception as exc:  # pragma: no cover - defensive fallback
        return f"⚠️ Не удалось обработать запрос: {exc}"


def split_message(text: str, chunk_size: int = 4000) -> list[str]:
    if len(text) <= chunk_size:
        return [text]
    chunks: list[str] = []
    current = ""
    for part in text.splitlines(True):
        if len(current) + len(part) > chunk_size:
            chunks.append(current.rstrip())
            current = part
        else:
            current += part
    if current:
        chunks.append(current.rstrip())
    return chunks or [text]
