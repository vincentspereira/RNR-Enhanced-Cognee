# Commercialisation & License Compliance Guide

**Question:** If Enhanced Cognee is monetised, sold as SaaS, or incorporated
into another commercial system (e.g., the Multi-Agent System), are there
license-compliance risks from the open-source components we depend on?

**Short answer:** **No blocking issues for any commercial use case currently
foreseen.** Three components warrant attention; mitigations are documented
below. The full component-by-component license list is in
[`LICENSE_AUDIT.md`](LICENSE_AUDIT.md).

---

## Risk Matrix

| Component | License | Self-host commercial | Bundled-product distribution | SaaS commercial |
|---|---|---|---|---|
| Enhanced Cognee (own code) | Apache-2.0 | OK | OK | OK |
| Cognee (upstream) | Apache-2.0 | OK | OK | OK |
| Valkey | Apache-2.0 | OK | OK | OK |
| PostgreSQL + pgvector | PostgreSQL License | OK | OK | OK |
| Qdrant | Apache-2.0 | OK | OK | OK |
| Caddy | Apache-2.0 | OK | OK | OK |
| Python pip deps (20+) | Apache/MIT/BSD/PSF | OK | OK | OK |
| **Neo4j Community** | **GPLv3** | OK | **CAUTION** | OK |
| **Grafana / Loki** (optional monitoring) | **AGPLv3** | OK | **CAUTION** | **CAUTION** |
| **psycopg2** | LGPL | OK | OK | OK |

---

## Scenario 1: You keep selling a Cloud SaaS (you host, customers use)

**No issues for any component.** SaaS is the "service over a network" model
where:
- GPLv3 obligations apply if you DISTRIBUTE binaries — you don't.
- AGPLv3 applies even on network use, BUT: the requirement is that you make
  YOUR modifications to the AGPL software available, not your whole product.
  Since we don't modify Grafana or Loki, only configure them, this is a
  non-issue.

**Action:** None required. SaaS is the safest commercialisation path.

---

## Scenario 2: You self-host commercially (customers run on their own infra, you sell support / consulting)

**No issues.** Same logic as Scenario 1 — no redistribution of GPL/AGPL
binaries occurs.

**Action:** None required.

---

## Scenario 3: You distribute Enhanced Cognee as a packaged product (e.g., a "MAS Enterprise Edition" tarball that customers install on their machines)

**This is where Neo4j GPLv3 gets nuanced.** Three sub-scenarios:

### 3a. You ship Docker Compose only, customers pull their own Neo4j image

**Safe.** You are not redistributing Neo4j; the customer's Docker pulls it
from neo4j/neo4j-community on Docker Hub at install time. You're providing
configuration only, which is your own Apache-2.0 code. This is the same
model as "we recommend you install Postgres" — no copyleft attaches to your
config.

**Action:** Ship the Docker Compose file unchanged. Document that Neo4j is
GPLv3 and customers should review.

### 3b. You bundle Neo4j JARs in your installer

**Triggers GPLv3 obligations.** If your tarball contains `neo4j-community.jar`
or you build a Docker image FROM neo4j:5.x and ship that image, you are now
distributing GPL software. You must:
- Offer corresponding source code (or written offer for it).
- License your own code that DIRECTLY LINKS to Neo4j Java APIs under GPL.
  (The Bolt protocol wire connection does NOT constitute linking; only
   loading Neo4j's Java code into your JVM does.)

**Mitigation:** Don't bundle Neo4j JARs. Use the Docker Compose pull pattern
(3a) or switch to a non-copyleft alternative (3c).

### 3c. Switch from Neo4j to Apache AGE on PostgreSQL

**Best long-term answer.** Apache AGE is an extension to PostgreSQL that adds
Cypher query support. Same query language as Neo4j, runs inside our existing
PostgreSQL container, **Apache-2.0 license**. Removes one of the four
containers.

**Pros:**
- 100% Apache-2.0 stack throughout
- One fewer container to operate
- One fewer port to expose
- Cypher queries are largely portable

**Cons:**
- AGE is less battle-tested than Neo4j for very-large graphs (millions of nodes)
- Some Neo4j-specific Cypher extensions (APOC procedures) don't have AGE equivalents
- ~ 2-4 weeks of integration work to port `src/agent_memory_integration.py`

**Recommendation:** Build this when (a) you have a paying customer that
requires pure-Apache compliance, or (b) you're already touching the graph
layer for another reason. Don't do it speculatively.

---

## Scenario 4: You embed Enhanced Cognee inside the Multi-Agent System (MAS)

**Two questions to answer first:**

1. **What's MAS's license?** If MAS is also Apache-2.0 (or any permissive
   license), there's no friction. If MAS is proprietary or has a different
   license, check below.
2. **How are MAS and Enhanced Cognee combined?** Three integration models:

### 4a. MAS imports Enhanced Cognee as a Python library

If MAS does `from enhanced_cognee_client import ...`, this is normal library
usage. Apache-2.0 has no copyleft. MAS can be ANY license, including
proprietary closed-source.

**Action:** Bump `enhanced-cognee-client` on PyPI when needed; nothing
special required.

### 4b. MAS shells out to a separate Enhanced Cognee MCP server

If MAS launches `bin/enhanced_cognee_mcp_server.py` as a child process or
talks to it over network MCP, this is "mere aggregation" — even stronger
isolation than 4a. Zero copyleft concern.

**Action:** Bundle the deploy/local/install scripts; MAS uses them as
external tools.

### 4c. MAS copies Enhanced Cognee source code into its own tree

If MAS source includes Enhanced Cognee files directly (vendored copy),
those copied files retain Apache-2.0 attribution. MAS as a whole can still
be ANY license (Apache permits sublicensing).

**Action:** Preserve LICENSE + NOTICE + per-file copyright headers from
Enhanced Cognee in MAS's source tree.

**Bottom line:** Embedding Enhanced Cognee in MAS is unrestricted under any
of the three models, regardless of MAS's commercial intent.

---

## Scenario 5: MAS (with Enhanced Cognee inside) is sold as a closed-source commercial product

**Still safe, with caveats below.**

### What's safe

- Enhanced Cognee code is Apache-2.0 → can be inside a closed-source product.
- All Python pip deps (Apache/MIT/BSD/PSF) → can be inside.
- Valkey, Qdrant, Caddy (Apache-2.0) → safe.
- PostgreSQL + pgvector (PostgreSQL license) → safe.

### What requires care

- **Neo4j Community (GPLv3):** Apply the same rules as Scenario 3 above.
  Don't bundle the JAR; let the customer's Docker pull it.

- **Grafana / Loki (AGPLv3):** Only ship if (a) they are clearly OPTIONAL,
  (b) customers can disable them, (c) you don't redistribute their binaries
  in your installer. Our `monitoring/docker-compose-monitoring.yml` is
  exactly that — separate, opt-in.

- **psycopg2 (LGPL):** Permitted in commercial closed-source products IF
  customers can replace `psycopg2` with a different version (dynamic linking
  permitted). The standard pip install satisfies this; static-linking the
  source code does not.

### Recommended distribution pattern

If you're selling MAS-as-binary:

1. Ship MAS's own Apache-2.0 / MIT / proprietary code in your installer.
2. Ship the Docker Compose file pointing at upstream images (PostgreSQL,
   Qdrant, Valkey, Neo4j Community).
3. Documentation tells the customer to run `docker compose pull` which
   fetches the third-party images directly from Docker Hub. You are not
   redistributing those images.
4. Include `NOTICE` and `LICENSES/` directory with the full license text
   of every component (for legal completeness).
5. Make monitoring opt-in (separate `monitoring/` compose file).

This pattern is used by hundreds of commercial products with no friction.

---

## Quick FAQ

> **"Can I sell support contracts for Enhanced Cognee?"**

Yes. Apache-2.0 explicitly permits commercial use without restriction.
This is the Red Hat / Suse / Canonical business model.

> **"Can I rename Enhanced Cognee to 'MyCompany Memory Platform' and sell it?"**

Yes, with conditions:
- Preserve the Apache-2.0 LICENSE and NOTICE files.
- Add your own copyright notice for new code you've added.
- Don't claim the original code is your work; the existing copyright
  notices stay.

> **"Can I keep my modifications to Enhanced Cognee private?"**

Yes. Apache-2.0 has no copyleft. You can fork, modify, and keep your
modifications closed-source.

> **"Can I bundle Enhanced Cognee with my proprietary closed-source agent framework?"**

Yes (see Scenario 5). Just don't bundle Neo4j JARs or Grafana binaries.

> **"What if I want to remove all GPL/AGPL components entirely?"**

See `docs/operations/MULTI_TENANT_DESIGN.md` and the Neo4j-alternatives
table in `LICENSE_AUDIT.md`. Apache AGE on PostgreSQL is the clean swap
for Neo4j. VictoriaMetrics + VictoriaLogs replace Grafana + Loki.

> **"Do I need to publish my source code?"**

No, never (unless you choose to share your modifications back to upstream
out of goodwill). Apache-2.0 has no source-disclosure requirement.

---

## Action Checklist Before Commercialising

- [ ] Decide which commercialisation scenario applies (1-5 above)
- [ ] Verify NOTICE file is preserved and accurate
- [ ] Confirm Neo4j is NOT bundled in your installer artefacts
- [ ] Confirm Grafana / Loki are OPTIONAL and in a separate compose file
- [ ] Add your own copyright notice to any new files you add
- [ ] Run `pip-licenses --format=markdown` to generate a current
      SBOM (Software Bill of Materials) and ship it with your product
- [ ] If unsure, get a 30-minute consult with a software lawyer
      (~ EUR 200-400; one-time cost)

For most practical purposes, **Enhanced Cognee + Multi-Agent System +
commercialisation = no license obstacles**. The Apache-2.0 license under
which Enhanced Cognee ships is the most permissive widely-used open-source
license; combined with the Apache/MIT/BSD ecosystem of Python deps, the
GPL Neo4j concern is the only one worth conscious attention, and it's
mitigated by the "customer pulls their own image" deployment pattern that
we already use.
