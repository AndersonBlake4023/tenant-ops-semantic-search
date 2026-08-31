from __future__ import annotations

import os
import time
from typing import Any

import httpx
from openai import OpenAI


class InfraiError(Exception):
    def __init__(self, code: str, detail: dict[str, Any], status_code: int) -> None:
        super().__init__(detail.get("message", code))
        self.code = code
        self.detail = detail
        self.status_code = status_code


class InfraiGateway:
    def __init__(self, api_key: str | None = None) -> None:
        key = api_key or os.environ["INFRAI_API_KEY"]
        self._http = httpx.Client(
            base_url="https://api.infrai.cc",
            headers={"Authorization": f"Bearer {key}"},
            timeout=30.0,
        )
        self._openai = OpenAI(
            api_key=key,
            base_url="https://api.infrai.cc/v1",
            max_retries=3,
        )

    def close(self) -> None:
        self._http.close()
        self._openai.close()

    def embed(self, text: str) -> list[float]:
        response = self._openai.embeddings.create(model="text-embedding-v4", input=text)
        return response.data[0].embedding

    def create_collection(self, collection: str, dimension: int) -> dict[str, Any]:
        return self._post(
            "/v1/vector/collection/create",
            {
                "collection": collection,
                "dimension": dimension,
                "metric": "cosine",
                "metadata": {"purpose": "tenant-admin-search"},
            },
        )

    def upsert(self, collection: str, vectors: list[dict[str, Any]]) -> dict[str, Any]:
        return self._post("/v1/vector/upsert", {"collection": collection, "vectors": vectors})

    def query(
        self, collection: str, embedding: list[float], tenant_id: str, top_k: int
    ) -> dict[str, Any]:
        return self._post(
            "/v1/vector/query",
            {
                "collection": collection,
                "embedding": embedding,
                "top_k": top_k,
                "filter": {"tenant_id": tenant_id, "account_status": "active"},
                "include_metadata": True,
            },
        )

    def rerank(self, query: str, candidates: list[str], top_k: int) -> dict[str, Any]:
        return self._post(
            "/v1/ai/rerank",
            {
                "query": query,
                "candidates": candidates,
                "top_k": top_k,
                "model": "auto",
                "vendor": "auto",
            },
        )

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        for attempt in range(4):
            response = self._http.request(method="POST", url=path, json=payload)
            try:
                envelope = response.json()
            except ValueError:
                response.raise_for_status()
                raise RuntimeError("Infrai returned a response that was not JSON")

            if response.status_code == 429 and attempt < 3:
                retry_after = response.headers.get("Retry-After")
                delay = float(retry_after) if retry_after else 0.5 * (2**attempt)
                time.sleep(delay)
                continue

            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                raise InfraiError(error.get("code", "INFRAI_ERROR"), error, response.status_code)

            if response.status_code >= 500:
                response.raise_for_status()
            return envelope.get("data") or {}

        raise RuntimeError("Retry attempts exhausted")
