"""Canonical read operations shared by API, dashboard, MCP and SDK adapters."""
from __future__ import annotations

import json

from src.memory_library import READ_PREDICATE
from src.security.memory_admission import contains_private_memory_details


class MemoryQueries:
    async def list_records(self, scope, *, limit=50, offset=0, category=None, agent=None, include_shared=True):
        if not 1 <= limit <= 200 or not 0 <= offset <= 100000:
            raise ValueError("Use bounded pagination: limit 1-200 and offset 0-100000")
        sql = "SELECT r.* FROM shared_memory.records r WHERE " + READ_PREDICATE
        args = [scope.tenant, scope.project, include_shared]
        for column, value in (("writer_agent", agent),):
            if value is not None:
                args.append(value)
                sql += " AND r." + column + "=$" + str(len(args))
        args += [limit + 1, offset]
        sql += " ORDER BY r.updated_at DESC,r.id LIMIT $" + str(len(args) - 1) + " OFFSET $" + str(len(args))
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(sql, *args)
        results, used, consumed = [], 0, 0
        for row in rows[:limit]:
            consumed += 1
            try:
                record = self._decode(row)
            except ValueError:
                continue
            if category is not None and record.get("category") != category:
                continue
            if scope.selected_capture and contains_private_memory_details(record):
                continue
            if row["project"] != scope.project:
                record = self.shared_view(record)
            if len(record["content"]) > 4096:
                record["content"] = record["content"][:4096]
                record["content_truncated"] = True
            if len(json.dumps(record.get("metadata", {}), ensure_ascii=True)) > 4096:
                record["metadata"] = {"omitted_from_list": True}
            size = len(json.dumps(record, ensure_ascii=True).encode())
            if used + size > 1024 * 1024:
                consumed -= 1
                break
            used += size
            results.append(record)
        more = len(rows) > consumed
        return {"results": results, "next_offset": offset + consumed if more else None,
                "response_limit_reached": consumed < min(limit, len(rows))}

    async def agents(self, scope):
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""SELECT writer_agent AS agent_id,count(*) AS memory_count
                FROM shared_memory.records WHERE tenant=$1 AND project=$2 AND state='active'
                AND (expires_at IS NULL OR expires_at>now()) GROUP BY writer_agent ORDER BY writer_agent LIMIT 200""",
                scope.tenant, scope.project)
        return {"agents": [dict(row) for row in rows]}

    async def history(self, scope, record_id, *, limit=50, before_version=None):
        if not 1 <= limit <= 100 or (before_version is not None and before_version < 1):
            raise ValueError("Use bounded version-history pagination")
        async with self.pool.acquire() as conn:
            owner = await conn.fetchrow("""SELECT owner_subject,state FROM shared_memory.records
                WHERE tenant=$1 AND project=$2 AND id=$3""", scope.tenant, scope.project, record_id)
            if owner is None or (owner["owner_subject"] != scope.subject and not scope.admin):
                raise KeyError("History is available only to the owning subject or project reviewer")
            rows = await conn.fetch("""SELECT version,payload,created_at FROM shared_memory.record_versions
                WHERE tenant=$1 AND project=$2 AND record_id=$3 AND ($4::int IS NULL OR version<$4)
                ORDER BY version DESC LIMIT $5""", scope.tenant, scope.project, record_id, before_version, limit)
        result, used = [], 0
        from src.security.memory_admission import require_no_credentials
        for row in rows:
            value = self._payload(row)
            try:
                require_no_credentials(json.dumps(value, ensure_ascii=True))
                if scope.selected_capture and contains_private_memory_details(value):
                    raise ValueError("Private historical content requires review")
                value.pop("embedding", None)
            except ValueError:
                value = {"content_withheld": True, "reason": "private_or_credential_review_required"}
            item = dict(value, id=record_id, version=row["version"], recorded_at=row["created_at"].isoformat())
            size = len(json.dumps(item, ensure_ascii=True).encode())
            if used + size > 1024 * 1024:
                break
            result.append(item)
            used += size
        return {"versions": result, "record_state": owner["state"],
                "next_before_version": result[-1]["version"] if result and (len(rows) == limit or len(result) < len(rows)) else None,
                "response_limit_reached": len(result) < len(rows)}
