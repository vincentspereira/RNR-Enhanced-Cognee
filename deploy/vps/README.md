# Enhanced Cognee VPS Deployment Guide

Self-hosted single-VPS deployment, optimised for cost (target < $10/month).
No Kubernetes, no managed databases. Just Docker Compose + Caddy + systemd
on a fresh Ubuntu 24.04 box.

## Recommended Provider

**Hetzner Cloud CX22** (~ EUR 4.50/month, Germany/Finland data centres)
- 2 vCPU, 4 GB RAM, 40 GB SSD
- Generous traffic allowance (20 TB)
- IPv4 + IPv6 included
- EU GDPR jurisdiction

Alternative: **DigitalOcean Basic Droplet** ($6/month) if you need a non-EU
region. Slightly less RAM (1 GB on the entry tier — too small; pick the
$12/month 2 GB tier).

Recommendation: **Hetzner CX22**. Best price/performance for this workload.

## Prerequisites

- A domain name pointing to your VPS IPv4 (e.g. `cognee.example.com`)
- SSH access as a non-root sudo user
- Docker Hub / GitHub credentials if you'll pull private images (optional)

## One-time Setup (copy/paste runbook)

### 1. Provision the VPS

Order a Hetzner CX22 with Ubuntu 24.04. Save the IPv4. Point a DNS A record
at it: `cognee.example.com -> <IPv4>`.

### 2. Initial server hardening

SSH in as root the first time, then create a sudo user and disable root login.

```bash
ssh root@<IPv4>

# Create a sudo user
adduser cognee
usermod -aG sudo cognee

# Lock down SSH (key-only, no root)
sed -i 's/^#*PermitRootLogin .*/PermitRootLogin no/' /etc/ssh/sshd_config
sed -i 's/^#*PasswordAuthentication .*/PasswordAuthentication no/' /etc/ssh/sshd_config

# Push your public key to the new user
mkdir -p /home/cognee/.ssh
cp ~/.ssh/authorized_keys /home/cognee/.ssh/
chown -R cognee:cognee /home/cognee/.ssh
chmod 700 /home/cognee/.ssh
chmod 600 /home/cognee/.ssh/authorized_keys

systemctl restart ssh
```

Now log out and reconnect as `cognee@<IPv4>`. The rest runs as the unprivileged user.

### 3. Install Docker + Caddy

```bash
# Docker (official convenience script)
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
# Log out + back in for the group change to take effect
exit
ssh cognee@<IPv4>

# Caddy (official APT repo)
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | \
    sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | \
    sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update
sudo apt install -y caddy

# UFW firewall: only SSH + HTTPS exposed
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp     # Caddy needs port 80 for cert challenges
sudo ufw allow 443/tcp
sudo ufw --force enable
```

### 4. Clone Enhanced Cognee

```bash
sudo apt install -y git python3.12 python3.12-venv python3-pip
cd /opt
sudo git clone https://github.com/vincentspereira/Enhanced-Cognee.git enhanced-cognee
sudo chown -R cognee:cognee /opt/enhanced-cognee
cd /opt/enhanced-cognee
```

### 5. Create the .env secrets file

The compose stack now FAILS CLOSED if required secrets are missing -- there are
no insecure defaults. Create `/opt/enhanced-cognee/.env` with at least:

```bash
cat > /opt/enhanced-cognee/.env <<'EOF'
# Required -- the stack refuses to start without these.
POSTGRES_PASSWORD=change-me-strong-pg
NEO4J_PASSWORD=change-me-strong-graph   # ArcadeDB root password (or set ARCADEDB_PASSWORD)
LLM_API_KEY=your-llm-api-key
ENHANCED_API_KEY=change-me-strong-api-key
ENHANCED_ENV=production

# Optional
REDIS_PASSWORD=
QDRANT_API_KEY=
LLM_MODEL=glm-4.6
LLM_PROVIDER=zai
LLM_ENDPOINT=https://api.z.ai/v1
EOF

chmod 600 /opt/enhanced-cognee/.env
```

### 6. Bring up the Docker stack (databases + app)

```bash
docker compose -f docker/docker-compose-enhanced-cognee.yml up -d --build
docker ps
# 4 DB containers + the enhanced-cognee app should report 'healthy' within ~30-60s.
# The app is built from docker/Dockerfile.enhanced-cognee and listens on
# host port 28080 (container 8080). DB ports are bound to 127.0.0.1 only.
```

This single command now runs everything, including the FastAPI app -- you do
NOT also need the systemd unit in step 9 (that is an alternative host-based
runner for operators who prefer running the app outside Docker).

### 7. Configure Caddy reverse proxy

Copy the bundled Caddyfile and edit the domain placeholder:

```bash
sudo cp /opt/enhanced-cognee/deploy/vps/Caddyfile /etc/caddy/Caddyfile
sudo sed -i 's/cognee.example.com/<YOUR-DOMAIN>/g' /etc/caddy/Caddyfile

# Reload Caddy
sudo systemctl reload caddy
```

Caddy will automatically obtain a Let's Encrypt certificate on first request.
Point its reverse_proxy upstream at the app:
- Compose-run app (step 6, default): `127.0.0.1:28080`
- Host systemd app (step 8, alternative): `127.0.0.1:8080`

### 8. (Alternative) Run the FastAPI app on the host via systemd

SKIP this if you used the compose stack in step 6 -- it already runs the app in
a container. This unit is for operators who prefer running the app directly on
the host (listens on 127.0.0.1:8080). It reads secrets from
`/etc/enhanced-cognee/secrets.env` (600 perms; same required keys as the .env in
step 5) and waits for the `postgres-enhanced-cognee` container to be healthy.

```bash
# Host venv is only needed for this alternative path:
sudo apt install -y python3.12 python3.12-venv python3-pip
python3.12 -m venv .venv && source .venv/bin/activate
pip install --upgrade pip && pip install -e .

sudo mkdir -p /etc/enhanced-cognee
sudo cp /opt/enhanced-cognee/.env /etc/enhanced-cognee/secrets.env
sudo chmod 600 /etc/enhanced-cognee/secrets.env

sudo cp /opt/enhanced-cognee/deploy/vps/enhanced-cognee.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now enhanced-cognee
sudo systemctl status enhanced-cognee
```

### 9. Configure nightly backups

```bash
sudo cp /opt/enhanced-cognee/deploy/vps/backup.sh /usr/local/bin/cognee-backup
sudo chmod +x /usr/local/bin/cognee-backup
sudo mkdir -p /var/backups/enhanced-cognee
sudo chown cognee:cognee /var/backups/enhanced-cognee

# Add to root crontab (runs at 02:30 nightly)
echo '30 2 * * * /usr/local/bin/cognee-backup >> /var/log/cognee-backup.log 2>&1' | sudo tee /etc/cron.d/cognee-backup
```

### 10. Smoke test

```bash
# Readiness: 200 when all critical dependencies are up; 503 if any dep is down.
curl -sf https://<YOUR-DOMAIN>/health/ready && echo "READY (200)"
# Liveness: 200 whenever the process is running (does not check dependencies).
curl -sf https://<YOUR-DOMAIN>/health/live && echo "LIVE (200)"
```

`/health/ready` returns HTTP 503 (so `curl -sf` exits non-zero) when a critical
dependency such as PostgreSQL or the graph DB is unavailable -- use it as the
real "is the service usable" check. ENHANCED_API_KEY and ENHANCED_ENV=production
must be set (step 5) or the app will refuse to start.

## Day-2 Operations

| Task | Command |
| ---- | ------- |
| View MCP server logs | `journalctl -u enhanced-cognee -f` |
| View Docker logs | `cd /opt/enhanced-cognee && docker compose logs -f` |
| Restart MCP server | `sudo systemctl restart enhanced-cognee` |
| Restart Docker stack | `cd /opt/enhanced-cognee && docker compose restart` |
| Update from git | `cd /opt/enhanced-cognee && git pull && sudo systemctl restart enhanced-cognee` |
| List backups | `ls -lh /var/backups/enhanced-cognee/` |
| Manual backup | `sudo /usr/local/bin/cognee-backup` |

## Cost Summary

| Item | Monthly Cost |
| ---- | ------------ |
| Hetzner CX22 | EUR 4.50 |
| Domain (.dev / .com) | ~ EUR 1 (amortised) |
| Let's Encrypt cert | Free |
| Backup storage (40 GB SSD) | Included |
| **Total** | **~ EUR 5.50 / month** |

For higher traffic, upgrade to CX32 (4 vCPU / 8 GB) at EUR 7.55/month.

## Security Checklist

- [x] SSH key-only login, root disabled
- [x] UFW firewall: only 22 + 80 + 443 exposed
- [x] Caddy auto-renews TLS certs
- [x] Nightly backups to `/var/backups/enhanced-cognee/`
- [x] Docker containers run as non-root inside
- [x] systemd hardening flags in `enhanced-cognee.service`
- [ ] Configure fail2ban for SSH brute-force protection (TODO)
- [ ] Enable Hetzner's free DDoS protection (in dashboard)
- [ ] Encrypt the data volumes at rest (`cryptsetup` on LVM) — optional

## Troubleshooting

- **502 Bad Gateway**: MCP server is down. `sudo systemctl status enhanced-cognee`
- **Healthcheck returns 503**: One of the 4 databases is unhealthy. `docker ps`.
- **Caddy can't get cert**: DNS A record is wrong or port 80 is blocked.
- **Out of disk**: Old backups accumulating. The backup script rotates after 30 days.

See `docs/operations/RUNBOOK.md` for more incident scenarios.
