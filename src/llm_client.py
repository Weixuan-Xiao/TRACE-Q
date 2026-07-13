from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from openai import OpenAI

Message = Dict[str, str]


@dataclass(frozen=True)
class LLMConfig:
    api_key: str
    model: str
    seed: Optional[int] = None  # For reproducibility
    base_url: Optional[str] = None  # None = api.openai.com; set for OpenAI-compatible gateways


class LLMClient:
    """
    Minimal wrapper around OpenAI Python SDK using chat.completions.
    """

    def __init__(self, config: Optional[LLMConfig] = None) -> None:
        load_dotenv(override=False)

        if config is None:
            api_key = os.getenv("OPENAI_API_KEY", "").strip()
            model = os.getenv("OPENAI_MODEL", "").strip()
            seed_str = os.getenv("OPENAI_SEED", "").strip()
            base_url = os.getenv("OPENAI_BASE_URL", "").strip() or None
            if not api_key:
                raise RuntimeError("Missing OPENAI_API_KEY in environment/.env")
            if not model:
                raise RuntimeError("Missing OPENAI_MODEL in environment/.env")
            seed = int(seed_str) if seed_str else None
            config = LLMConfig(api_key=api_key, model=model, seed=seed, base_url=base_url)

        self.config = config
        self._client = OpenAI(api_key=self.config.api_key, base_url=self.config.base_url)
        self.usage = {"input": 0, "output": 0, "calls": 0}
        self.temperature_fallbacks = 0  # calls where the model rejected the requested temperature

    def chat_completions(
        self,
        messages: List[Message],
        *,
        model: Optional[str] = None,
        temperature: float = 0.0,
        response_format: Optional[Dict[str, Any]] = None,
        seed: Optional[int] = None,
    ) -> str:
        payload: Dict[str, Any] = {
            "model": model or self.config.model,
            "messages": messages,
            "temperature": temperature,
        }
        # Use provided seed, or fall back to config seed
        effective_seed = seed if seed is not None else self.config.seed
        if effective_seed is not None:
            payload["seed"] = effective_seed
        if response_format is not None:
            payload["response_format"] = response_format

        for _attempt in range(3):
            try:
                resp = self._client.chat.completions.create(**payload)
                break
            except TypeError:
                if "response_format" in payload:
                    payload.pop("response_format")
                    continue
                raise
            except Exception as e:
                msg = str(e).lower()
                # Some models (e.g. GPT-5.x reasoning family) only support their
                # default temperature; retry without it and record the fallback.
                if "temperature" in payload and "'temperature'" in msg and "support" in msg:
                    payload.pop("temperature")
                    self.temperature_fallbacks += 1
                    continue
                # Some models reject response_format; retry once without it.
                if "response_format" in payload and ("response_format" in msg or "response format" in msg):
                    payload.pop("response_format")
                    continue
                raise
        else:
            raise RuntimeError("chat.completions retries exhausted")

        self._record_usage(payload["model"], getattr(resp, "usage", None))
        return (resp.choices[0].message.content or "").strip()

    def _record_usage(self, model: str, usage: Any) -> None:
        if usage is None:
            return
        input_tokens = getattr(usage, "prompt_tokens", 0) or 0
        output_tokens = getattr(usage, "completion_tokens", 0) or 0
        self.usage["input"] += input_tokens
        self.usage["output"] += output_tokens
        self.usage["calls"] += 1
        log_path = os.getenv("TOKEN_LOG_PATH")
        if log_path:
            with open(log_path, "a") as f:
                f.write(json.dumps({"model": model, "input": input_tokens,
                                    "output": output_tokens}) + "\n")


