from __future__ import annotations

import json
import uuid
from typing import Any, Dict, List, Optional, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph
from sqlalchemy.orm import Session

from agents.skill_registry import SkillRegistry
from llm import get_llm_for_purpose
from models import ChatRun
from observability import record_llm_call, record_tool_invocation, record_error, trace_span
from services.config_registry import config_registry
from services.soul_service import SoulService
from services.trace_service import TraceRecorder


class ChatState(TypedDict, total=False):
    run_id: str
    session_id: str
    user_message: str
    chat_history: List[Dict[str, str]]
    iteration: int
    max_iterations: int
    layer1_decision: Dict[str, Any]
    tool_results: List[Dict[str, Any]]
    final_layer1_result: Dict[str, Any]
    response: str
    should_end: bool
    tool_calls: List[Dict[str, Any]]


class ChatWorkflow:
    def __init__(self, db: Session, run_id: Optional[str] = None):
        self.db = db
        self.run_id = run_id or str(uuid.uuid4())
        self.skill_registry = SkillRegistry(db)
        self.trace: Optional[TraceRecorder] = None
        self.graph = self._build_graph()

    def process_message(
        self,
        user_message: str,
        chat_history: List[Dict[str, str]],
        session_id: str = "default",
        user_message_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        runtime = config_registry.get_runtime("chat")
        self.trace = TraceRecorder(self.db, self.run_id, session_id)
        state: ChatState = {
            "run_id": self.run_id,
            "session_id": session_id,
            "user_message": user_message,
            "chat_history": self._trim_history(chat_history, runtime),
            "iteration": 1,
            "max_iterations": int(runtime.get("layer1_max_iterations", 3)),
            "tool_results": [],
            "tool_calls": [],
        }
        result = self.graph.invoke(state)
        run = ChatRun(
            run_id=self.run_id,
            session_id=session_id,
            user_message_id=user_message_id,
            layer1_result_json=result.get("final_layer1_result"),
            response=result.get("response"),
        )
        self.db.add(run)
        self.db.commit()
        return {
            "response": result.get("response", ""),
            "tool_calls": result.get("tool_calls") or None,
            "reasoning": result.get("final_layer1_result", {}).get("reasoning"),
            "run_id": self.run_id,
            "skip_response": result.get("should_end", False),
        }

    def _build_graph(self):
        graph = StateGraph(ChatState)
        graph.add_node("intent_and_tool_enrichment", self._intent_and_tool_enrichment)
        graph.add_node("execute_tool", self._execute_tool)
        graph.add_node("persist_layer1_result", self._persist_layer1_result)
        graph.add_node("generate_response", self._generate_response)

        graph.set_entry_point("intent_and_tool_enrichment")
        graph.add_conditional_edges(
            "intent_and_tool_enrichment",
            self._route_after_intent,
            {
                "tool": "execute_tool",
                "finish": "persist_layer1_result",
            },
        )
        graph.add_conditional_edges(
            "execute_tool",
            self._route_after_tool,
            {
                "continue": "intent_and_tool_enrichment",
                "finish": "persist_layer1_result",
            },
        )
        graph.add_conditional_edges(
            "persist_layer1_result",
            self._route_after_layer1,
            {
                "end": END,
                "respond": "generate_response",
            },
        )
        graph.add_edge("generate_response", END)
        return graph.compile()

    def _intent_and_tool_enrichment(self, state: ChatState) -> ChatState:
        prompt = self._build_layer1_prompt(state)
        if self.trace:
            self.trace.record(
                node_name="intent_and_tool_enrichment",
                event_type="llm_call",
                layer="layer1",
                input_json={"iteration": state["iteration"], "prompt_chars": len(prompt)},
            )
        record_llm_call("intent_recognition")
        try:
            with trace_span("intent_and_tool_enrichment", as_type="generation"):
                llm = get_llm_for_purpose("intent_recognition")
                response = llm.invoke([
                    SystemMessage(content="你是第一层对话编排器，只返回 JSON。"),
                    HumanMessage(content=prompt),
                ])
                decision = json.loads(_extract_json(response.content))
        except Exception as exc:
            record_error("intent_and_tool_enrichment")
            decision = {
                "action": "finish",
                "reasoning": f"intent fallback: {exc}",
                "final_summary": state["user_message"],
                "skip_response": False,
            }
        state["layer1_decision"] = decision
        if self.trace:
            self.trace.record(
                node_name="intent_and_tool_enrichment",
                event_type="llm_result",
                layer="layer1",
                output_json=decision,
            )
        return state

    def _execute_tool(self, state: ChatState) -> ChatState:
        decision = state.get("layer1_decision", {})
        tool_name = decision.get("tool_name")
        args = decision.get("tool_args") or {}
        if self.trace:
            self.trace.record(
                node_name="execute_tool",
                event_type="tool_call",
                layer="layer1",
                tool_name=tool_name,
                input_json=args,
            )
        record_tool_invocation(tool_name or "unknown")
        try:
            with trace_span(f"tool_call.{tool_name}", as_type="tool"):
                result = self.skill_registry.execute(tool_name, args)
        except Exception as exc:
            record_error("execute_tool")
            result = {"error": str(exc)}
        call = {"tool": tool_name, "args": args, "result": result}
        state.setdefault("tool_results", []).append(call)
        state.setdefault("tool_calls", []).append(call)
        state["iteration"] = state.get("iteration", 1) + 1
        if self.trace:
            self.trace.record(
                node_name="execute_tool",
                event_type="tool_result",
                layer="layer1",
                tool_name=tool_name,
                output_json={"result": result},
            )
        return state

    def _persist_layer1_result(self, state: ChatState) -> ChatState:
        decision = state.get("layer1_decision", {})
        final = {
            "summary": decision.get("final_summary") or decision.get("reasoning") or state["user_message"],
            "reasoning": decision.get("reasoning"),
            "iterations_used": state.get("iteration", 1),
            "tool_results": state.get("tool_results", []),
            "skip_response": bool(decision.get("skip_response")),
        }
        state["final_layer1_result"] = final
        state["should_end"] = bool(decision.get("skip_response"))
        if state["should_end"]:
            state["response"] = self._soul_only_response(final)
        if self.trace:
            self.trace.record(
                node_name="persist_layer1_result",
                event_type="state",
                layer="layer1",
                output_json=final,
            )
        return state

    def _generate_response(self, state: ChatState) -> ChatState:
        docs = SoulService(self.db).read_docs(["diary-soul.md", "user-soul.md"])
        prompt = f"""你是 Call It A Day 的回答生成层。

diary-soul.md:
{docs.get("diary-soul.md", "")}

user-soul.md:
{docs.get("user-soul.md", "")}

第一层结果：
{json.dumps(state.get("final_layer1_result", {}), ensure_ascii=False, indent=2)}

请基于第一层结果和用户当前消息生成给用户的最终回答。回答要自然、真诚、简洁。"""
        messages = [SystemMessage(content=prompt)]
        for msg in state.get("chat_history", []):
            if msg.get("role") in {"user", "assistant"}:
                messages.append(HumanMessage(content=f"{msg['role']}: {msg['content']}"))
        messages.append(HumanMessage(content=state["user_message"]))

        if self.trace:
            self.trace.record(
                node_name="generate_response",
                event_type="llm_call",
                layer="layer2",
                input_json={"history_count": len(state.get("chat_history", []))},
            )
        record_llm_call("response_generation")
        try:
            with trace_span("generate_response", as_type="generation"):
                llm = get_llm_for_purpose("response_generation")
                response = llm.invoke(messages)
                state["response"] = response.content
        except Exception as exc:
            record_error("generate_response")
            state["response"] = f"我现在没能成功调用回答模型，但已经记录了你的消息。错误：{exc}"
        if self.trace:
            self.trace.record(
                node_name="generate_response",
                event_type="llm_result",
                layer="layer2",
                output_json={"response": state["response"]},
            )
        return state

    def _route_after_intent(self, state: ChatState) -> str:
        decision = state.get("layer1_decision", {})
        if decision.get("action") == "call_tool" and decision.get("tool_name"):
            return "tool"
        return "finish"

    def _route_after_tool(self, state: ChatState) -> str:
        if state.get("iteration", 1) > state.get("max_iterations", 3):
            return "finish"
        decision = state.get("layer1_decision", {})
        if decision.get("continue_after_tool", True):
            return "continue"
        return "finish"

    def _route_after_layer1(self, state: ChatState) -> str:
        return "end" if state.get("should_end") else "respond"

    def _build_layer1_prompt(self, state: ChatState) -> str:
        docs = SoulService(self.db).read_docs(["diary-soul.md"])
        return f"""第一层对话任务：做意图识别和信息补充，判断是否调用 skill。

必须考虑这五类信息：
1. 本 prompt。
2. 按长度裁剪后的历史 message 和当前 message。
3. diary-soul.md。
4. 三个技能及其工具 schema。
5. 当前第几次意图识别和信息补充，以及最多允许几次。

当前轮次：{state["iteration"]} / {state["max_iterations"]}

diary-soul.md:
{docs.get("diary-soul.md", "")}

skills:
{json.dumps(self.skill_registry.specs(), ensure_ascii=False, indent=2)}

history:
{json.dumps(state.get("chat_history", []), ensure_ascii=False)}

current user message:
{state["user_message"]}

已有 tool results:
{json.dumps(state.get("tool_results", []), ensure_ascii=False)}

返回 JSON only，格式：
{{
  "action": "call_tool" 或 "finish",
  "tool_name": "工具名或null",
  "tool_args": {{}},
  "continue_after_tool": true,
  "skip_response": false,
  "final_summary": "第一层最终结果摘要",
  "reasoning": "简短原因"
}}

如果用户只是要求修改 diary-soul.md 或 user-soul.md，并且 soul-manager 已完成处理，则 skip_response=true。
如果需要 diary 历史、chat 历史、保存 diary 或读取/修改 soul，请调用相应工具。"""

    def _trim_history(self, history: List[Dict[str, str]], runtime: Dict[str, Any]) -> List[Dict[str, str]]:
        max_total = int(runtime.get("history_max_chars", 12000))
        max_each = int(runtime.get("message_max_chars", 2000))
        selected: List[Dict[str, str]] = []
        total = 0
        for msg in reversed(history):
            content = (msg.get("content") or "")[-max_each:]
            item = {"role": msg.get("role", "user"), "content": content, "length": len(content)}
            if total + len(content) > max_total:
                break
            selected.append(item)
            total += len(content)
        return list(reversed(selected))

    def _soul_only_response(self, final: Dict[str, Any]) -> str:
        tool_results = final.get("tool_results") or []
        last = tool_results[-1]["result"] if tool_results else {}
        if isinstance(last, dict) and last.get("status") == "applied":
            return "已完成 soul 文档更新，并记录了变更日志。"
        if isinstance(last, dict) and last.get("status") == "rejected":
            return f"这次 soul 文档修改未通过校验：{last.get('validation', {}).get('reason', '未说明原因')}"
        return "已完成第一层处理。"


def _extract_json(content: str) -> str:
    start = content.find("{")
    end = content.rfind("}") + 1
    if start >= 0 and end > start:
        return content[start:end]
    return content
