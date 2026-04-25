"""Integration tests for the submission HTTP API."""

import pytest
from httpx import AsyncClient


@pytest.mark.integration
class TestCreateSubmission:
    async def test_returns_201_on_success(
        self, client: AsyncClient, sample_submission_payload: dict
    ):
        response = await client.post("/v1/submissions", json=sample_submission_payload)

        assert response.status_code == 201, response.text

    async def test_response_has_system_fields(
        self, client: AsyncClient, sample_submission_payload: dict
    ):
        response = await client.post("/v1/submissions", json=sample_submission_payload)

        body = response.json()
        assert "id" in body
        assert body["reference"] == "BRK-TEST-0001"
        assert body["status"] == "received"
        assert body["fleet_size"] == 1
        assert body["total_fleet_value"] == "25000"

    async def test_returns_409_for_duplicate_reference(
        self, client: AsyncClient, sample_submission_payload: dict
    ):
        first = await client.post("/v1/submissions", json=sample_submission_payload)
        assert first.status_code == 201

        second = await client.post("/v1/submissions", json=sample_submission_payload)

        assert second.status_code == 409
        assert "already exists" in second.json()["detail"]

    async def test_returns_422_for_invalid_payload(self, client: AsyncClient):
        response = await client.post("/v1/submissions", json={"reference": "X"})

        assert response.status_code == 422

    async def test_returns_422_for_empty_fleet(
        self, client: AsyncClient, sample_submission_payload: dict
    ):
        sample_submission_payload["vehicles"] = []

        response = await client.post("/v1/submissions", json=sample_submission_payload)

        assert response.status_code == 422


@pytest.mark.integration
class TestGetSubmission:
    async def test_returns_submission_by_id(
        self, client: AsyncClient, sample_submission_payload: dict
    ):
        create_response = await client.post("/v1/submissions", json=sample_submission_payload)
        submission_id = create_response.json()["id"]

        get_response = await client.get(f"/v1/submissions/{submission_id}")

        assert get_response.status_code == 200
        assert get_response.json()["id"] == submission_id

    async def test_returns_404_for_unknown_id(self, client: AsyncClient):
        response = await client.get("/v1/submissions/00000000-0000-0000-0000-000000000000")

        assert response.status_code == 404


@pytest.mark.integration
class TestListSubmissions:
    async def test_returns_empty_list_when_no_submissions(self, client: AsyncClient):
        response = await client.get("/v1/submissions")

        assert response.status_code == 200
        body = response.json()
        assert body["items"] == []
        assert body["total"] == 0

    async def test_returns_created_submissions(
        self, client: AsyncClient, sample_submission_payload: dict
    ):
        await client.post("/v1/submissions", json=sample_submission_payload)

        response = await client.get("/v1/submissions")

        body = response.json()
        assert body["total"] == 1
        assert len(body["items"]) == 1
        assert body["items"][0]["reference"] == "BRK-TEST-0001"

    async def test_paginates_results(self, client: AsyncClient, sample_submission_payload: dict):
        for i in range(5):
            payload = {**sample_submission_payload, "reference": f"BRK-TEST-{i:04d}"}
            await client.post("/v1/submissions", json=payload)

        response = await client.get("/v1/submissions?limit=2&offset=0")

        body = response.json()
        assert body["total"] == 5
        assert len(body["items"]) == 2
        assert body["limit"] == 2
        assert body["offset"] == 0


@pytest.mark.integration
class TestHealthCheck:
    async def test_health_returns_ok(self, client: AsyncClient):
        response = await client.get("/health")

        assert response.status_code == 200
        assert response.json()["status"] == "ok"
