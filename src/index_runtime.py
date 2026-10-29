"""Operator entrypoint for the explicitly configured local default-stack worker."""
from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
import signal

from pydantic import BaseModel, ConfigDict, Field

from src.index_contracts import IndexIdentity
from src.index_sinks import DefaultIndexSinks


class IndexSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    pipeline: str = Field(pattern=r"^[a-z][a-z0-9_]{0,31}$")
    model: str = Field(min_length=1, max_length=200)
    dimensions: int = Field(ge=1, le=8192)
    qdrant_url: str
    arcade_url: str
    arcade_database: str = Field(pattern=r"^[a-z][a-z0-9_]{0,31}$")
    allow_internal_http: bool = False


def configured_sinks(*, readonly: bool = False):
    path = Path(os.environ["ENHANCED_INDEX_CONFIG"])
    if not path.is_absolute() or path.is_symlink() or path.stat().st_size > 16384:
        raise ValueError("Use an explicit bounded index settings file")
    settings = IndexSettings.model_validate_json(path.read_text())
    identity = IndexIdentity(os.environ["ENHANCED_INDEX_KEY"], settings.pipeline)
    return DefaultIndexSinks(identity, model=settings.model, dimensions=settings.dimensions,
        qdrant_url=settings.qdrant_url, arcade_url=settings.arcade_url,
        arcade_database=settings.arcade_database, allow_internal_http=settings.allow_internal_http,
        arcade_user=os.environ["INDEX_ARCADEDB_USER"], arcade_password=os.environ["INDEX_ARCADEDB_PASSWORD"],
        cache_url=None if readonly else os.environ["INDEX_VALKEY_URL"], readonly=readonly,
        qdrant_key=os.getenv("INDEX_QDRANT_API_KEY", ""))


async def _run(args):
    import asyncpg
    from src.index_outbox import IndexWorker
    from src.local_embeddings import LocalEmbeddings
    from src.memory_keys import canonical_cipher_from_environment
    from src.memory_service import MemoryService
    sinks = configured_sinks()
    try:
        if args.command == "provision":
            await sinks.provision(create_graph_database=args.create_graph_database)
            return {"index_schema_provisioned": True}
        embedder = LocalEmbeddings(sinks.model, os.environ["ENHANCED_MODEL_CACHE"])
        if len(await embedder.embed("Index configuration check")) != sinks.dimensions:
            raise ValueError("The prepared model has a different embedding dimension")
        pool = await asyncpg.create_pool(os.environ["ENHANCED_INDEX_DATABASE_URL"], min_size=1,
                                        max_size=3, command_timeout=15)
        try:
            service = MemoryService(pool, canonical_cipher_from_environment(), embedder)
            await service.check_schema()
            worker = IndexWorker(service, sinks)
            if args.command == "once":
                return {"work_attempted": await worker.run_once()}
            stop = asyncio.Event()
            loop = asyncio.get_running_loop()
            for signum in (signal.SIGINT, signal.SIGTERM):
                loop.add_signal_handler(signum, stop.set)
            await worker.run(stop)
            return {"worker_stopped": True}
        finally:
            await pool.close()
    finally:
        await sinks.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("provision", "once", "run"))
    parser.add_argument("--create-graph-database", action="store_true")
    args = parser.parse_args()
    if args.create_graph_database and args.command != "provision":
        parser.error("Graph creation is an explicit operator provisioning action")
    try:
        print(json.dumps(asyncio.run(_run(args)), ensure_ascii=True))
    except Exception:
        parser.exit(1, "Index action stopped. No credentials or source text were printed. Inspect sanitized delivery status.\n")


if __name__ == "__main__":
    main()
