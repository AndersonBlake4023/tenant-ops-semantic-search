from __future__ import annotations

import hashlib
from typing import Any, Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .infrai_gateway import InfraiError, InfraiGateway

COLLECTION = "saas-operations"


class ContentRecord(BaseModel):
    tenant_id: str = Field(min_length=1)
    account_id: str = Field(min_length=1)
    account_status: Literal["onboarding", "active", "suspended", "closed"]
    title: str = Field(min_length=1)
    body: str = Field(min_length=1)
    operation: Literal["tenant_onboarding", "account_lifecycle", "admin_operation"]


class IndexResult(BaseModel):
    document_id: str
    indexed: bool
    reason: str


class SearchRequest(BaseModel):
    tenant_id: str = Field(min_length=1)
    query: str = Field(min_length=2)
    top_k: int = Field(default=5, ge=1, le=20)


class SearchHit(BaseModel):
    document_id: str
    title: str
    operation: str


class SearchResponse(BaseModel):
    hits: list[SearchHit]


def indexing_decision(record: ContentRecord) -> IndexResult:
    document_id = hashlib.sha256(
        f"{record.tenant_id}:{record.account_id}:{record.title}".encode()
    ).hexdigest()[:24]
    if record.account_status != "active":
        return IndexResult(
            document_id=document_id,
            indexed=False,
            reason="Only active accounts are searchable",
        )
    return IndexResult(document_id=document_id, indexed=True, reason="Active account content")


app = FastAPI(title="B2B SaaS operations search")


def gateway() -> InfraiGateway:
    return InfraiGateway()


@app.post("/admin/collections", response_model=dict[str, Any])
def prepare_collection() -> dict[str, Any]:
    client = gateway()
    try:
        probe = client.embed("tenant onboarding")
        return client.create_collection(COLLECTION, len(probe))
    except InfraiError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    finally:
        client.close()


@app.post("/content", response_model=IndexResult)
def index_content(record: ContentRecord) -> IndexResult:
    decision = indexing_decision(record)
    if not decision.indexed:
        return decision

    client = gateway()
    try:
        embedding = client.embed(f"{record.title}\n{record.body}")
        client.upsert(
            COLLECTION,
            [
                {
                    "id": decision.document_id,
                    "embedding": embedding,
                    "metadata": record.model_dump(),
                }
            ],
        )
        return decision
    except InfraiError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    finally:
        client.close()


@app.post("/search", response_model=SearchResponse)
def search(request: SearchRequest) -> SearchResponse:
    client = gateway()
    try:
        embedding = client.embed(request.query)
        result = client.query(COLLECTION, embedding, request.tenant_id, request.top_k * 2)
        matches = result.get("matches", [])
        candidates = [f"{m['metadata']['title']}\n{m['metadata']['body']}" for m in matches]
        if not candidates:
            return SearchResponse(hits=[])
        ranked = client.rerank(request.query, candidates, request.top_k)
        ordered = ranked.get("results", [])
        hits = []
        for item in ordered:
            match = matches[item["index"]]
            metadata = match["metadata"]
            hits.append(
                SearchHit(
                    document_id=match["id"],
                    title=metadata["title"],
                    operation=metadata["operation"],
                )
            )
        return SearchResponse(hits=hits)
    except InfraiError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    finally:
        client.close()
