"""Language detection and instruction utilities for chat services."""

# Personality presets for different assistant behaviors
PERSONALITY_PROMPTS: dict[str, str] = {
    "professional": "You are a professional assistant. Be formal, concise, and accurate.",
    "friendly": "You are a friendly assistant. Be conversational, helpful, and approachable.",
    "technical": "You are a technical assistant. Be detailed, precise, and use technical terminology when appropriate.",
}

# Language instruction - added to system prompt when custom prompt doesn't have it
LANGUAGE_INSTRUCTION = """
LANGUAGE: Always respond in the same language as the user's question. If the user asks in Portuguese, respond in Portuguese. If in English, respond in English."""

# Keywords that indicate custom prompt already has language instructions
LANGUAGE_KEYWORDS: frozenset[str] = frozenset({
    # English
    "respond in", "answer in", "reply in", "language:",
    # Portuguese
    "responda em", "responder em", "idioma:", "linguagem:",
    # Spanish
    "responde en", "responder en",
    # Italian
    "rispondi in", "rispondere in", "lingua:",
    # French
    "répondre en", "réponds en", "langue:",
})

# Language keywords mapping for auto-detection from custom prompts
# Maps keywords to prefix that will be added to user message
LANGUAGE_PREFIXES: dict[tuple[str, ...], str] = {
    ("espanhol", "spanish"): "[Respond in Spanish] ",
    ("inglês", "english"): "[Respond in English] ",
    ("francês", "french"): "[Respond in French] ",
    ("alemão", "german"): "[Respond in German] ",
    ("italiano", "italian"): "[Respond in Italian] ",
    ("japonês", "japanese"): "[Respond in Japanese] ",
    ("chinês", "chinese"): "[Respond in Chinese] ",
}


def has_language_instruction(text: str) -> bool:
    """Check if text contains language-related instructions.

    Args:
        text: Text to check (typically custom system prompt).

    Returns:
        True if text contains language keywords.
    """
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in LANGUAGE_KEYWORDS)


def detect_language_prefix(custom_instructions: str | None) -> str:
    """Detect language instruction and return appropriate prefix.

    This helps enforce language instructions for models that might
    otherwise ignore system prompt language directives.

    Args:
        custom_instructions: The custom system prompt to analyze.

    Returns:
        A prefix string like "[Respond in Spanish] " or empty string.
    """
    if not custom_instructions:
        return ""

    custom_lower = custom_instructions.lower()
    for keywords, prefix in LANGUAGE_PREFIXES.items():
        if any(kw in custom_lower for kw in keywords):
            return prefix
    return ""
