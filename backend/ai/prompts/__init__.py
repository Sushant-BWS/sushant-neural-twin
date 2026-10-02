"""Prompt management split by responsibility."""

from backend.ai.prompts.casual import casual_prompt
from backend.ai.prompts.profile import profile_prompt
from backend.ai.prompts.recruiter import recruiter_prompt
from backend.ai.prompts.system import system_prompt
from backend.ai.prompts.technical import technical_prompt
from backend.ai.prompts.voice import voice_prompt

__all__ = [
    "casual_prompt",
    "profile_prompt",
    "recruiter_prompt",
    "system_prompt",
    "technical_prompt",
    "voice_prompt",
]
