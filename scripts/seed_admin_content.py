import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.tenant_search_service import app


def main() -> None:
    record = {
        "tenant_id": "acme",
        "account_id": "account-42",
        "account_status": "active",
        "title": "Transfer workspace ownership",
        "body": "An organization admin can transfer ownership from the workspace settings page.",
        "operation": "admin_operation",
    }
    with TestClient(app) as client:
        response = client.post("/content", json=record)
        response.raise_for_status()
        print(response.json())


if __name__ == "__main__":
    main()
