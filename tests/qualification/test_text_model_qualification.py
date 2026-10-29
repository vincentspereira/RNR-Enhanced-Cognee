"""Real pinned model inference, offline startup and fresh-session parity."""
import asyncio
import json
import os
from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest

from src.local_embeddings import LocalEmbeddings, MODEL


@pytest.mark.asyncio
async def test_real_model_restart_long_input_and_parallel_queries():
    cache = os.getenv("RNR_QUALIFICATION_MODEL_CACHE")
    if not cache:
        pytest.skip("Requires the explicit prepared offline text-model cache")
    # No remote model clients are used even when the environment permits them.
    first = LocalEmbeddings(MODEL, cache)
    texts = ["", "Cedar reviews plans every eleven days.", "one " * 700,
             "  Spaces\nnewlines and punctuation: REVIEW.  "]
    before = np.asarray(await asyncio.gather(*(first.embed(t) for t in texts)))
    second = LocalEmbeddings(MODEL, cache)
    after = np.asarray([await second.embed(t) for t in texts])
    assert before.shape == (4, 384) and np.isfinite(before).all()
    np.testing.assert_allclose(np.linalg.norm(before, axis=1), 1, atol=1e-6)
    np.testing.assert_allclose(before, after, atol=1e-6, rtol=1e-5)
    reference = json.loads((Path(__file__).resolve().parents[1] /
                            "fixtures/text_embedding_reference.json").read_text())
    assert reference["model"] == MODEL
    for case in reference["cases"]:
        actual = np.asarray(await second.embed(case["text"]))
        expected = np.asarray(case["vector"])
        # A quantized model can choose different integer kernels on another
        # CPU. Keep same-host restart strict above; compare the stored baseline
        # by bounded component error AND angular agreement across machines.
        assert np.max(np.abs(actual - expected)) <= 1e-3
        cosine = np.dot(actual, expected) / (np.linalg.norm(actual) * np.linalg.norm(expected))
        assert cosine >= 0.99999
    with pytest.raises(ValueError, match="admitted"):
        LocalEmbeddings("unreviewed/other-model", cache)
    with pytest.raises(ValueError, match="text"):
        await first.embed(None)


def test_restricted_model_subprocess_has_no_image_framework():
    cache = os.getenv("RNR_QUALIFICATION_MODEL_CACHE")
    if not cache:
        pytest.skip("Requires the explicit prepared offline text-model cache")
    # This absence check is mandatory in the actual reduced environment; the
    # full development environment may legitimately retain optional image tools.
    code = """import asyncio,sys
from src.local_embeddings import LocalEmbeddings,MODEL
engine=LocalEmbeddings(MODEL,sys.argv[1])
assert len(asyncio.run(engine.embed('Synthetic local text.')))==384
assert 'fastembed' not in sys.modules and 'PIL' not in sys.modules
"""
    root = Path(__file__).resolve().parents[2]
    subprocess.run([sys.executable, "-B", "-c", code, cache], cwd=root,
                   env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HF_HUB_OFFLINE": "1",
                        "PYTHONPATH": str(root / "tests/support/network_guard")},
                   check=True, timeout=60, capture_output=True)
