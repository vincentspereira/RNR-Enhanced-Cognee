"""Exercise a built restricted image with invented records and scoped tokens.

Run as a script against a disposable service, not as a collected unit test.
The caller supplies the synthetic service URL and signing key via environment.
"""
import os
import time
import uuid

import httpx
import jwt


def main():
    origin = os.environ["RNR_QUALIFICATION_SERVICE_URL"]
    secret = os.environ["RNR_QUALIFICATION_JWT_SECRET"]
    tenant = "q_" + uuid.uuid4().hex[:20]

    def credential(project="one", role="api_client"):
        return {"Authorization": "Bearer " + jwt.encode({
            "sub": "container-qualification", "agent_id": "fixture-agent",
            "tenant": tenant, "project_id": project, "roles": [role],
            "exp": int(time.time()) + 300,
        }, secret, algorithm="HS256")}

    with httpx.Client(base_url=origin, timeout=5, trust_env=False, follow_redirects=False) as client:
        deadline = time.monotonic() + 30
        while True:
            try:
                response = client.get("/health/ready")
                if response.status_code == 200 and response.json().get("ready"):
                    break
            except httpx.TransportError:
                pass
            if time.monotonic() >= deadline:
                raise RuntimeError("Disposable image did not become ready within 30 seconds")
            time.sleep(0.25)

        body = {"content": "Synthetic container cedar fixture", "idempotency_key": "container-one",
                "evidence": {"kind": "inference", "source_id": "synthetic_container_source", "confidence": 0.4}}
        assert client.post("/v1/memories", json=body).status_code == 401
        assert client.post("/v1/memories", json=body, headers=credential(role="readonly")).status_code == 403
        first = client.post("/v1/memories", json=body, headers=credential())
        assert first.status_code == 200
        record = first.json()
        assert record["evidence"]["authority"] == "actor_submitted_unverified"
        assert record["evidence"]["declaration"] == body["evidence"]
        assert client.post("/v1/memories", json=body | {"evidence": {"verified": True}}, headers=credential()).status_code == 422
        repeated = client.post("/v1/memories", json=body, headers=credential())
        assert repeated.json()["id"] == record["id"]
        path = "/v1/memories/" + record["id"]
        assert client.get(path, headers=credential("two")).status_code == 404
        assert client.post("/v1/memories", json=body | {"project_id": "two"}, headers=credential()).status_code == 403
        recalled = client.post("/v1/memories/recall", json={"query": "cedar"}, headers=credential(role="readonly"))
        assert recalled.status_code == 200 and recalled.json()["results"][0]["id"] == record["id"]
        share = {"expected_version": 1, "target_project": "two"}
        assert client.post(path + "/share", json=share, headers=credential(role="admin")).status_code == 200
        shared = client.post("/v1/memories/recall", json={"query": "cedar"}, headers=credential("two"))
        assert shared.json()["results"][0]["shared"]
        assert client.post(path + "/share", json=share | {"revoke": True}, headers=credential(role="admin")).status_code == 200
        revoked = client.post("/v1/memories/recall", json={"query": "cedar"}, headers=credential("two"))
        assert revoked.json()["results"] == []
        corrected = client.patch(path, json={"expected_version": 1, "content": "Synthetic container birch fixture"}, headers=credential())
        assert corrected.status_code == 200 and corrected.json()["version"] == 2
        revised = client.get(path, headers=credential()).json()
        assert revised["evidence"]["source_review_required"]
        assert revised["provenance"]["supersedes_version"] == 1
        assert client.patch(path, json={"expected_version": 1, "content": "Stale fixture"}, headers=credential()).status_code == 409
        assert client.post(path + "/retract", json={"expected_version": 2}, headers=credential()).status_code == 200
        assert client.get(path, headers=credential()).status_code == 404
        assert client.patch(path, json={"expected_version": 3, "content": "Accidental resurrection"}, headers=credential()).status_code == 409
        status = client.get("/v1/memories/status", headers=credential())
        assert status.status_code == 200 and status.json()["active_records"] == 0
        assert status.json()["graph"] == os.getenv("RNR_EXPECTED_GRAPH_CAPABILITY", "unavailable")
        assert status.json()["encryption_key_id"] == os.getenv("RNR_EXPECTED_MEMORY_KEY_ID", "legacy_unnamed")
    print("Built-image authentication, retry, scope, recall, sharing/revocation, evidence, correction lineage, retraction and key-status checks passed.")


if __name__ == "__main__":
    main()
