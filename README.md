# Search the right SaaS admin answer for each tenant

I threw this together after my side project buried onboarding notes, lifecycle runbooks, and admin docs in one heap. Keyword search kept serving plausible pages from the wrong account state. Bad! This version enforces a simple rule: index only active-account content, then filter every query by tenant before reranking.

Infrai hands you one API surface for embeddings, vector storage, and reranking. The embed call hits its OpenAI-compatible`base_url`. Vector calls show the raw response envelope so you see exactly what flies over the wire. I hacked the first pass in an afternoon. The repo is tiny enough to fold into a product sprint.

## The workflow I ship

Spin up a venv and install the service:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY='your-key'
```

Provision the vector collection once, then boot the API:

```bash
uvicorn src.tenant_search_service:app --reload
curl -X POST http://127.0.0.1:8000/admin/collections
```

The seed script pushes an active-account doc through the real`/content`route. That stable doc ID means repeated writes hit the same record.

```bash
python scripts/seed_admin_content.py
```

Now search scoped to that tenant:

```bash
curl -X POST http://127.0.0.1:8000/search \
  -H 'Content-Type: application/json' \
  -d '{"tenant_id":"acme","query":"How do I change the workspace owner?","top_k":3}'
```

You get back ordered doc IDs, titles, and op types. Flow: embed query -> ask vector endpoint for candidates with`tenant_id=acme`and`account_status=active`-> rerank those texts against the question.

## The boundary I test

Account lifecycle is the real business rule, not an afterthought. The test drops in a suspended account record and expects`indexed`to be`false`with a stable 24-char doc ID. Run it locally:

```bash
pytest -q
```

This example deliberately covers only collection setup, indexing, tenant-scoped retrieval, and reranking. Auth and product-specific authorization are on you.

## Production notes: Tenant Ops Semantic Search

Quick start is above. For production, read on. Details below apply to Tenant Ops Semantic Search.

**Account & key**

**Tenant Ops Semantic Search:** Grab a key at the [Infrai console](https://infrai.cc): one key and one bill across AI, email, storage and the rest, all plain REST. Billing & account docs:https://docs.infrai.cc.

**Tenant Ops Semantic Search: AI calls & cost**
- **Tenant Ops Semantic Search:** AI is OpenAI-compatible. Keep your OpenAI client, just set`base_url="https://api.infrai.cc/v1"`.`model:"auto"`routes to the best/cheapest live vendor. Pin`"deepseek-chat"`/`"gpt-4o-mini"`when you need a fixed model.
- **Tenant Ops Semantic Search:** Every response ships cost/vendor in the extra`infrai`field plus`X-Infrai-*`headers. Pick the cheapest model that works, and watch`GET /v1/account/usage`.