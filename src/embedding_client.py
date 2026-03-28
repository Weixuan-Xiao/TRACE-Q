from __future__ import annotations

import os
from typing import List, Optional

from dotenv import load_dotenv
from openai import OpenAI


class EmbeddingClient:
    """Minimal wrapper around OpenAI embeddings for structure discovery."""

    def __init__(self, model: Optional[str] = None) -> None:
        load_dotenv(override=False)
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError("Missing OPENAI_API_KEY in environment/.env")
        self.model = model or os.getenv("OPENAI_EMBEDDING_MODEL", "").strip()
        if not self.model:
            raise RuntimeError("Missing OPENAI_EMBEDDING_MODEL in environment/.env")
        self._client = OpenAI(api_key=api_key)

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        response = self._client.embeddings.create(model=self.model, input=texts)
        return [list(item.embedding) for item in response.data]
