import json
from typing import Dict, Any
from langchain_core.messages import HumanMessage, SystemMessage

from llm import get_llm, load_intent_prompt


def classify_intent(user_message: str, chat_history: list, agent_summary: Dict[str, Any]) -> Dict[str, Any]:
    """
    Classify the user's intent to determine if tools are needed.

    Args:
        user_message: The current user message
        chat_history: Recent chat history
        agent_summary: Summary of user's diary and chat context

    Returns:
        Dictionary with needs_tools, tool_name, and reasoning
    """
    intent_prompt = load_intent_prompt()

    history_str = "\n".join([
        f"{msg['role']}: {msg['content']}" for msg in chat_history[-5:]
    ])

    summary_str = json.dumps(agent_summary, indent=2)

    prompt = f"""{intent_prompt}

---

Conversation Summary:
{summary_str}

Recent Chat History:
{history_str}

User Message: {user_message}

Respond with JSON only:"""

    try:
        messages = [
            SystemMessage(content="You are an intent classifier. Respond with JSON only."),
            HumanMessage(content=prompt)
        ]
        response = get_llm(temperature=0.3, purpose="intent_recognition").invoke(messages)
        content = response.content

        json_start = content.find("{")
        json_end = content.rfind("}") + 1
        if json_start >= 0 and json_end > json_start:
            json_str = content[json_start:json_end]
            result = json.loads(json_str)
        else:
            result = json.loads(content)

        return {
            "needs_tools": result.get("needs_tools", False),
            "tool_name": result.get("tool_name"),
            "reasoning": result.get("reasoning", "")
        }
    except json.JSONDecodeError:
        return {
            "needs_tools": False,
            "tool_name": None,
            "reasoning": "Failed to parse intent, defaulting to direct response"
        }
    except Exception as e:
        return {
            "needs_tools": False,
            "tool_name": None,
            "reasoning": f"Error in classification: {str(e)}"
        }
