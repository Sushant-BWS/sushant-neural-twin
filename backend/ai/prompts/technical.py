"""Technical prompts for skill and project summaries."""


def technical_prompt(topic: str = "software") -> str:
    return (
        f"Explain {topic} experience using documented skills, projects, and career evidence. "
        "Do not speculate beyond the available records."
    )
