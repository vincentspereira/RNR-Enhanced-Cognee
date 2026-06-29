# Commercialisation & License Compliance Guide

**Question:** If RNR Enhanced Cognee is monetised, sold as SaaS, or incorporated
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
| RNR Enhanced Cognee (own code) | Apache-2.0 | OK | OK | OK |
| Cognee (upstream) | Apache-2.0 | OK | OK | OK |
| Valkey | Apache-2.0 | OK | OK | OK |
| PostgreSQL + pgvector | PostgreSQL License | OK | OK | OK |
| Qdrant | Apache-2.0 | OK | OK | OK |
| Caddy | Apache-2.0 | OK | OK | OK |
| Python pip deps (20+) | Apache/MIT/BSD/PSF | OK | OK | OK |
| **ArcadeDB** (default since 2026-05-19) | Apache-2.0 | OK | OK | OK |
| Neo4j Community (legacy alternative; `ENHANCED_GRAPH_PROVIDER=neo4j`) | GPLv3 | OK | **CAUTION** | OK |
| **SigNoz + Apache Superset** (optional monitoring; default since 2026-05-19) | MIT + Apache-2.0 | OK | OK | OK |
| ~~Grafana / Loki / Tempo~~ (removed Phase 4) | AGPLv3 | n/a | n/a | n/a |
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

## Scenario 3: You distribute RNR Enhanced Cognee as a packaged product (e.g., a "MAS Enterprise Edition" tarball that customers install on their machines)

**Status (since 2026-05-19, Phase 2):** ArcadeDB (Apache-2.0) replaced Neo4j
as the default graph DB. The default packaged product is now copyleft-free for
the database tier. The Neo4j-GPLv3 caveat only applies if a customer
explicitly opts in via `ENHANCED_GRAPH_PROVIDER=neo4j`.

### 3a. Ship the default stack (ArcadeDB-based)

**Safe by default.** ArcadeDB is Apache-2.0, can be bundled or pulled at
install time, and is the default in
`docker/docker-compose-enhanced-cognee.yml`. No copyleft attaches to any of
the four containers (PostgreSQL + Qdrant + ArcadeDB + Valkey).

**Action:** Ship the default Compose file. Document that switching graph
providers (e.g. to Neo4j) carries the customer's own licence considerations.

### 3b. A customer chooses to switch to Neo4j

**Triggers the legacy Neo4j-GPLv3 considerations** (see Section 3c below).
This is now a customer-driven choice rather than a default, so the GPL
exposure only applies when explicitly opted into.

**Action:** Point them at [`docs/ARCADEDB_MIGRATION.md` §3.3](./ARCADEDB_MIGRATION.md#33-keep-using-neo4j-instead)
for the opt-in compose snippet, and ensure they understand they're now in
the Scenario 3c territory below.

### 3c. (Historical / opt-in) Neo4j GPLv3 considerations

This subsection applied universally before Phase 2 shipped (when Neo4j was
the default). It still applies to customers who opt in to
`ENHANCED_GRAPH_PROVIDER=neo4j`.

**Safe configurations:**
- **Ship Docker Compose only, customers pull their own Neo4j image.** You're
  not redistributing Neo4j; the customer's Docker pulls it from
  neo4j/neo4j-community on Docker Hub at install time. You're providing
  configuration only.
- **Connect via the Bolt network protocol** -- no copyleft obligation.

**Triggers GPLv3 obligations:**
- Bundling `neo4j-community.jar` in your installer or building a Docker image
  FROM neo4j:5.x and shipping that image. You'd then have to offer
  corresponding source and license code that loads Neo4j Java APIs under GPL.

**Mitigation:** Stay on the default ArcadeDB stack, or use the Docker Compose
pull pattern if you need Neo4j.

### 3d. Apache AGE as a pluggable alternative (Phase 3)

Apache AGE remains a pluggable graph backend for users who want a
Postgres-only deployment (no separate Java container at all). It is shipping
as `ENHANCED_GRAPH_PROVIDER=apache_age` in Phase 3 -- not yet wired but
documented in [`STRATEGY.md` §4.2](./STRATEGY.md#42-recommended-new-default-arcadedb-revised-2026-05-19)
and [HANDOVER §4 Phase 3](./HANDOVER.md).

---

## Scenario 4: You embed RNR Enhanced Cognee inside the Multi-Agent System (MAS)

**Two questions to answer first:**

1. **What's MAS's license?** If MAS is also Apache-2.0 (or any permissive
   license), there's no friction. If MAS is proprietary or has a different
   license, check below.
2. **How are MAS and RNR Enhanced Cognee combined?** Three integration models:

### 4a. MAS imports RNR Enhanced Cognee as a Python library

If MAS does `from enhanced_cognee_client import ...`, this is normal library
usage. Apache-2.0 has no copyleft. MAS can be ANY license, including
proprietary closed-source.

**Action:** Bump `enhanced-cognee-client` on PyPI when needed; nothing
special required.

### 4b. MAS shells out to a separate RNR Enhanced Cognee MCP server

If MAS launches `bin/enhanced_cognee_mcp_server.py` as a child process or
talks to it over network MCP, this is "mere aggregation" — even stronger
isolation than 4a. Zero copyleft concern.

**Action:** Bundle the deploy/local/install scripts; MAS uses them as
external tools.

### 4c. MAS copies RNR Enhanced Cognee source code into its own tree

If MAS source includes RNR Enhanced Cognee files directly (vendored copy),
those copied files retain Apache-2.0 attribution. MAS as a whole can still
be ANY license (Apache permits sublicensing).

**Action:** Preserve LICENSE + NOTICE + per-file copyright headers from
RNR Enhanced Cognee in MAS's source tree.

**Bottom line:** Embedding RNR Enhanced Cognee in MAS is unrestricted under any
of the three models, regardless of MAS's commercial intent.

---

## Scenario 5: MAS (with RNR Enhanced Cognee inside) is sold as a closed-source commercial product

**Still safe, with caveats below.**

### What's safe

- RNR Enhanced Cognee code is Apache-2.0 → can be inside a closed-source product.
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

> **"Can I sell support contracts for RNR Enhanced Cognee?"**

Yes. Apache-2.0 explicitly permits commercial use without restriction.
This is the Red Hat / Suse / Canonical business model.

> **"Can I rename RNR Enhanced Cognee to 'MyCompany Memory Platform' and sell it?"**

Yes, with conditions:
- Preserve the Apache-2.0 LICENSE and NOTICE files.
- Add your own copyright notice for new code you've added.
- Don't claim the original code is your work; the existing copyright
  notices stay.

> **"Can I keep my modifications to RNR Enhanced Cognee private?"**

Yes. Apache-2.0 has no copyleft. You can fork, modify, and keep your
modifications closed-source.

> **"Can I bundle RNR Enhanced Cognee with my proprietary closed-source agent framework?"**

Yes (see Scenario 5). After Phase 4 (2026-05-19) the entire default
stack is permissive, so there's no GPL/AGPL component to *not* bundle.
The only opt-in caveat is `ENHANCED_GRAPH_PROVIDER=neo4j` -- if a
customer chooses it, the Scenario 3c Neo4j-GPLv3 considerations apply
to *their* deployment.

> **"What if I want to remove all GPL/AGPL components entirely?"**

**The default already is.** Since Phase 2 (ArcadeDB replaced Neo4j) and
Phase 4 (SigNoz + Apache Superset replaced Grafana + Loki + Tempo), the
default `docker compose up` produces a 100% MIT + Apache-2.0
deployment. Both the main 4-database stack and the optional
observability stack are permissive end-to-end.

The only way GPL/AGPL re-enters the picture is opt-in:

- Setting `ENHANCED_GRAPH_PROVIDER=neo4j` re-adds Neo4j Community
  (GPLv3) -- see Scenario 3c above.
- Pulling the *removed-in-Phase-4* Grafana / Loki / Tempo stack out of
  git history and running it instead of `monitoring/docker-compose-monitoring.yml`.

Historical note (pre-Phase-4): the recommendation here used to be
"Apache AGE on PostgreSQL replaces Neo4j; VictoriaMetrics +
VictoriaLogs replace Grafana + Loki." That recommendation is
superseded by the actual Phase 2 + Phase 4 ship. AGE remains available
as a pluggable graph backend via `ENHANCED_GRAPH_PROVIDER=apache_age`
(Phase 3); SigNoz now plays the role VictoriaMetrics was going to.

> **"Do I need to publish my source code?"**

No, never (unless you choose to share your modifications back to upstream
out of goodwill). Apache-2.0 has no source-disclosure requirement.

---

## Action Checklist Before Commercialising

- [ ] Decide which commercialisation scenario applies (1-5 above)
- [ ] Verify NOTICE file is preserved and accurate
- [ ] Confirm `ENHANCED_GRAPH_PROVIDER` is `arcadedb` (default) or
      `apache_age` (lean profile) in shipped artefacts; opt-in to
      `neo4j` only when a specific customer requires it
- [ ] Confirm the monitoring stack you ship is the
      `docker-compose-monitoring.yml` (SigNoz + Superset, MIT +
      Apache-2.0), NOT the pre-Phase-4 Grafana/Loki/Tempo combination
- [ ] Add your own copyright notice to any new files you add
- [ ] Run `pip-licenses --format=markdown` to generate a current
      SBOM (Software Bill of Materials) and ship it with your product
- [ ] If unsure, get a 30-minute consult with a software lawyer
      (~ EUR 200-400; one-time cost)

For most practical purposes, **RNR Enhanced Cognee + Multi-Agent System +
commercialisation = no license obstacles**. The Apache-2.0 license under
which RNR Enhanced Cognee ships is the most permissive widely-used open-source
license; combined with the Apache/MIT/BSD ecosystem of Python deps, the
GPL Neo4j concern is the only one worth conscious attention, and it's
mitigated by the "customer pulls their own image" deployment pattern that
we already use.

## See also

When you're evaluating a specific RNR Enhanced Cognee feature for inclusion in
MAS (rather than evaluating the project as a whole), use:

- [`FEATURE_LICENSE_MATRIX.md`](FEATURE_LICENSE_MATRIX.md) -- per-feature
  view that maps every feature -> its OSS dependencies -> their licenses ->
  a SAFE / SAFE+ATTR / REVIEW / OPT-IN / CONFLICT verdict for MAS. Use
  this matrix as the first stop when porting code; cross-references
  [`LICENSE_AUDIT.md`](LICENSE_AUDIT.md) for the per-dependency rationale.
