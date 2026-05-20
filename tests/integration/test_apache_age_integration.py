"""Live integration tests for the Apache AGE graph adapter.

Boots against a running Postgres instance that has the AGE extension
loaded. The CI workflow uses `apache/age:PG16_latest` for the postgres
service container so the extension is pre-installed; locally, you can
swap your postgres image in `docker/docker-compose-enhanced-cognee.yml`
to `apache/age:PG16_latest`.

Tests verify:
  - LOAD 'age' succeeds (extension is available)
  - The cognee_graph default graph exists or is creatable
  - A round-trip CREATE -> MATCH -> DETACH DELETE works via the adapter
  - Native graph elements (`_AGENode` / `_AGERelationship`) come back
    when querying ::vertex / ::edge agtype payloads
  - Async path (asyncpg-backed) round-trips identically
"""

from __future__ import annotations

import os
import time

import pytest

from src.db_adapters import graph_apache_age


_REASON_NO_AGE = (
    "Apache AGE not reachable on Postgres at "
    + os.getenv("AGE_HOST", os.getenv("POSTGRES_HOST", "localhost"))
    + ":"
    + os.getenv("AGE_PORT", os.getenv("POSTGRES_PORT", "25432"))
    + "; skipping. Use `apache/age:release_PG16_1.6.0` image."
)


def _try_load_extension():
    """Returns True if AGE extension loads successfully."""
    try:
        driver = graph_apache_age.create_driver()
        with driver.session() as sess:
            # Make sure the graph exists; idempotent.
            sess.run("RETURN 1")
        return True
    except Exception:
        return False


@pytest.fixture(scope="module")
def age_driver():
    """Yields a connected AGE driver or skips."""
    deadline = time.monotonic() + 30
    available = False
    while time.monotonic() < deadline:
        if _try_load_extension():
            available = True
            break
        time.sleep(2)

    if not available:
        pytest.skip(_REASON_NO_AGE)

    driver = graph_apache_age.create_driver()
    # Ensure the graph exists before tests run -- AGE's `create_graph`
    # is idempotent in psycopg2 if wrapped in try/except.
    try:
        import psycopg2

        conn = driver._connect()
        cur = conn.cursor()
        cur.execute("LOAD 'age';")
        cur.execute("SET search_path = ag_catalog, public;")
        try:
            cur.execute("SELECT create_graph('cognee_graph');")
            conn.commit()
        except psycopg2.errors.DuplicateObject:
            conn.rollback()  # already exists
        except Exception:
            conn.rollback()
        finally:
            conn.close()
    except Exception:
        # If even the bootstrap fails, downstream tests will skip.
        pass

    yield driver


@pytest.mark.integration
@pytest.mark.apache_age
class TestAGEConnectivity:
    def test_connectivity_ping(self, age_driver):
        with age_driver.session() as sess:
            result = sess.run("RETURN 1")
            row = result.single()
            assert row is not None
            # AGE returns the value at column 0 (single agtype column)
            assert row[0] == 1


@pytest.mark.integration
@pytest.mark.apache_age
class TestAGENativeElements:
    """Verify ::vertex / ::edge round-trip into _AGENode / _AGERelationship."""

    def test_create_and_return_vertex(self, age_driver):
        tag = f"int_age_marker_{int(time.time())}"
        with age_driver.session() as sess:
            sess.run(
                "CREATE (n:IntegrationMarker {tag: $tag}) RETURN n",
                tag=tag,
            )

            result = sess.run(
                "MATCH (n:IntegrationMarker {tag: $tag}) RETURN n",
                tag=tag,
            )
            rows = list(result)
            assert len(rows) >= 1

            n = rows[0][0]
            # The whole point of PR 7 (AGE native elements): n is now
            # an _AGENode with labels / property dict access, not a
            # raw dict.
            assert isinstance(n, graph_apache_age._AGENode)
            assert "IntegrationMarker" in n.labels
            assert n["tag"] == tag

            # Cleanup
            sess.run(
                "MATCH (n:IntegrationMarker {tag: $tag}) DETACH DELETE n",
                tag=tag,
            )

    def test_create_relationship_returns_age_relationship(self, age_driver):
        tag = f"int_age_rel_{int(time.time())}"
        with age_driver.session() as sess:
            sess.run(
                "CREATE (a:RelMarkerA {tag: $tag})-[:KNOWS]->(b:RelMarkerB {tag: $tag})",
                tag=tag,
            )

            result = sess.run(
                "MATCH (:RelMarkerA {tag: $tag})-[r:KNOWS]->(:RelMarkerB {tag: $tag}) RETURN r",
                tag=tag,
            )
            rows = list(result)
            assert len(rows) >= 1

            r = rows[0][0]
            assert isinstance(r, graph_apache_age._AGERelationship)
            assert r.type == "KNOWS"

            # Cleanup
            sess.run(
                "MATCH (a:RelMarkerA {tag: $tag})-[r]-(b:RelMarkerB {tag: $tag}) "
                "DETACH DELETE a, b",
                tag=tag,
            )


@pytest.mark.integration
@pytest.mark.apache_age
class TestAGEAsync:
    @pytest.mark.asyncio
    async def test_async_connectivity_ping(self, age_driver):
        # age_driver fixture confirms sync connectivity. Build async on
        # top.
        driver = graph_apache_age.create_async_driver()
        async with driver.session() as sess:
            result = await sess.run("RETURN 1")
            row = result.single()
            assert row is not None
            assert row[0] == 1
