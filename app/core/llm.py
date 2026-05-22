from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv

load_dotenv()


class OpenAIClient:
    """Wrapper around OpenAI SDK. Uses new `openai>=1.x` API when available,
    and falls back to the legacy `openai` usage if needed.

    The public method `create_chat_completion(messages, ...)` remains unchanged.
    """

    def __init__(self) -> None:
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.base_url = os.getenv("OPENAI_BASE_URL")
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

        # Try to import new OpenAI client API
        try:
            from openai import OpenAI as OpenAINew  # type: ignore

            # construct client with provided credentials (if any)
            client_kwargs: dict[str, Any] = {}
            if self.api_key:
                client_kwargs["api_key"] = self.api_key
            if self.base_url:
                client_kwargs["base_url"] = self.base_url
            self._client = OpenAINew(**client_kwargs)
            self._mode = "new"
        except Exception:
            # Fallback to legacy `openai` module usage
            try:
                import openai as _openai  # type: ignore

                if self.api_key:
                    _openai.api_key = self.api_key
                if self.base_url:
                    _openai.api_base = self.base_url
                self._client = _openai
                self._mode = "legacy"
            except Exception:
                self._client = None
                self._mode = "none"

    def create_chat_completion(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        model: str | None = None,
    ) -> str:
        """Create a chat completion using the configured OpenAI client.

        Tries to use `client.chat.completions.create(...)` (new SDK). If not
        available, falls back to legacy `openai.ChatCompletion.create(...)`.
        """
        if self._mode == "new" and self._client is not None:
            try:
                resp = self._client.chat.completions.create(
                    model=model or self.model,
                    messages=messages,
                    temperature=temperature,
                )
                return self._extract_content(resp)
            except Exception:
                # fallthrough to fallback simulation
                return self._fallback_simulation(messages)

        if self._mode == "legacy" and self._client is not None:
            try:
                resp = self._client.ChatCompletion.create(
                    model=model or self.model,
                    messages=messages,
                    temperature=temperature,
                )
                return self._extract_content(resp)
            except Exception:
                return self._fallback_simulation(messages)

        return self._fallback_simulation(messages)

    def create_chat_completion_strict(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        model: str | None = None,
    ) -> str:
        """Create a chat completion and raise on API/client failures.

        RAG endpoints use this method so user-facing responses never contain
        the local fallback prompt simulation when the LLM call fails.
        """
        if self._mode == "new" and self._client is not None:
            try:
                resp = self._client.chat.completions.create(
                    model=model or self.model,
                    messages=messages,
                    temperature=temperature,
                )
                content = self._extract_content(resp)
            except Exception as exc:
                raise RuntimeError(f"OpenAI chat completion failed: {exc}") from exc

            if not content.strip():
                raise RuntimeError("OpenAI chat completion returned empty content.")
            return content.strip()

        if self._mode == "legacy" and self._client is not None:
            try:
                resp = self._client.ChatCompletion.create(
                    model=model or self.model,
                    messages=messages,
                    temperature=temperature,
                )
                content = self._extract_content(resp)
            except Exception as exc:
                raise RuntimeError(f"OpenAI chat completion failed: {exc}") from exc

            if not content.strip():
                raise RuntimeError("OpenAI chat completion returned empty content.")
            return content.strip()

        raise RuntimeError("OpenAI chat completion client is not available.")

    def _extract_content(self, resp: Any) -> str:
        """Try multiple strategies to extract text content from various SDK response shapes."""
        # If it's a mapping-like object
        try:
            # support new SDK response objects
            if hasattr(resp, "choices") and resp.choices:
                first = resp.choices[0]
                # try message.content
                if hasattr(first, "message"):
                    msg = first.message
                    if isinstance(msg, dict):
                        content = msg.get("content")
                    else:
                        content = getattr(msg, "content", None)
                    if content:
                        return str(content).strip()

                # try text field
                if hasattr(first, "text"):
                    return str(getattr(first, "text")).strip()

            # dict-like access
            if isinstance(resp, dict):
                choices = resp.get("choices") or resp.get("data")
                if choices and len(choices) > 0:
                    first = choices[0]
                    if isinstance(first, dict):
                        # new SDK sometimes nests message as {'message': {'content': ...}}
                        if "message" in first and isinstance(first["message"], dict):
                            content = first["message"].get("content")
                            if content:
                                return str(content).strip()
                        if "text" in first and first.get("text"):
                            return str(first.get("text")).strip()

            # try attribute access for newer response models
            if hasattr(resp, "data") and resp.data:
                first = resp.data[0]
                if hasattr(first, "message"):
                    msg = first.message
                    content = getattr(msg, "content", None) or (msg.get("content") if isinstance(msg, dict) else None)
                    if content:
                        return str(content).strip()
        except Exception:
            pass

        # Fallback: stringify response
        try:
            return str(resp)
        except Exception:
            return ""

    def _fallback_simulation(self, messages: list[dict[str, str]]) -> str:
        prompt_text = " ".join([m["content"] for m in messages if m.get("role") in {"user", "system"}])
        return (
            "[模拟输出] 由于未配置或调用失败，系统返回本地生成内容。"
            "\n\n" + (prompt_text[:800] if prompt_text else "")
        )
