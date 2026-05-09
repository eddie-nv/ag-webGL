"""LLMClient adapter wrapping langchain-anthropic for production runs.

Tests pass a deterministic stub (StubLLM / CycleStubLLM in agent/evals/).
M8 plus runtime use this adapter against a real Anthropic API.
"""

from __future__ import annotations

import os
import re

DEFAULT_MODEL = "claude-sonnet-4-6"

_FENCE_RE = re.compile(r"```(?:json)?\s*\n?(.*?)\n?```", re.DOTALL)


def _extract_json(text: str) -> str:
    """Extract a JSON object/array from a possibly-chatty LLM response.

    Tries (in order):
    1. ```json ... ``` fenced block (real LLMs love these despite prompt rules)
    2. The substring from the first '{' / '[' to its matching close
    3. The original text (Pydantic will surface a clearer error)
    """
    text = text.strip()

    fence_match = _FENCE_RE.search(text)
    if fence_match:
        return fence_match.group(1).strip()

    obj_start = text.find("{")
    arr_start = text.find("[")
    candidates = [i for i in (obj_start, arr_start) if i >= 0]
    if not candidates:
        return text

    start = min(candidates)
    closer = "}" if text[start] == "{" else "]"
    end = text.rfind(closer)
    if end > start:
        return text[start : end + 1].strip()

    return text


class AnthropicLLM:
    """Adapter to satisfy agent.agents.types.LLMClient.

    Lazy-imports langchain_anthropic so test runs that never instantiate this
    class don't pay the import cost (and don't require ANTHROPIC_API_KEY).
    """

    def __init__(self, model: str | None = None, temperature: float = 0.0) -> None:
        from langchain_anthropic import ChatAnthropic

        resolved_model = model or os.environ.get("SCENE_LLM_MODEL", DEFAULT_MODEL)
        self._model = ChatAnthropic(model=resolved_model, temperature=temperature)

    def invoke(self, prompt: str) -> str:
        from langchain_core.messages import HumanMessage

        result = self._model.invoke([HumanMessage(content=prompt)])
        content = result.content

        if isinstance(content, str):
            return _extract_json(content)

        # Anthropic responses may arrive as a list of content blocks.
        text = "".join(
            block["text"] if isinstance(block, dict) and "text" in block else str(block)
            for block in content
        )
        return _extract_json(text)
