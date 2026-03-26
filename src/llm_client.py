from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv
from openai import OpenAI

logger = logging.getLogger(__name__)

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

    _warned: bool = False  # class-level flag: only warn once per process

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
            if not LLMClient._warned:
                LLMClient._warned = True
                if seed is None:
                    logger.warning(
                        "OPENAI_SEED not set — results will NOT be reproducible. "
                        "Set OPENAI_SEED in .env for deterministic runs."
                    )
                import re
                if not re.search(r"-\d{4}-\d{2}-\d{2}", model):
                    logger.warning(
                        "OPENAI_MODEL='%s' looks like an alias, not a pinned snapshot. "
                        "For reproducibility, use a dated model ID (e.g., "
                        "gpt-5.4-2025-04-14 instead of gpt-5.4).", model
                    )
            config = LLMConfig(api_key=api_key, model=model, seed=seed)

        self.config = config
        self._client = OpenAI(api_key=self.config.api_key)
        # Accumulated system_fingerprints from all calls (for reproducibility auditing)
        self.fingerprints: List[str] = []

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

        # Capture system_fingerprint for reproducibility auditing
        fp = getattr(resp, "system_fingerprint", None)
        if fp:
            self.fingerprints.append(fp)

        return (resp.choices[0].message.content or "").strip()


