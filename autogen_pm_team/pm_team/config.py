"""Central configuration for Autogen PM Team real LLM integration.

Edit OPENAI_API_KEY in your environment rather than hardcoding secrets.

Usage:
    export OPENAI_API_KEY="sk-..."
    (Optional) export OPENAI_MODEL_NAME="gpt-4o-mini"

The create_llm_config() function returns a structure consumed by autogen's ConversableAgent.
If no key is present, returns False so calling code can fall back gracefully.
"""
from __future__ import annotations
import os
from typing import Dict, Any, Union

DEFAULT_MODEL = os.getenv("OPENAI_MODEL_NAME", "gpt-4o-mini")


def create_llm_config(timeout: int = 60) -> Union[Dict[str, Any], bool]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        # Returning False is the autogen convention to disable LLM client creation
        return False
    return {
        "config_list": [
            {
                "model": DEFAULT_MODEL,
                "api_key": api_key,
            }
        ],
        "timeout": timeout,
    }


def describe_key_setup() -> str:
    return (
        "Set environment variable OPENAI_API_KEY before running with --autogen. "
        "Optionally set OPENAI_MODEL_NAME to override default model (current: " + DEFAULT_MODEL + ")."
    )

__all__ = ["create_llm_config", "describe_key_setup", "DEFAULT_MODEL"]