# Secrets Management

> **Audience:** anyone deploying RNR Enhanced Cognee beyond a single developer
> laptop (team deploys, production VPS, SaaS, CI/CD pipelines).
>
> **Scope:** how to keep database credentials, API keys, encryption keys,
> and TLS certificate material out of source control and out of plain-text
> shell history. Covers the four levels of secrecy this project recognises.

## What counts as a secret

| Category | Example env vars | Where it lives in this project |
| --- | --- | --- |
| **Database credentials** | `POSTGRES_PASSWORD`, `ARCADEDB_PASSWORD`, `NEO4J_PASSWORD` | Docker compose `environment:` blocks |
| **External-service API keys** | `LLM_API_KEY`, `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `QDRANT_API_KEY` | `~/.claude.json`, `.env` |
| **MCP-server hardening tokens** | `ENHANCED_API_KEY` | `~/.claude.json`, `.env` |
| **Encryption keys** | The Fernet key minted by `src/encryption_manager.py` (stored in a secrets backend, not env) | Operator-managed |
| **TLS certificate material** | `ENHANCED_HTTPS_CERT_FILE`, `ENHANCED_HTTPS_KEY_FILE` paths | File-system paths (the files themselves are sensitive) |

`POSTGRES_USER`, port numbers, `ENHANCED_GRAPH_PROVIDER`, etc. are NOT secrets -- they're configuration. Mixing them with secrets is fine; the rules below apply only to the secret subset.

## Four levels of secrecy (pick the one that matches your deployment)

### Level 1 -- Developer laptop / local Claude Code MCP

**Default for personal use.** Secrets live in `~/.claude.json` (MCP env vars) and an optional `.env` file in the project root. Both are `.gitignore`d. No special tooling required.

Pros: zero setup overhead.
Cons: secrets stored in plain text on disk; if the laptop is compromised, everything in `~/.claude.json` leaks.

Use this when:

- You're the only user.
- The laptop is encrypted at rest (FileVault on macOS, BitLocker on Windows, LUKS on Linux).
- No tokens grant access to paid third-party services beyond your personal usage.

### Level 2 -- Single-VPS deployment

**Recommended for personal SaaS, single-tenant production.** Use a `.env` file owned by `root:root` with mode `0600`, loaded by `docker compose --env-file .env`. The compose file references `${VAR}` substitutions.

Example layout on the VPS:

```bash
sudo install -d -o root -g root -m 0700 /etc/enhanced-cognee
sudo install -o root -g root -m 0600 .env /etc/enhanced-cognee/.env
sudo ln -s /etc/enhanced-cognee/.env /opt/enhanced-cognee/.env
```

In `docker-compose-enhanced-cognee.yml`:

```yaml
services:
  cognee-mcp-postgres:
    environment:
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
```

In `/etc/enhanced-cognee/.env`:

```
POSTGRES_PASSWORD=use-a-32-char-random-string-here
ARCADEDB_PASSWORD=use-another-one
ENHANCED_API_KEY=use-a-third-one
LLM_API_KEY=sk-real-anthropic-key
```

Pros: secrets co-located with the deploy; works with vanilla compose; backups can include `/etc/enhanced-cognee/.env` only if the backup is encrypted.

Cons: still on disk; needs file-permission discipline; can't be safely committed to a Git repo even if encrypted (unless you use Level 3+).

### Level 3 -- Multi-developer team / production SaaS

**Recommended for teams + CI/CD.** Encrypt secrets at rest with one of:

#### Option A: sops + age (recommended)

[sops](https://github.com/getsops/sops) edits encrypted files in-place; [age](https://github.com/FiloSottile/age) provides the encryption backend. Both Apache-2.0 / BSD-style.

```bash
# One-time setup: generate an age key per developer + per-environment
age-keygen -o ~/.config/sops/age/keys.txt

# Encrypt the .env file with all team members' public keys + the CI key
sops --encrypt --age "age1abc...team1,age1def...team2,age1ghi...ci" \
    .env > .env.enc

# Commit .env.enc to the repo; .env stays gitignored.
git add .env.enc

# Decrypt on the deploy host
sops --decrypt .env.enc > /etc/enhanced-cognee/.env
```

`.sops.yaml` at the repo root configures which keys decrypt which paths so the rules are explicit and reviewable in PRs.

Pros: secrets are reviewable in PRs (the encrypted blob is opaque but the structure is visible); per-developer access without re-encrypting; works with GitHub Actions via the `sops-action`; rotate by re-encrypting against the new key set.

Cons: requires every developer to install `sops` + `age` and import the team's public keys; key rotation is a deliberate workflow rather than automatic.

#### Option B: Docker secrets (compose v3.1+)

Works inside the Docker daemon's Raft store on Swarm; available as a file mounted at `/run/secrets/<name>` inside containers.

```yaml
services:
  cognee-mcp-postgres:
    secrets:
      - postgres_password
    environment:
      POSTGRES_PASSWORD_FILE: /run/secrets/postgres_password

secrets:
  postgres_password:
    external: true
```

Then `docker secret create postgres_password ./postgres_password.txt`.

Pros: secrets never appear in `docker inspect` output or environment listings; native to Docker.

Cons: Swarm-only; compose-standalone doesn't support `external: true` for secrets without Swarm; managing rotation requires `docker service update`.

#### Option C: HashiCorp Vault (or AWS Secrets Manager / GCP Secret Manager)

For teams already running Vault. Use the [Vault Agent](https://developer.hashicorp.com/vault/docs/agent-and-proxy/agent) to template `.env` from Vault on container start. Out of scope for this doc; reference the Vault docs.

Pros: dynamic secrets, audit logs, rotation, fine-grained ACLs.
Cons: significant operational overhead; only worthwhile when you already need Vault for other reasons.

### Level 4 -- Compliance-driven (HIPAA, SOC 2, GDPR Article 32)

When auditors are involved, everything in Level 3 + the following:

- **Encryption keys held in a hardware security module (HSM) or KMS** -- e.g., AWS KMS, GCP KMS, Azure Key Vault. The application never sees the raw key; it requests sign / encrypt operations.
- **Audit logging of every secret access.** `src/audit_logger.py` already logs admin operations; extend to log secret retrievals from your secrets backend.
- **Automated rotation.** Quarterly minimum for API keys, monthly for database credentials, weekly for short-lived tokens.
- **Tenant isolation for secrets in a multi-tenant deploy.** Each tenant gets its own KMS key or sops keypair; one tenant's compromise doesn't expose another's secrets.

This level is beyond the scope of this doc; consult your compliance officer and a security engineer.

## CI/CD secrets

GitHub Actions, GitLab CI, etc.

- **Repository / organisation secrets** for CI-only credentials (deploy keys, test database passwords). Reference via `${{ secrets.NAME }}` in workflows; never `echo "$SECRET"` to logs (CI's masking only catches exact matches).
- **Environment-scoped secrets** for prod / staging / dev. Combined with required reviewers, this gives a "deploy needs manual approval" flow without manual secret handling.
- **OIDC-federated identity** for cloud deploys (no static cloud credentials in the CI vault). GitHub Actions supports OIDC against AWS, GCP, Azure.

Example for GitHub Actions:

```yaml
jobs:
  deploy:
    permissions:
      id-token: write  # for OIDC
      contents: read
    environment: production
    steps:
      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::<acct>:role/enhanced-cognee-deploy
          aws-region: us-east-1
      - run: ./deploy/vps/install.sh
        env:
          ENHANCED_API_KEY: ${{ secrets.ENHANCED_API_KEY }}
```

## TLS material in particular

`ENHANCED_HTTPS_CERT_FILE` / `ENHANCED_HTTPS_KEY_FILE` point at PEM files. The private key (key file) is a secret; the cert file is public but reproducible-only-by-the-private-key.

Recommended setup:

- **Local dev:** self-signed certs via `mkcert` (Apache-2.0); cert + key in `~/.config/enhanced-cognee/certs/`.
- **Production single-VPS:** Let's Encrypt via Caddy (Apache-2.0) as a reverse proxy; RNR Enhanced Cognee stays on plain HTTP behind Caddy. Caddy handles automatic cert renewal.
- **Production K8s:** cert-manager (Apache-2.0) issuing certs into Kubernetes secrets, mounted into the pod at the expected paths.

When RNR Enhanced Cognee terminates TLS itself (no reverse proxy), the recommended cert paths are inside a Docker secret or a tmpfs-mounted directory so the private key never persists to a disk image. Example:

```yaml
services:
  RNR-Enhanced-Cognee:
    environment:
      ENHANCED_HTTPS_CERT_FILE: /run/secrets/server_cert
      ENHANCED_HTTPS_KEY_FILE: /run/secrets/server_key
    secrets:
      - server_cert
      - server_key

secrets:
  server_cert:
    file: /etc/letsencrypt/live/example.com/fullchain.pem
  server_key:
    file: /etc/letsencrypt/live/example.com/privkey.pem
```

## Rotation policy

Minimum rotation cadence for each secret class:

| Class | Rotation cadence | Trigger conditions |
| --- | --- | --- |
| Database passwords (`POSTGRES_PASSWORD`, `ARCADEDB_PASSWORD`) | Every 90 days | Suspected leak; departing team member; quarterly review |
| Encryption keys (Fernet, KMS) | Every 365 days; never rotate keys that have encrypted long-lived data without re-encrypting that data first | Suspected leak; audit finding |
| External-service API keys (`LLM_API_KEY`, `QDRANT_API_KEY`) | Every 90 days | Suspected leak; usage anomaly |
| `ENHANCED_API_KEY` | Every 60 days | Any 401 spike (rotate-on-attack); team change |
| TLS certificates | 90 days (Let's Encrypt default) | Cert expiry; domain change |

`src/encryption_manager.py` has a `rotate_encryption_key()` method exposed as an MCP tool (`mcp__cognee__rotate_encryption_key`). It re-encrypts existing memories under the new key and invalidates the old one.

## Project-specific notes

- The docker-compose files are fail-closed: `POSTGRES_PASSWORD`, `ARCADEDB_PASSWORD`, and `NEO4J_PASSWORD` are required (`${VAR:?...}`) with **no baked-in default**, so the stack will not start without them. The local installers (`deploy/local/install.sh` / `install.ps1`) generate a strong random password per service at install time and write it to the stack `.env`. To rotate or set one manually, a 32-byte random string from `python -c "import secrets; print(secrets.token_urlsafe(32))"` works. **Never reuse a known/shared password for any non-localhost deploy.**
- Multi-tenant deployments should also set `ENHANCED_REQUIRE_TENANT=1` (production safety knob) so un-tenanted storage calls raise rather than silently fall back to the global tables. Not a secret, but related to the same trust model.
- `~/.claude.json` is the canonical secrets store for personal Claude Code MCP usage. Keep its mode at `0600` (owner-only read).
- Never commit `.env` files. The repo `.gitignore` already excludes them; if you find one in git history, scrub it (`git filter-repo` or BFG) and rotate every key it contained.

## See also

- [`SECURITY.md`](../SECURITY.md) -- responsible disclosure policy
- [`docs/operations/SECURITY_HARDENING_CHECKLIST.md`](operations/SECURITY_HARDENING_CHECKLIST.md) -- pre-prod checklist
- [`src/mcp_security.py`](../src/mcp_security.py) -- the auth + rate-limit + payload-cap helpers protected by `ENHANCED_API_KEY` and friends
- [`src/encryption_manager.py`](../src/encryption_manager.py) -- Fernet AES-128-CBC encryption at rest
