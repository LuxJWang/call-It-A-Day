import json
import os
from typing import Optional, Dict, Any

SOUL_DIR = os.path.join(os.path.dirname(__file__), "..", "soul")


def load_system_prompt() -> str:
    path = os.path.join(SOUL_DIR, "system_prompt.txt")
    try:
        with open(path, "r") as f:
            return f.read()
    except FileNotFoundError:
        return _default_system_prompt()


def load_intent_prompt() -> str:
    path = os.path.join(SOUL_DIR, "intent_prompt.txt")
    try:
        with open(path, "r") as f:
            return f.read()
    except FileNotFoundError:
        return _default_intent_prompt()


def load_tool_spec(tool_name: str) -> Optional[Dict[str, Any]]:
    path = os.path.join(SOUL_DIR, "tool_specs", f"{tool_name}.json")
    try:
        with open(path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return None


def get_all_tool_names() -> list:
    tool_specs_dir = os.path.join(SOUL_DIR, "tool_specs")
    if not os.path.exists(tool_specs_dir):
        return []
    files = os.listdir(tool_specs_dir)
    return [f.replace(".json", "") for f in files if f.endswith(".json")]


def _default_system_prompt() -> str:
    return """You are a thoughtful and empathetic diary companion. Your role is to:

1. Listen attentively to the user's thoughts and experiences
2. Offer gentle, supportive responses
3. Help them reflect on their day and patterns in their life
4. Reference relevant past memories when appropriate
5. Be concise but warm in your responses

Remember details they've shared before and use them to provide personalized support."""


def _default_intent_prompt() -> str:
    return """You are an intent classifier for a diary companion AI.

Given the user's message and conversation summary, decide if any tools are needed.

Available tool categories:
- memory_search: When user asks about past events, patterns, or history
- memory_add: When user shares new information worth remembering long-term
- diary_retrieve: When user references specific diary entries or dates

Respond in this exact JSON format:
{
    "needs_tools": true/false,
    "tool_name": "memory_search" or null,
    "reasoning": "brief explanation"
}

Keep your response concise and focused."""
