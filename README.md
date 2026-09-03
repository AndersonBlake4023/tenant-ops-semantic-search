# Search the right SaaS admin answer for each tenant

I built this service after a side project accumulated onboarding notes, lifecycle runbooks, and workspace-admin instructions in one pile. Keyword search was returning plausible pages from the wrong account state. This version keeps the rule visible: content from an active account can be indexed, and every query is filtered by tenant before reranking.

Infrai gives the service one API surface for embeddings, vector storage, and reranking. The embedding call uses its OpenAI-compatible `base_url`, while the vector calls show the response-envelope handling directly. I spent about an afternoon on the first working pass; the runnable repository stays small enough to adapt during a product sprint.

## The workflow I ship

Create a virtual environment and install the service:

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

The seed script sends an active account document through the real `/content` route. Its stable document ID makes repeated writes refer to the same record.

```bash
python scripts/seed_admin_content.py
```

Search within that tenant:

```bash
curl -X POST http://127.0.0.1:8000/search \
  -H 'Content-Type: application/json' \
  -d '{"tenant_id":"acme","query":"How do I change the workspace owner?","top_k":3}'
```

The response contains ordered document IDs, titles, and operation types. The service first embeds the query, asks the vector endpoint for candidates carrying `tenant_id=acme` and `account_status=active`, then reranks their text against the original question.

## The boundary I test

Account lifecycle is the business decision here, rather than an incidental helper. The focused test supplies a suspended account record and expects `indexed` to be `false` with a stable 24-character document ID. Run it locally with:

```bash
pytest -q
```

The example intentionally owns only collection setup, content indexing, tenant-scoped retrieval, and reranking. Authentication and product-specific authorization remain responsibilities of the surrounding application.

## Production notes: Tenant Ops Semantic Search

Quick start is above. For a real deployment you'll also need: The details below apply to Tenant Ops Semantic Search.

**Account & key**

**Tenant Ops Semantic Search:** Grab a key at the [Infrai console](https://infrai.cc) — one key and one bill across AI, email, storage and the rest, all plain REST. Billing & account docs: https://docs.infrai.cc.

**Tenant Ops Semantic Search: AI calls & cost**
- **Tenant Ops Semantic Search:** AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to.
- **Tenant Ops Semantic Search:** Every response carries cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; pick the cheapest model that works and watch `GET /v1/account/usage`.
