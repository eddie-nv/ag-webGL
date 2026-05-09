"""Shared pytest fixtures for evals + e2e tests."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

# Auto-load .env from the project root so e2e tests pick up ANTHROPIC_API_KEY
# without requiring `export` in the shell.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(_PROJECT_ROOT / ".env")


@pytest.fixture(scope="session")
def real_llm():
    """Real Anthropic-backed LLMClient. Skips the test when no API key is set."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        pytest.skip("ANTHROPIC_API_KEY not set; skipping e2e test")
    from agent.llm import AnthropicLLM

    return AnthropicLLM()
