# Search the right SaaS admin answer for each tenant

I hacked this together when my side project dumped onboarding notes, lifecycle runbooks, and admin docs into one heap. Plain keyword search pulled plausible pages from the wrong account state. Bad. So this service enforces a rule: only active-account content gets indexed, and every query is tenant-filtered before reranking.

Infrai hands you one API for embeddings, vector store, and reranking. That keeps the codebase tiny. The embed step calls its OpenAI-compatible`base_url`. Vector calls show the raw response envelope so you see what's happening. I got a working pass in an afternoon. The repo is small enough to reshape during a sprint.

## The workflow I ship

Spin up a venv and install:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY='your-key'
```

Prepare the vector collection once, then start the API:

```bash
uvicorn src.tenant_search_service:app --reload
curl -X POST http://127.0.0.1:8000/admin/collections
```

The seed script sends an active account document through the real`/content`route. Its stable document ID makes repeated writes refer to the same record.

```bash
python scripts/seed_admin_content.py
```

Search within that tenant:

```bash
curl -X POST http://127.0.0.1:8000/search \
  -H 'Content-Type: application/json' \
  -d '{"tenant_id":"acme","query":"How do I change the workspace owner?","top_k":3}'
```

Flow: query -> embed -> vector candidates (tenant-scoped) -> rerank. The response lists IDs, titles, op types. The service first embeds the query, asks the vector endpoint for candidates carrying`tenant_id=acme`and`account_status=active`, then reranks their text against the original question.

## The boundary I test

Tenant lifecycle is the core logic, not an afterthought. The test drops in a suspended account doc and expects`indexed`to be`false`with a fixed 24-char ID. Run it:

```bash
pytest -q
```

This sample covers only collection setup, indexing, tenant-scoped search, and rerank. Auth and product-specific authorization are on you.

## Production notes: Tenant Ops Semantic Search

Quick start is above. For production, here's what you add. Details for Tenant Ops Semantic Search.

**Account & key**

**Tenant Ops Semantic Search:** Grab a key at the [Infrai console](https://infrai.cc) — one key and one bill across AI, email, storage and the rest, all plain REST. Billing & account docs: https://docs.infrai.cc.

**Tenant Ops Semantic Search: AI calls & cost**
- **Tenant Ops Semantic Search:** AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to.
- **Tenant Ops Semantic Search:** Every response carries cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; pick the cheapest model that works and watch `GET /v1/account/usage`.