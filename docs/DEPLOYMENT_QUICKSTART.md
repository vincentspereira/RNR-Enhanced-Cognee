# Enhanced Cognee Deployment Quickstart

Two paths, depending on where you're deploying.

| Path | When to use | Time |
|---|---|---|
| **A. Local (Windows laptop)** | Personal use, dev, integration with MAS | 10 min |
| **B. VPS (Hetzner CX22)** | Production, shared with team, internet-reachable | 45 min |

Both paths assume you already have:
- The repo cloned at `C:\Users\vince\Projects\AI Agents\enhanced-cognee\` (or equivalent)
- Docker Desktop installed
- Python 3.11+ installed
- Claude Code installed

---

## PATH A: Local Windows Laptop Deployment

This is what you're already running. The Docker stack is up, the MCP server is
registered. These steps cover what to do if you ever need to set it up from
scratch on a fresh machine.

### A1. Verify the Docker stack is healthy

Open PowerShell:

```powershell
docker ps
```

You should see 4 containers, all `(healthy)`:
- `cognee-mcp-postgres` (port 25432)
- `cognee-mcp-qdrant` (port 26333)
- `cognee-mcp-neo4j` (port 27687)
- `cognee-mcp-valkey` (port 26379)

If any are missing or unhealthy:

```powershell
cd "C:\Users\vince\Projects\AI Agents\enhanced-cognee"
docker compose -f docker/docker-compose-enhanced-cognee.yml up -d
# Wait 30 seconds, then check again
docker ps
```

### A2. Run the smoke test

```powershell
cd "C:\Users\vince\Projects\AI Agents\enhanced-cognee"

# Postgres
docker exec cognee-mcp-postgres pg_isready -U cognee_user
# Expected output: localhost:5432 - accepting connections

# Qdrant
curl http://localhost:26333/healthz
# Expected: 200 OK

# Valkey (Redis-compatible cache; replaces Redis 7.4+ for license reasons,
# see docs/LICENSE_AUDIT.md)
docker exec cognee-mcp-valkey valkey-cli PING
# Expected: PONG

# Neo4j
curl http://localhost:27474
# Expected: 200 OK
```

If all 4 return success, the stack is healthy.

**Note:** `make smoke` is a Linux-style command. On native Windows, the manual
commands above are equivalent. If you use WSL or Git Bash, `make smoke` works
out of the box.

### A3. Install the MCP server in Claude Code

```powershell
# Run the installer (idempotent - safe to re-run)
cd "C:\Users\vince\Projects\AI Agents\enhanced-cognee"
powershell -ExecutionPolicy Bypass -File deploy/local/install.ps1
```

The installer:
1. Confirms Python 3.11+ is installed
2. Creates `.venv` if missing
3. Installs Enhanced Cognee in editable mode
4. Verifies Docker stack is healthy
5. Registers the MCP server in `%USERPROFILE%\.claude.json`

To also enable auto-start on Windows login:

```powershell
powershell -ExecutionPolicy Bypass -File deploy/local/install.ps1 -AutoStart
```

This creates a Task Scheduler entry that brings up the Docker stack when you log in.

### A4. Restart Claude Code

Quit Claude Code completely (right-click tray icon -> Exit). Reopen it.

### A5. Verify the MCP server is connected

In Claude Code, run:

```
/mcp
```

You should see `cognee` listed with green status. If it shows red/failed:

1. Open `%USERPROFILE%\.claude.json` and verify the `cognee` entry has correct
   paths to the venv Python and the MCP server script
2. Open a PowerShell, run the MCP server directly and look for errors:
   ```powershell
   cd "C:\Users\vince\Projects\AI Agents\enhanced-cognee"
   .venv\Scripts\python.exe bin\enhanced_cognee_mcp_server.py
   ```
3. Most common cause: Docker stack not running. Run `docker ps` and confirm.

### A6. Test the integration

In Claude Code, try:

```
Hey Claude, please use the Enhanced Cognee MCP to store this memory:
"Production deployment quickstart was followed successfully on <date>"
```

Claude should call `add_memory(...)` and confirm. Then:

```
Now please search for "production deployment"
```

Claude should call `search_memories(query="production deployment")` and return
the memory you just stored.

### A7. (Optional) Integrate with the Multi-Agent System

If you want the MAS agents at `C:\Users\vince\Projects\AI Agents\Multi-Agent System`
to use Enhanced Cognee as their memory layer, follow
[`deploy/integration-with-mas/README.md`](../deploy/integration-with-mas/README.md).

---

## PATH B: Hetzner CX22 VPS Deployment

For when you want public access (e.g. for a team) or to free up your laptop.

**Cost: ~ EUR 4.50/month**. Single VPS, no managed databases, no Kubernetes.

### B1. Order the VPS

1. Open https://www.hetzner.com/cloud
2. Sign up (no credit card needed for the trial month if you're new)
3. Create a new project ("Enhanced Cognee")
4. Click **Add Server**:
   - Location: pick closest to you (Falkenstein DE / Helsinki FI / Ashburn US)
   - Image: **Ubuntu 24.04**
   - Type: **CX22** (2 vCPU, 4 GB RAM, 40 GB SSD - EUR 4.50/mo)
   - Networking: leave defaults (IPv4 + IPv6 included)
   - SSH key: add yours (`~/.ssh/id_ed25519.pub`) - do NOT use password auth
   - Name: `enhanced-cognee-1`
5. Click **Create & Buy now**

You'll be assigned an IPv4 within 30 seconds. Save it.

### B2. Point a domain at the VPS

You need a domain like `cognee.example.com`.

If you don't have one, buy one cheaply:
- **Cloudflare Registrar** ($9/year .com, no markup)
- **Namecheap** ($5-15/year)

Add an **A record**: `cognee.example.com -> <YOUR_VPS_IPV4>`. Set TTL to 300.

Wait ~5 minutes for DNS propagation.

### B3. First SSH login + harden

```bash
# From your laptop:
ssh root@<YOUR_VPS_IPV4>

# Create a non-root sudo user
adduser cognee        # set a strong password
usermod -aG sudo cognee

# Disable root login + password auth
sed -i 's/^#*PermitRootLogin .*/PermitRootLogin no/' /etc/ssh/sshd_config
sed -i 's/^#*PasswordAuthentication .*/PasswordAuthentication no/' /etc/ssh/sshd_config

# Copy your authorized_keys to the new user
mkdir -p /home/cognee/.ssh
cp ~/.ssh/authorized_keys /home/cognee/.ssh/
chown -R cognee:cognee /home/cognee/.ssh
chmod 700 /home/cognee/.ssh
chmod 600 /home/cognee/.ssh/authorized_keys

systemctl restart ssh

exit
```

Reconnect as the unprivileged user:

```bash
ssh cognee@<YOUR_VPS_IPV4>
```

If this works, root is locked. If it doesn't, you're locked out -- use Hetzner's
web console to fix it.

### B4. Install Docker, Caddy, firewall

Copy-paste the entire block:

```bash
# Docker
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
exit
ssh cognee@<YOUR_VPS_IPV4>   # log back in for group change to take effect

# Caddy (automatic HTTPS reverse proxy)
sudo apt update
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | \
    sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | \
    sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update
sudo apt install -y caddy

# Firewall: only SSH + HTTP + HTTPS
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp     # Let's Encrypt cert challenge
sudo ufw allow 443/tcp    # HTTPS to Caddy
sudo ufw --force enable

# Python + git
sudo apt install -y git python3.12 python3.12-venv python3-pip
```

### B5. Clone Enhanced Cognee + bring up Docker stack

```bash
cd /opt
sudo git clone https://github.com/vincentspereira/Enhanced-Cognee.git enhanced-cognee
sudo chown -R cognee:cognee /opt/enhanced-cognee
cd /opt/enhanced-cognee

# Bring up the 4-database stack
docker compose -f docker/docker-compose-enhanced-cognee.yml up -d

# Wait ~30 seconds, then verify
docker ps
# Should show 4 healthy containers
```

### B6. Install Python deps

```bash
cd /opt/enhanced-cognee
python3.12 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e .
```

### B7. Configure Caddy with your domain

```bash
sudo cp /opt/enhanced-cognee/deploy/vps/Caddyfile /etc/caddy/Caddyfile

# Replace the placeholder with YOUR domain
sudo sed -i 's/cognee.example.com/<YOUR_DOMAIN>/g' /etc/caddy/Caddyfile

# Reload Caddy (it will request a TLS cert from Let's Encrypt on first visit)
sudo systemctl reload caddy

# Watch the logs to confirm cert acquisition
sudo journalctl -u caddy -f
# Press Ctrl+C once you see "certificate obtained successfully"
```

### B8. Run the FastAPI MCP server as a systemd service

```bash
sudo cp /opt/enhanced-cognee/deploy/vps/enhanced-cognee.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now enhanced-cognee
sudo systemctl status enhanced-cognee
# Should show "active (running)"
```

### B9. Configure nightly backups

```bash
sudo cp /opt/enhanced-cognee/deploy/vps/backup.sh /usr/local/bin/cognee-backup
sudo chmod +x /usr/local/bin/cognee-backup
sudo mkdir -p /var/backups/enhanced-cognee
sudo chown cognee:cognee /var/backups/enhanced-cognee

# Add cron job: nightly at 02:30
echo '30 2 * * * cognee /usr/local/bin/cognee-backup >> /var/log/cognee-backup.log 2>&1' | sudo tee /etc/cron.d/cognee-backup

# Test manually
sudo -u cognee /usr/local/bin/cognee-backup
ls -lh /var/backups/enhanced-cognee/
# Should show a new directory named with today's timestamp
```

### B10. Smoke test from your laptop

```bash
# From your laptop:
curl -sf https://cognee.example.com/health
# Expected: {"status":"ok","services":{"postgres":"ok","qdrant":"ok","neo4j":"ok","redis":"ok"}}
```

If you get TLS errors, wait 1-2 minutes (Let's Encrypt may still be issuing).
If you get connection refused, check `sudo ufw status` and `sudo systemctl status enhanced-cognee`.

### B11. Hook your Claude Code into the remote MCP server

This requires the Python SDK client:

```bash
# On your laptop:
pip install enhanced-cognee-client
```

Then edit `~/.claude.json` to add a remote MCP entry (replace the local one):

```json
{
  "mcpServers": {
    "cognee": {
      "command": "python",
      "args": ["-m", "enhanced_cognee_client.mcp_proxy"],
      "env": {
        "ENHANCED_COGNEE_URL": "https://cognee.example.com",
        "ENHANCED_COGNEE_API_KEY": "<your-api-key>"
      }
    }
  }
}
```

Restart Claude Code. The MCP server now routes all 122 tool calls through HTTPS
to your VPS.

### B12. Operations cheatsheet

| Task | Command |
|---|---|
| Watch MCP server logs | `sudo journalctl -u enhanced-cognee -f` |
| Watch DB logs | `cd /opt/enhanced-cognee && docker compose logs -f` |
| Restart MCP server | `sudo systemctl restart enhanced-cognee` |
| Restart Docker stack | `cd /opt/enhanced-cognee && docker compose restart` |
| Update from GitHub | `cd /opt/enhanced-cognee && git pull && sudo systemctl restart enhanced-cognee` |
| Manual backup | `sudo -u cognee /usr/local/bin/cognee-backup` |
| List backups | `ls -lh /var/backups/enhanced-cognee/` |
| Disk usage | `df -h && du -sh /var/lib/docker /var/backups/enhanced-cognee` |

For more detailed troubleshooting see [`docs/operations/RUNBOOK.md`](operations/RUNBOOK.md).

---

## Common Issues

### "MCP server failed to connect" in Claude Code

1. `docker ps` -- are all 4 containers up?
2. `tail -20 ~/.claude/logs/mcp.log` -- look for the actual error
3. Try running the server directly to see stderr:
   ```powershell
   cd "C:\Users\vince\Projects\AI Agents\enhanced-cognee"
   .venv\Scripts\python.exe bin\enhanced_cognee_mcp_server.py
   ```

### "Permission denied" running install.ps1

PowerShell blocks unsigned scripts by default. Use:

```powershell
powershell -ExecutionPolicy Bypass -File deploy/local/install.ps1
```

Or change execution policy once:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### "DNS not resolving" for VPS

Wait 5-10 minutes after creating the A record. Verify with:

```bash
dig +short cognee.example.com
# Should return your VPS IPv4
```

If still not resolving after 15 minutes, check Cloudflare/Namecheap dashboard
for the correct record.

### "Let's Encrypt cert acquisition failed"

Caddy needs port 80 reachable. Check:
- `sudo ufw status` includes `80/tcp ALLOW`
- Your Hetzner firewall (separate from UFW) allows port 80
- DNS is resolving correctly

### Docker stack consumes too much RAM

The CX22's 4GB is enough for typical workloads. If you hit OOM:
- Upgrade to CX32 (8 GB, EUR 7.55/mo)
- Or tune resource limits in `docker/docker-compose-enhanced-cognee.yml` (add
  `deploy.resources.limits.memory: 512M` per service)

### "Caddy returns 502 Bad Gateway"

The MCP server (port 8000) isn't responding:

```bash
sudo systemctl status enhanced-cognee
sudo journalctl -u enhanced-cognee --since "5 minutes ago"
```

Most common cause: a database is unhealthy. `docker ps` to verify.
