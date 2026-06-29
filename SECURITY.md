# Security Policy

Thank you for helping keep RNR Enhanced Cognee secure.

## Supported Versions

Security fixes are backported to the most recent minor release on PyPI.

| Version | Supported |
| ------- | --------- |
| 1.0.x   | YES       |
| < 1.0   | NO        |

## Reporting a Vulnerability

**Please do NOT open a public GitHub issue for security bugs.**

Email **vincyspereira@gmail.com** with:

1. A clear description of the vulnerability
2. Steps to reproduce (if possible)
3. Affected versions
4. Any suggested mitigation

We aim to:

- **Acknowledge** within 48 hours
- **Triage** within 5 business days
- **Patch + release** critical issues within 14 days

You will be credited in the release notes unless you request otherwise.

## In-Scope

- The RNR Enhanced Cognee MCP server (`bin/enhanced_cognee_mcp_server.py`)
- The FastAPI HTTP variant (`src/enhanced_cognee_mcp.py`)
- The Python SDK client (`enhanced-cognee-client` on PyPI)
- All source modules under `src/`
- The shipped Docker compose stack (default configuration)
- Documentation that could mislead operators (e.g. insecure example configs)

## Out-of-Scope

- Issues in upstream `topoteretes/cognee` (report there)
- Vulnerabilities in `pip` dependencies (Dependabot already monitors these)
- Issues that require physical access to the host
- Social engineering or phishing
- DoS via volumetric traffic (use a CDN / WAF)

## Hardening Checklist (Self-Hosted Operators)

If you're running RNR Enhanced Cognee in production, follow this checklist:

- [ ] Change ALL default passwords in `docker/docker-compose-enhanced-cognee.yml`
- [ ] Set `POSTGRES_PASSWORD`, `NEO4J_PASSWORD`, `REDIS_PASSWORD` via env vars or
      a secrets manager (NOT in the compose file)
- [ ] Restrict the Docker bridge network to internal IPs only
- [ ] Run the MCP server as a non-root user (the bundled systemd unit does this)
- [ ] Enable Caddy automatic HTTPS for the FastAPI HTTP endpoint
- [ ] Keep Python deps current (Dependabot helps)
- [ ] Run nightly backups to encrypted storage
- [ ] Enable PII detection (`src.pii_detector` with `presidio_analyzer` installed)
- [ ] Audit MCP tool calls via `query_audit_log()` regularly
- [ ] Subscribe to this repo's security advisories (Watch -> Custom -> Security)

## Known Security Considerations

- **Tool authorization model**: any tool call carries an `agent_id`. The server
  trusts the caller for now -- there is no per-tool RBAC. Plan: add Phase F+
  tool-level permissions for multi-user deployments.
- **Audit log retention**: indefinite by default. Configure pruning in
  `automation_config.json` if storage is a concern.
- **GDPR right-to-erasure**: `gdpr_delete_user_data()` removes Postgres rows
  and Qdrant vectors; Neo4j relationships are pruned via cascade. Verify with
  `gdpr_verify_tenant_isolation()` after a deletion.

## Disclosure Timeline (example)

| Day | Event |
| --- | ----- |
| D-0  | Vulnerability reported privately to vincyspereira@gmail.com |
| D-2  | Acknowledged by maintainer |
| D-5  | Triaged; severity assigned (CVSS) |
| D-14 | Patch released to PyPI; advisory drafted |
| D-21 | Public disclosure (CVE assigned if applicable) |
| D-30 | Credit to reporter in release notes |

For critical issues, this timeline is compressed to ~7 days.
