from src.tenant_search_service import ContentRecord, indexing_decision


def test_suspended_account_content_stays_out_of_search() -> None:
    record = ContentRecord(
        tenant_id="acme",
        account_id="account-42",
        account_status="suspended",
        title="Invite a workspace administrator",
        body="Open workspace settings and assign the administrator role.",
        operation="tenant_onboarding",
    )

    result = indexing_decision(record)

    assert result.indexed is False
    assert result.reason == "Only active accounts are searchable"
    assert len(result.document_id) == 24
