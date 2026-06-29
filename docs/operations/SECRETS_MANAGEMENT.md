# Secrets Management

**Per Q9 in PRODUCTION_READINESS_PLAN.md:** "agent decides on the best for
this system". Decision: **Docker secrets + locked-down `.env`** for simplicity.
sops/age recommended only when you need multi-developer encrypted secrets in git.

## Approach 1 (Recommended for Self-Hosted): Locked-Down `.env`

### Setup

```bash
# 1. Create the secrets file outside the repo
sudo mkdir -p /etc/enhanced-cognee
sudo touch /etc/enhanced-cognee/secrets.env
sudo chmod 600 /etc/enhanced-cognee/secrets.env
sudo chown cognee:cognee /etc/enhanced-cognee/secrets.env

# 2. Edit with your real credentials
sudo nano /etc/enhanced-cognee/secrets.env
```

Content:

```bash
POSTGRES_PASSWORD=<generate-32-char-random-string>
NEO4J_PASSWORD=<generate-32-char-random-string>
REDIS_PASSWORD=<generate-32-char-random-string>
QDRANT_API_KEY=<generate-32-char-random-string>
JWT_SECRET=<generate-64-char-random-string>
ANTHROPIC_API_KEY=sk-ant-...
GMAIL_APP_PASSWORD=<16-char-app-password>
```

### Generate strong passwords

```bash
# Linux/macOS
openssl rand -base64 32

# Windows PowerShell
[Convert]::ToBase64String((1..32 | ForEach-Object {Get-Random -Maximum 256}))
```

### Reference in systemd unit

In `/etc/systemd/system/enhanced-cognee.service`:

```ini
[Service]
EnvironmentFile=-/etc/enhanced-cognee/secrets.env
Environment="POSTGRES_HOST=localhost"
# ... non-secret env ...
```

The `EnvironmentFile=-` prefix (with hyphen) means "ignore if missing", so the
service still starts on dev machines without the secrets file.

### Reference in Docker Compose

Mount the secrets file as an env_file:

```yaml
services:
  enhanced-cognee-mcp:
    env_file:
      - /etc/enhanced-cognee/secrets.env
    environment:
      POSTGRES_HOST: postgres   # non-secret
```

### Rotation

```bash
# 1. Generate new value
NEW_PG_PWD=$(openssl rand -base64 32)

# 2. Update Postgres
docker exec cognee-mcp-postgres psql -U postgres -c \
    "ALTER USER cognee_user WITH PASSWORD '$NEW_PG_PWD';"

# 3. Update secrets file
sudo sed -i "s|^POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=$NEW_PG_PWD|" \
    /etc/enhanced-cognee/secrets.env

# 4. Restart RNR Enhanced Cognee
sudo systemctl restart RNR-Enhanced-Cognee
```

**Rotation cadence:** every 90 days for DB passwords, every 30 days for JWT
secret, immediately on any suspected leak.

## Approach 2: Docker Secrets (Swarm mode)

If you're using Docker Swarm or Kubernetes, prefer native secrets:

```bash
echo "your-postgres-password" | docker secret create pg_password -
```

Then reference in compose:

```yaml
services:
  postgres:
    image: pgvector/pgvector:pg16
    secrets:
      - pg_password
    environment:
      POSTGRES_PASSWORD_FILE: /run/secrets/pg_password

secrets:
  pg_password:
    external: true
```

This avoids any plaintext secrets on disk and integrates with Vault / AWS Secrets
Manager when you scale up.

## Approach 3: sops + age (For Multi-Developer Encrypted-In-Git Secrets)

Use this when:
- Multiple developers need to deploy
- You want secrets committed (encrypted) to git for audit trail
- You're operating across multiple environments

### One-time setup

```bash
# Install age (modern encryption tool)
brew install age  # macOS
# or download from https://github.com/FiloSottile/age/releases

# Install sops
brew install sops
# or https://github.com/getsops/sops/releases

# Generate a key pair
age-keygen -o ~/.age/key.txt
# Note the public key from the output, e.g.:
# age1abc...xyz
```

### Configure sops

Create `.sops.yaml` in repo root:

```yaml
creation_rules:
  - path_regex: \.enc\.yaml$
    age: age1abc...xyz   # paste your public key(s) here; multiple = multi-recipient
```

### Encrypt a secrets file

```bash
# Edit secrets
sops .secrets.enc.yaml

# In your editor, write plain YAML:
postgres_password: my-strong-pwd
neo4j_password: another-strong-pwd

# Save & close - sops encrypts in place
```

### Decrypt at runtime

```bash
# In your deploy script
export SOPS_AGE_KEY_FILE=~/.age/key.txt
eval $(sops -d .secrets.enc.yaml | yq -r 'to_entries | .[] | "export " + (.key | ascii_upcase) + "=\"" + .value + "\""')
docker compose up -d
```

### Pros / Cons

| | Locked-down `.env` | Docker Swarm Secrets | sops + age |
|---|---|---|---|
| Setup time | 5 min | 30 min | 1 hr (learning curve) |
| Multi-dev safe | No (manual transfer) | Yes (via Vault) | Yes (encrypted in git) |
| Audit trail | No | Limited | Full (git history) |
| Operational overhead | Low | Medium | Medium |
| Cost | Free | Free | Free |
| Best for | Solo / small team | Production Swarm | Multi-dev / regulated |

## What NOT to do

- **Don't** commit unencrypted `.env` to git (already in `.gitignore`)
- **Don't** put secrets in `docker-compose.yml` directly (use env_file)
- **Don't** use the same password for prod and dev
- **Don't** rotate secrets without a rollback plan
- **Don't** email secrets — use Bitwarden / 1Password vault sharing
- **Don't** log secrets — the audit_logger has redaction for known keys

## Recommendation

For Vincent's current scope (single-user, self-hosted laptop + future single-VPS):
**Use Approach 1 (locked-down `.env`)**. It's the simplest and meets all your
security requirements. Revisit when you scale to 2+ deployments or accept
external contributors who need deploy access.
