import json
from typing import Dict, Any
from llm import bedrock_client, load_intent_prompt


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
        response = bedrock_client.generate(
            prompt=prompt,
            max_tokens=512
        )

        json_start = response.find("{")
        json_end = response.rfind("}") + 1
        if json_start >= 0 and json_end > json_start:
            json_str = response[json_start:json_end]
            result = json.loads(json_str)
        else:
            result = json.loads(response)

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
