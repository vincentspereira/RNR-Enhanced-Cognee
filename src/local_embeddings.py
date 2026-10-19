"""Optional CPU embeddings from an explicitly prepared local model cache."""
from __future__ import annotations

import asyncio
from pathlib import Path


class LocalEmbeddings:
    def __init__(self, model: str, cache: str):
        from fastembed import TextEmbedding
        if not Path(cache).is_dir():
            raise ValueError("Prepare the local embedding model cache before starting")
        self.model = model
        self._slots = asyncio.Semaphore(2)
        # Never download a model or contact a provider during service startup.
        self.engine = TextEmbedding(model_name=model, cache_dir=cache, local_files_only=True,
                                    threads=2)

    async def embed(self, content: str) -> list[float]:
        def run():
            vector = next(iter(self.engine.embed([content])))
            return vector.tolist()
        async with self._slots:
            return await asyncio.to_thread(run)
