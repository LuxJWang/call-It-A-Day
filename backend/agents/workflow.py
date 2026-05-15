import json
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from llm import bedrock_client, load_system_prompt, load_tool_spec
from agents.intent_classifier import classify_intent
from agents.summary_builder import build_agent_summary
from tools.memory_tools import search_memories, add_memory
from tools.diary_tools import get_recent_diaries


class ChatWorkflow:
    def __init__(self, db: Session):
        self.db = db
        self.system_prompt = load_system_prompt()

    def process_message(self, user_message: str, chat_history: List[Dict[str, str]], session_id: str = "default") -> Dict[str, Any]:
        """
        Process a user message through the two-turn workflow.

        Args:
            user_message: The user's message
            chat_history: Previous chat messages
            session_id: Current session ID

        Returns:
            Response dictionary with text and optional tool calls
        """
        agent_summary = build_agent_summary(self.db, session_id)

        intent = classify_intent(user_message, chat_history, agent_summary)

        if not intent["needs_tools"]:
            response = self._generate_direct_response(user_message, chat_history)
            return {
                "response": response,
                "tool_calls": None,
                "reasoning": intent.get("reasoning", "Direct response")
            }

        tool_name = intent.get("tool_name")
        tool_result = self._execute_tool(tool_name, user_message)

        response = self._generate_response_with_tool_result(
            user_message, chat_history, tool_name, tool_result
        )

        return {
            "response": response,
            "tool_calls": [{"tool": tool_name, "result": tool_result}],
            "reasoning": intent.get("reasoning", "Used tool: " + tool_name)
        }

    def _generate_direct_response(self, user_message: str, chat_history: List[Dict[str, str]]) -> str:
        """Generate a direct response without tools."""
        messages = chat_history + [{"role": "user", "content": user_message}]

        return bedrock_client.generate_with_history(
            messages=messages,
            system_prompt=self.system_prompt,
            max_tokens=2048
        )

    def _execute_tool(self, tool_name: Optional[str], user_message: str) -> Any:
        """Execute the specified tool."""
        if tool_name == "memory_search":
            return search_memories(user_message, limit=5)

        elif tool_name == "memory_add":
            memory_id = add_memory(user_message)
            return {"memory_id": memory_id, "status": "added"}

        elif tool_name == "diary_retrieve":
            recent = get_recent_diaries(self.db, limit=5)
            return [
                {"id": d.id, "content": d.content[:200] + "...", "date": d.created_at.isoformat()}
                for d in recent
            ]

        else:
            return {"error": f"Unknown tool: {tool_name}"}

    def _generate_response_with_tool_result(
        self,
        user_message: str,
        chat_history: List[Dict[str, str]],
        tool_name: str,
        tool_result: Any
    ) -> str:
        """Generate a response incorporating tool results."""
        tool_spec = load_tool_spec(tool_name)
        tool_desc = tool_spec.get("description", "A tool for retrieving information") if tool_spec else "A tool"

        tool_context = f"""[Tool Result]
Tool Used: {tool_name}
Description: {tool_desc}
Result: {json.dumps(tool_result, indent=2)}
[/Tool Result]

Based on this information, respond to the user's message."""

        messages = chat_history + [
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": tool_context},
            {"role": "user", "content": "Please respond based on the tool result above."}
        ]

        return bedrock_client.generate_with_history(
            messages=messages,
            system_prompt=self.system_prompt,
            max_tokens=2048
        )
