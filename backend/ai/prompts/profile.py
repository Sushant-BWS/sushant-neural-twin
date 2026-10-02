"""Profile-oriented prompts."""


def profile_prompt(name: str = "Sushant") -> str:
    return (
        f"Provide a concise and accurate profile summary for {name}. "
        "Use documented facts, experience, and education sources only."
    )
