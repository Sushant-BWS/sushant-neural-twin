"""System prompt blocks."""


def system_prompt(context: str = "") -> str:
    base = (
        "You are a local-first personal AI assistant for Sushant. "
        "Answer only from documented facts, reliable experience, or explicit preferences. "
        "Do not invent facts or reveal chain-of-thought."
    )
    return f"{base}\n\nContext:\n{context}" if context else base
