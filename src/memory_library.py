"""Reviewed portfolio-library access; group membership never exposes raw projects."""
from __future__ import annotations

import json

from src.multi_tenant import validate_tenant_id
from src.security.enterprise_auth import AuthError
from src.security.memory_admission import contains_private_details


READ_PREDICATE = """r.tenant=$1 AND r.state='active'
 AND (r.expires_at IS NULL OR r.expires_at > now()) AND
 (r.project=$2 OR ($3 AND (
   EXISTS(SELECT 1 FROM shared_memory.record_shares s
     WHERE s.tenant=r.tenant AND s.project=r.project AND s.record_id=r.id
     AND s.target_project=$2 AND s.version=r.version)
   OR EXISTS(SELECT 1 FROM shared_memory.library_publications p
     JOIN shared_memory.library_members reader ON reader.tenant=p.tenant
       AND reader.library=p.library AND reader.project=$2
     JOIN shared_memory.library_members source ON source.tenant=p.tenant
       AND source.library=p.library AND source.project=r.project AND source.can_publish
     WHERE p.tenant=r.tenant AND p.project=r.project AND p.record_id=r.id
       AND p.version=r.version)
 )))"""

LIBRARY_SCHEMA = """
CREATE TABLE IF NOT EXISTS shared_memory.library_members (
 tenant TEXT NOT NULL, library TEXT NOT NULL, project TEXT NOT NULL,
 can_publish BOOLEAN NOT NULL DEFAULT false, approved_by TEXT NOT NULL,
 updated_at TIMESTAMPTZ NOT NULL DEFAULT now(), PRIMARY KEY(tenant,library,project)
);
CREATE TABLE IF NOT EXISTS shared_memory.library_publications (
 tenant TEXT NOT NULL, library TEXT NOT NULL, project TEXT NOT NULL,
 record_id TEXT NOT NULL, version INTEGER NOT NULL, reviewed_by TEXT NOT NULL,
 created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 PRIMARY KEY(tenant,library,project,record_id),
 FOREIGN KEY(tenant,project,record_id) REFERENCES shared_memory.records(tenant,project,id)
);
"""


class LibraryAccess:
    async def set_library_member(self, scope, *, library: str, member_project: str,
                                 admitted: bool, can_publish: bool = False) -> dict:
        if not scope.admin:
            raise AuthError(403, "Library membership requires a reviewer credential")
        validate_tenant_id(library)
        validate_tenant_id(member_project)
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                # Serialize membership revocation and publication for this group.
                await conn.execute("SELECT pg_advisory_xact_lock(hashtextextended($1,0))",
                                   scope.tenant + ":library:" + library)
                if admitted:
                    await conn.execute("""INSERT INTO shared_memory.library_members
                        (tenant,library,project,can_publish,approved_by) VALUES($1,$2,$3,$4,$5)
                        ON CONFLICT(tenant,library,project) DO UPDATE SET
                        can_publish=excluded.can_publish,approved_by=excluded.approved_by,updated_at=now()""",
                        scope.tenant, library, member_project, can_publish, scope.subject)
                else:
                    await conn.execute("DELETE FROM shared_memory.library_members WHERE tenant=$1 AND library=$2 AND project=$3",
                                       scope.tenant, library, member_project)
                if not admitted or not can_publish:
                    await conn.execute("DELETE FROM shared_memory.library_publications WHERE tenant=$1 AND library=$2 AND project=$3",
                                       scope.tenant, library, member_project)
                await self._audit(conn, scope, "library:" + library, 0,
                                  ("member_admitted:" if admitted else "member_revoked:") + member_project)
        return {"library": library, "member_project": member_project, "admitted": admitted,
                "can_publish": admitted and can_publish}

    async def publish_library(self, scope, record_id: str, *, library: str,
                              expected_version: int, revoke: bool = False) -> dict:
        if not scope.admin:
            raise AuthError(403, "Library publication requires a reviewer credential")
        validate_tenant_id(library)
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute("SELECT pg_advisory_xact_lock(hashtextextended($1,0))",
                                   scope.tenant + ":library:" + library)
                row = await conn.fetchrow("""SELECT * FROM shared_memory.records WHERE
                    tenant=$1 AND project=$2 AND id=$3 AND state='active'
                    AND (expires_at IS NULL OR expires_at > now()) FOR UPDATE""",
                    scope.tenant, scope.project, record_id)
                if row is None:
                    raise KeyError("Memory not found")
                if row["version"] != expected_version:
                    from src.memory_service import MemoryConflict
                    raise MemoryConflict("Library review must name the current version")
                if revoke:
                    await conn.execute("""DELETE FROM shared_memory.library_publications
                        WHERE tenant=$1 AND project=$2 AND record_id=$3 AND library=$4""",
                        scope.tenant, scope.project, record_id, library)
                else:
                    member = await conn.fetchval("""SELECT can_publish FROM shared_memory.library_members
                        WHERE tenant=$1 AND library=$2 AND project=$3""", scope.tenant, library, scope.project)
                    if member is not True:
                        raise AuthError(403, "Source project has no library publication grant")
                    payload = self._payload(row)
                    visible = {key: payload.get(key) for key in ("content", "category", "metadata", "evidence", "knowledge_links", "fact_key")}
                    if contains_private_details(json.dumps(visible, ensure_ascii=True)):
                        raise ValueError("Private details require a sanitized library summary")
                    await conn.execute("""INSERT INTO shared_memory.library_publications
                        (tenant,library,project,record_id,version,reviewed_by) VALUES($1,$2,$3,$4,$5,$6)
                        ON CONFLICT(tenant,library,project,record_id) DO UPDATE SET
                        version=excluded.version,reviewed_by=excluded.reviewed_by,created_at=now()""",
                        scope.tenant, library, scope.project, record_id, expected_version, scope.subject)
                await self._audit(conn, scope, record_id, expected_version,
                                  ("library_revoked:" if revoke else "library_published:") + library)
        return {"id": record_id, "library": library, "published": not revoke}

    @staticmethod
    def shared_view(result: dict) -> dict:
        """Project-internal session/actor metadata does not accompany publication."""
        result["shared"] = True
        result["metadata"] = {"source_project": result["project_id"]}
        result["provenance"] = {key: value for key, value in result.get("provenance", {}).items()
                                if key in {"observed_at", "content_sha256", "authority", "corrected_at",
                                           "supersedes_version", "previous_content_sha256"}}
        return result
