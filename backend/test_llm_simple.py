#!/usr/bin/env python3
"""Simple test for LLM in Docker."""

from langchain_core.messages import HumanMessage, SystemMessage
from llm import get_llm

def test_llm():
    print("Testing LLM connection...")

    # Get LLM instance
    llm = get_llm()
    print(f"Model: {llm.model_name}")
    print(f"Base URL: {llm.openai_api_base}")

    # Simple test
    messages = [
        SystemMessage(content="You are a helpful assistant."),
        HumanMessage(content="Say 'Hello from Docker!' and nothing else.")
    ]

    print("\nSending request...")
    response = llm.invoke(messages)
    print(f"\nResponse: {response.content}")

    print("\nTest passed!")

if __name__ == "__main__":
    test_llm()
