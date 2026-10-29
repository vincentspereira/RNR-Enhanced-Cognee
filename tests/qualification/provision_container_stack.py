"""Prepare fresh invented-data image fixtures, never a private deployment.

Requires an explicit disposable operator database and output directory. Existing
database/role/files are never replaced. No image or service is published.
"""
import argparse
import asyncio
import json
import os
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import asyncpg

from src.index_contracts import IndexIdentity
from src.index_sinks import DefaultIndexSinks
from src.memory_admin import grant_runtime, grant_worker
from src.memory_service import MemoryService


async def provision(directory):
    if os.getenv("RNR_ALLOW_SYNTHETIC_CONTAINERS") != "1":
        raise ValueError("Explicitly select invented-data container qualification")
    root = Path(directory)
    if not root.is_absolute() or root.parent != root.parent.resolve(strict=True):
        raise ValueError("Choose an absolute new fixture directory")
    root.mkdir(mode=0o700)
    operator_url = os.environ["RNR_QUALIFICATION_DATABASE_URL"]
    uri = urlsplit(operator_url)
    target = urlunsplit((uri.scheme, uri.netloc, "/canonical_image_qualification", uri.query, ""))
    conn = await asyncpg.connect(operator_url)
    try:
        await conn.execute("CREATE DATABASE canonical_image_qualification")
    finally:
        await conn.close()
    pool = await asyncpg.create_pool(target, min_size=1, max_size=2)
    try:
        await MemoryService.provision(pool)
        await grant_runtime(pool, role="ci_image_runtime", operator_url=target, output=str(root/"api-db.json"))
        await grant_worker(pool, role="ci_image_index", operator_url=target, output=str(root/"worker-db.json"))
    finally:
        await pool.close()
    settings_path = os.getenv("RNR_QUALIFICATION_INDEX_SETTINGS")
    settings = json.loads(Path(settings_path).read_text()) if settings_path else {
        "qdrant_url": "http://127.0.0.1:6333", "arcade_url": "http://127.0.0.1:2480",
        "arcade_user": "root", "arcade_password": "synthetic-default-graph-only",
        "cache_url": "redis://127.0.0.1:6379/0"}
    model, pipeline = "BAAI/bge-small-en-v1.5", "ci_image"
    index_key = "synthetic-image-index-key-at-least-32-bytes"
    sinks = DefaultIndexSinks(IndexIdentity(index_key, pipeline), qdrant_url=settings["qdrant_url"],
        arcade_url=settings["arcade_url"], arcade_database=pipeline, arcade_user=settings["arcade_user"],
        arcade_password=settings["arcade_password"], cache_url=settings["cache_url"], dimensions=384, model=model)
    try:
        await sinks.provision(create_graph_database=True)
    finally:
        await sinks.close()
    config = {"pipeline": pipeline, "model": model, "dimensions": 384,
        "qdrant_url": settings["qdrant_url"], "arcade_url": settings["arcade_url"], "arcade_database": pipeline}
    with (root/"index.json").open("x") as handle:
        json.dump(config, handle)
    # Public model/configuration only; service credentials remain private files.
    (root/"index.json").chmod(0o644)
    common = {"ENHANCED_ENV": "production", "ENHANCED_REQUIRE_TENANT": "1",
        "ENCRYPTION_MASTER_KEY": "cXFxcXFxcXFxcXFxcXFxcXFxcXFxcXFxcXFxcXFxcXE=",
        "ENHANCED_EMBEDDING_MODEL": model, "ENHANCED_MODEL_CACHE": "/models",
        "ENHANCED_INDEX_CONFIG": "/config/index.json", "ENHANCED_INDEX_KEY": index_key,
        "INDEX_ARCADEDB_USER": settings["arcade_user"], "INDEX_ARCADEDB_PASSWORD": settings["arcade_password"]}
    api = common | json.loads((root/"api-db.json").read_text()) | {
        "ENHANCED_JWT_SECRET": "synthetic-ci-container-key-at-least-32-bytes",
        "ENHANCED_RATE_LIMIT_PER_MINUTE": "600"}
    worker = common | json.loads((root/"worker-db.json").read_text()) | {"INDEX_VALKEY_URL": settings["cache_url"]}
    for name, values in (("api.env", api), ("worker.env", worker)):
        fd = os.open(root/name, os.O_WRONLY|os.O_CREAT|os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as handle:
            for key, value in values.items():
                if any(char in value for char in ("\n", "\r", "\0")):
                    raise ValueError("Invalid fixture environment field")
                handle.write(key+"="+value+"\n")
    print("Fresh synthetic image database, restricted roles and index namespaces prepared")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    try:
        asyncio.run(provision(args.output))
    except Exception:
        parser.exit(1, "Synthetic provisioning stopped; existing resources and secret values were preserved.\n")
