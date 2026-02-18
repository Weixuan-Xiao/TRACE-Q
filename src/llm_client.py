from __future__ import annotations

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
            if not api_key:
                raise RuntimeError("Missing OPENAI_API_KEY in environment/.env")
            if not model:
                raise RuntimeError("Missing OPENAI_MODEL in environment/.env")
            seed = int(seed_str) if seed_str else None
            config = LLMConfig(api_key=api_key, model=model, seed=seed)

        self.config = config
        self._client = OpenAI(api_key=self.config.api_key)

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

        try:
            resp = self._client.chat.completions.create(**payload)
        except TypeError:
            payload.pop("response_format", None)
            resp = self._client.chat.completions.create(**payload)
        except Exception as e:
            # Some models reject response_format; retry once without it.
            if response_format is not None and ("response_format" in str(e) or "response format" in str(e).lower()):
                payload.pop("response_format", None)
                resp = self._client.chat.completions.create(**payload)
            else:
                raise

        return (resp.choices[0].message.content or "").strip()


