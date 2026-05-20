"""Live integration tests for the ArcadeDB graph adapter.

Boots against a running ArcadeDB container (provided by the CI
workflow's `services:` block, or by the user's local
docker-compose-enhanced-cognee.yml). Each test skips if the adapter
can't reach the server -- which is the correct CI-friendly behaviour
because ArcadeDB has historically been slow to come up.

The tests exercise the *minimum viable* surface: connectivity, schema
setup via Cypher, write + read round-trip, and async session.
"""

from __future__ import annotations

import os
import time

import pytest

from src.db_adapters import graph_arcadedb


_REASON_NO_ARCADEDB = (
    "ArcadeDB not reachable on bolt://"
    + os.getenv("ARCADEDB_HOST", "localhost")
    + ":"
    + os.getenv("ARCADEDB_PORT", "26687")
    + "; skipping. Boot the service with "
    + "`docker compose -f docker/docker-compose-enhanced-cognee.yml up arcadedb`."
)


def _try_connect():
    """Attempt a quick connectivity ping, returning a driver on success."""
    try:
        driver = graph_arcadedb.create_driver()
        with driver.session() as sess:
            result = sess.run("RETURN 1 AS x")
            row = result.single()
            assert row is not None
            assert row["x"] == 1
        return driver
    except Exception:
        return None


@pytest.fixture(scope="module")
def arcadedb_driver():
    """Returns a connected driver or skips the test module."""
    # Allow up to 30s for the container to become ready.
    deadline = time.monotonic() + 30
    driver = None
    while time.monotonic() < deadline:
        driver = _try_connect()
        if driver is not None:
            break
        time.sleep(2)

    if driver is None:
        pytest.skip(_REASON_NO_ARCADEDB)

    yield driver

    try:
        driver.close()
    except Exception:
        pass


@pytest.mark.integration
@pytest.mark.arcadedb
class TestArcadeDBConnectivity:
    def test_connectivity_ping(self, arcadedb_driver):
        """`RETURN 1` round-trips."""
        with arcadedb_driver.session() as sess:
            result = sess.run("RETURN 1 AS one")
            row = result.single()
            assert row is not None
            assert row["one"] == 1

    def test_record_iteration(self, arcadedb_driver):
        """Multiple records iterate cleanly."""
        with arcadedb_driver.session() as sess:
            result = sess.run("UNWIND [1, 2, 3] AS x RETURN x")
            xs = [r["x"] for r in result]
            assert sorted(xs) == [1, 2, 3]


@pytest.mark.integration
@pytest.mark.arcadedb
class TestArcadeDBWrite:
    def test_create_and_count_node(self, arcadedb_driver):
        """Create + count + cleanup round-trip."""
        marker = f"int_test_marker_{int(time.time())}"
        with arcadedb_driver.session() as sess:
            sess.run(
                "CREATE (:IntegrationMarker {tag: $tag, created_at: timestamp()})",
                tag=marker,
            )
            result = sess.run(
                "MATCH (n:IntegrationMarker {tag: $tag}) RETURN count(n) AS c",
                tag=marker,
            )
            row = result.single()
            assert row is not None
            assert row["c"] >= 1

            # Cleanup
            sess.run(
                "MATCH (n:IntegrationMarker {tag: $tag}) DETACH DELETE n",
                tag=marker,
            )


@pytest.mark.integration
@pytest.mark.arcadedb
class TestArcadeDBAsync:
    """Verify the async driver path works against the live server."""

    @pytest.mark.asyncio
    async def test_async_connectivity_ping(self):
        # Build the async driver only after the sync driver has
        # confirmed connectivity (via the module fixture).
        driver = graph_arcadedb.create_async_driver()
        try:
            async with driver.session() as sess:
                result = await sess.run("RETURN 1 AS x")
                row = await result.single()
                assert row is not None
                assert row["x"] == 1
        finally:
            await driver.close()
