from __future__ import annotations
"""Central configuration for real LLM integration.

Environment variables:
  OPENAI_API_KEY     API key for OpenAI compatible endpoint
  OPENAI_MODEL_NAME  Model override (default: gpt-4o-mini)
"""
import os
from typing import Dict, Any, Union

DEFAULT_MODEL = os.getenv("OPENAI_MODEL_NAME", "gpt-4o-mini")


def create_llm_config(timeout: int = 60) -> Union[Dict[str, Any], bool]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return False  # Autogen convention to disable LLM client
    return {
        "config_list": [
            {"model": DEFAULT_MODEL, "api_key": api_key},
        ],
        "timeout": timeout,
    }


def describe_key_setup() -> str:
    return (
        "Set OPENAI_API_KEY (and optionally OPENAI_MODEL_NAME). "
        f"Current default model: {DEFAULT_MODEL}."
    )

__all__ = ["create_llm_config", "describe_key_setup", "DEFAULT_MODEL"]
