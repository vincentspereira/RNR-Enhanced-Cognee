"""Exercise actual API/worker containers with four real stores and invented facts."""
import os
import subprocess
import time
import uuid

import httpx
import jwt

from container_smoke import main as core_smoke


def main():
    if os.getenv("RNR_ALLOW_SYNTHETIC_CONTAINERS") != "1":
        raise ValueError("Explicitly select invented-data container qualification")
    tenant = "image_"+uuid.uuid4().hex[:20]

    def credential(project="one"):
        return {"Authorization": "Bearer "+jwt.encode({"sub": "synthetic_image_owner", "tenant": tenant,
            "project_id": project, "agent_id": "synthetic_agent", "roles": ["api_client"],
            "exp": int(time.time())+300}, os.environ["RNR_QUALIFICATION_JWT_SECRET"], algorithm="HS256")}

    with httpx.Client(base_url=os.environ["RNR_QUALIFICATION_SERVICE_URL"], timeout=10, trust_env=False) as http:
        def status():
            response = http.get("/v1/memories/status", headers=credential())
            response.raise_for_status()
            return response.json()

        def caught_up():
            deadline = time.monotonic()+30
            while True:
                try:
                    value = status()
                    if value["index"]["worker_available"] and value["pending_change_events"] == 0:
                        assert value["retrieval"] == "semantic"
                        return
                except (httpx.HTTPError, KeyError):
                    pass
                if time.monotonic() >= deadline:
                    raise RuntimeError("Actual container indexes did not become ready and caught up")
                time.sleep(.25)

        def remember(content, subject, obj, key):
            body = {"content": content, "idempotency_key": key,
                "knowledge_links": [{"subject": subject, "predicate": "related to", "object": obj,
                                     "span_start": 0, "span_end": len(content)}]}
            response = http.post("/v1/memories", json=body, headers=credential())
            response.raise_for_status()
            again = http.post("/v1/memories", json=body, headers=credential())
            assert again.json()["id"] == response.json()["id"]
            return response.json()

        caught_up()
        first = remember("Cedar depends on Birch.", "Cedar", "Birch", "image-one")
        second = remember("Birch stores its recovery copies in Lisbon.", "Birch", "Lisbon", "image-two")
        caught_up()
        graph = http.post("/v1/memories/connections", json={"entity": "Cedar", "depth": 2}, headers=credential())
        assert graph.status_code == 200 and graph.json()["paths"][-1][-1]["object"] == "Lisbon"
        assert {edge["record_id"] for edge in graph.json()["paths"][-1]} == {first["id"], second["id"]}
        assert http.get("/v1/memories/"+first["id"], headers=credential("other")).status_code == 404
        # Stop/restart only the explicitly named fixture worker; keep all data.
        label = subprocess.check_output(["docker", "inspect", "--format",
            '{{index .Config.Labels "rnr.cognee.qualification"}}', "canonical-memory-index"], text=True).strip()
        if label != "synthetic":
            raise ValueError("Refusing to stop a container without the synthetic qualification label")
        subprocess.run(["docker", "stop", "canonical-memory-index"], check=True, stdout=subprocess.DEVNULL)
        assert not status()["index"]["worker_available"]
        pending = remember("Orchid uses a nine-day review cycle.", "Orchid", "review", "image-pending")
        assert status()["pending_change_events"] >= 1
        recall = http.post("/v1/memories/recall", json={"query": "Orchid nine-day reviews"}, headers=credential()).json()
        assert any(item["id"] == pending["id"] for item in recall["results"])
        subprocess.run(["docker", "start", "canonical-memory-index"], check=True, stdout=subprocess.DEVNULL)
        caught_up()
        content = "Cedar depends on Maple."
        changed = http.patch("/v1/memories/"+first["id"], headers=credential(), json={"content": content,
            "expected_version": 1, "knowledge_links": [{"subject": "Cedar", "predicate": "depends on", "object": "Maple",
                                                         "span_start": 0, "span_end": len(content)}]})
        assert changed.status_code == 200
        caught_up()
        paths = http.post("/v1/memories/connections", json={"entity": "Cedar", "depth": 2}, headers=credential()).json()["paths"]
        assert len(paths) == 1 and paths[0][0]["object"] == "Maple" and paths[0][0]["version"] == 2
        assert http.post("/v1/memories/"+first["id"]+"/retract", headers=credential(), json={"expected_version": 2}).status_code == 200
        caught_up()
        assert http.post("/v1/memories/connections", json={"entity": "Cedar"}, headers=credential()).json()["paths"] == []
        assert len(http.get("/v1/memories/"+first["id"]+"/history", headers=credential()).json()["versions"]) == 3
    os.environ["RNR_EXPECTED_GRAPH_CAPABILITY"] = "source_linked_graph"
    core_smoke()
    print("Actual restricted API/worker images: semantic/source-linked recall, restart/backlog recovery, scope, correction and retraction passed")


if __name__ == "__main__":
    main()
