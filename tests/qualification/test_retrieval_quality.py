"""Small, explicit English retrieval set; not a general accuracy benchmark.

Runs with the prepared local model and a disposable PostgreSQL database. Reports
top-three recall and query latency, and retains all synthetic data for inspection.
"""
import json
import math
import os
from pathlib import Path
import statistics
import time
import uuid

import asyncpg
from cryptography.fernet import Fernet
import pytest

from src.encryption_manager import EncryptionManager
from src.local_embeddings import LocalEmbeddings
from src.memory_service import MemoryScope, MemoryService


CASES = [
    ("Cedar reviews", "Cedar holds its planning review every eleven days.", "How frequently does Cedar reassess its plans?"),
    ("Birch database", "Birch's primary database is hosted in Lisbon.", "Where is the main Birch data store located?"),
    ("Maple backup", "Maple encrypts its backups before sending them to offsite storage.", "How does Maple protect archived recovery copies?"),
    ("Aspen approval", "Aspen requires a human approval before publishing a release.", "Who must authorize Aspen's software publication?"),
    ("Willow retention", "Willow keeps inactive records for ninety days.", "For how long does Willow retain dormant entries?"),
    ("Oak upload", "Oak accepts uploaded documents up to twenty-five megabytes.", "What is the largest file Oak will accept?"),
    ("Elm languages", "Elm supports French and Spanish document translation.", "Which languages can Elm translate documents into?"),
    ("Pine timezone", "Pine schedules reminders according to the Europe/London time zone.", "Which regional clock does Pine use for notifications?"),
    ("Juniper retry", "Juniper reuses the same retry identifier after an interrupted payment request.", "How does Juniper avoid charging twice after a connection failure?"),
    ("Hazel delivery", "Hazel delivers weekly progress reports on Mondays.", "On which weekday are Hazel status updates distributed?"),
    ("Rowan access", "Rowan gives temporary contractors read-only project access.", "Can external short-term Rowan workers edit project data?"),
    ("Alder recovery", "Alder restores encrypted backups into a fresh database before verification.", "Where does Alder perform a trial recovery of its saved data?"),
]


@pytest.mark.asyncio
async def test_english_paraphrase_set_and_scope_boundary():
    url = os.getenv("RNR_QUALIFICATION_DATABASE_URL")
    cache = os.getenv("RNR_QUALIFICATION_MODEL_CACHE")
    if not url or not cache or not Path(cache).is_dir():
        pytest.skip("Prepare an explicit disposable database and local embedding cache")
    pool = await asyncpg.create_pool(url, min_size=1, max_size=2)
    tenant = "q_" + uuid.uuid4().hex[:20]
    owner = MemoryScope(tenant, "quality", "synthetic_evaluator", "evaluation")
    isolated = MemoryScope(tenant, "private_other", "synthetic_evaluator", "evaluation")
    service = MemoryService(pool, EncryptionManager(master_key=Fernet.generate_key().decode()),
                            LocalEmbeddings("BAAI/bge-small-en-v1.5", cache))
    try:
        await service.initialize()
        identifiers = {}
        for label, content, _ in CASES:
            record = await service.remember(owner, content, idempotency_key=label, category="retrieval_evaluation",
                                            evidence={"kind": "fact", "source_id": label})
            identifiers[label] = record["id"]
        hidden = await service.remember(isolated, "Cedar's secret alternate planning interval is three days.",
                                        idempotency_key="private_distractor")
        hits, durations, ranks = 0, [], {}
        for label, _, query in CASES:
            started = time.monotonic()
            result = await service.recall(owner, query, limit=3)
            durations.append((time.monotonic() - started) * 1000)
            ids = [item["id"] for item in result["results"]]
            assert hidden["id"] not in ids
            assert result["retrieval"] == "semantic" and not result["candidate_limit_reached"]
            rank = ids.index(identifiers[label]) + 1 if identifiers[label] in ids else None
            ranks[label] = rank
            hits += rank is not None
            for item in result["results"]:
                assert item["version"] == 1 and item["evidence"]["declaration"]["source_id"] in identifiers
        ordered = sorted(durations)
        report = {"fixtures": len(CASES), "top_three_hits": hits, "ranks": ranks,
                  "median_query_ms": round(statistics.median(durations), 2),
                  "p95_query_ms": round(ordered[math.ceil(.95 * len(ordered)) - 1], 2),
                  "scope_leaks": 0, "language": "English", "graph_reasoning_tested": False}
        print("Retrieval evaluation: " + json.dumps(report, sort_keys=True))
        # Fixed acceptance before running: at least eleven of twelve paraphrases.
        assert hits >= 11, report
        assert (await service.recall(MemoryScope("q_" + uuid.uuid4().hex[:20], "quality", "reader", "evaluation"),
                                      "Cedar review interval"))["results"] == []
    finally:
        await pool.close()
