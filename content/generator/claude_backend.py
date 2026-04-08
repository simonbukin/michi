"""Drop-in replacement for anthropic.Anthropic() that uses `claude -p` subprocess.

Provides the same client.messages.create() interface so existing code
(outline_gen, prose_gen, correction_gen) works without changes.

Requires `claude` CLI to be installed and authenticated.
"""

import subprocess
import json
from dataclasses import dataclass


@dataclass
class TextBlock:
    text: str
    type: str = "text"


@dataclass
class MessageResponse:
    content: list[TextBlock]


class Messages:
    """Mimics anthropic.Anthropic().messages interface using claude -p."""

    def create(self, *, model: str = "sonnet", max_tokens: int = 4096,
               system: str = "", messages: list[dict],
               **kwargs) -> MessageResponse:
        # Build the prompt from messages
        user_text = ""
        for msg in messages:
            if msg["role"] == "user":
                user_text = msg["content"]
                break

        # Combine system + user into a single prompt for claude -p
        full_prompt = ""
        if system:
            full_prompt = f"{system}\n\n"
        full_prompt += user_text

        # Map model names to claude CLI model flags
        model_flag = "sonnet"
        if "opus" in model.lower():
            model_flag = "opus"
        elif "haiku" in model.lower():
            model_flag = "haiku"

        cmd = [
            "claude", "-p",
            "--output-format", "text",
            "--allowedTools", "",
            "--model", model_flag,
            full_prompt,
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
        )

        if result.returncode != 0:
            raise RuntimeError(
                f"claude -p failed (exit {result.returncode}): {result.stderr[:500]}")

        return MessageResponse(content=[TextBlock(text=result.stdout.strip())])


class ClaudeCodeClient:
    """Drop-in replacement for anthropic.Anthropic() using claude CLI."""

    def __init__(self):
        self.messages = Messages()
