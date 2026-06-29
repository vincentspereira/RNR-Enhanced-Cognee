# RNR Enhanced Cognee -- Production-Class Host (Terraform)

Turnkey provisioning for the **SLA / soak re-confirmation on real hardware**.
One `terraform apply` brings up a dedicated-vCPU box (Hetzner Cloud or
DigitalOcean), bootstraps the full RNR Enhanced Cognee stack via cloud-init, and
leaves you one SSH command away from a hard PASS/FAIL SLA report.

This exists because the headline capacity numbers
(`tests/benchmarks/baselines/2026-06-04_sla_100users.md`: 210.6 RPS / p95 170ms
/ 0% errors) were captured on a single dev box with the server, 4 DB
containers, and Locust all co-resident. That is the one remaining trust gap for
external commercial scale -- this automation closes it reproducibly.

## Why dedicated vCPU

SLA numbers must be reproducible. Shared-vCPU instances (Hetzner `cx*`,
DigitalOcean Basic `s-*`) suffer noisy-neighbour jitter that muddies p95/p99.
The defaults here are **dedicated-vCPU** boxes:

| Provider | Default | Spec | ~Cost |
| --- | --- | --- | --- |
| Hetzner | `ccx23` | 4 dedicated vCPU / 16 GB | ~EUR 25/mo (hourly billed) |
| DigitalOcean | `c-4` | 4 dedicated vCPU / 8 GB | ~$0.12/hr |

Both are billed hourly -- spin up, measure, `terraform destroy`. A full
SLA+soak run costs well under a dollar of compute.

## Prerequisites

- [Terraform](https://developer.hashicorp.com/terraform/install) >= 1.5
- A provider API token (Hetzner: Project -> Security -> API Tokens;
  DigitalOcean: API -> Tokens)
- An SSH keypair

## Quick start (Hetzner)

```bash
cd deploy/terraform/hetzner
cp terraform.tfvars.example terraform.tfvars
# edit terraform.tfvars: hcloud_token + ssh_public_key (lock ssh_allowed_cidrs to your IP)

terraform init
terraform apply            # ~30s to create; cloud-init finishes in ~3-4 min

# Re-confirm the SLA (+ optional soak) on the box:
terraform output -raw run_sla_suite | bash
#   -> runs tests/load/run_perf_suite.sh both
#   -> SLA burst prints PASS/FAIL; soak runs SOAK_DURATION (default 4h)

terraform destroy          # throwaway host -- tear it down when done
```

DigitalOcean is identical under `deploy/terraform/digitalocean/` (`do_token`,
`droplet_size`, `region`).

## What cloud-init does (`../cloud-init.yaml.tftpl`)

The automated equivalent of `deploy/vps/README.md` steps 2-9:

1. Creates the unprivileged `cognee` user, installs your SSH key.
2. Hardens SSH (key-only, no root) + enables `fail2ban`.
3. Installs Docker, Compose, Python, UFW; firewall allows only 22/80/443.
4. Clones the repo to `/opt/enhanced-cognee` at `repo_ref`.
5. **Generates strong DB passwords on the box** (`openssl rand`) into a
   600-perm `.env` -- secrets never transit Terraform state. The
   auto-generated `ENHANCED_API_KEY` is saved to
   `/root/enhanced-cognee-api-key.txt`.
6. Brings up the Docker stack (`docker compose up -d --build`). The functional
   GIN FTS index ships in `docker/init-scripts/01-init-pgvector.sql`, so the
   search path is fast from first boot.
7. Creates a `.venv-perf` with `locust` + `psutil` for on-box load generation.
8. Installs the nightly backup cron.

Progress log on the box: `/var/log/enhanced-cognee-bootstrap.log`. The marker
file `/opt/.enhanced-cognee-bootstrapped` appears when it's done.

## On-box vs off-box load generation

By default the load generator runs **on the box** (matching how the dev-box
baseline was captured, just on better silicon) and the app port stays internal.

For the **gold-standard** measurement (load generator off-box, so it never
competes with the stack for CPU):

1. Set `app_port_allowed_cidrs = ["<your-ip>/32"]` in `terraform.tfvars` to
   open port 8080 to your machine.
2. From your machine, point Locust at the box:
   ```bash
   python -m locust -f tests/load/locustfile.py --headless \
     --host http://<box-ip>:8080 --users 100 --spawn-rate 10 --run-time 90s \
     --csv sla_offbox --only-summary
   ```

## Outputs

| Output | Meaning |
| --- | --- |
| `ipv4` | Public IP |
| `ssh` | `ssh cognee@<ip>` |
| `run_sla_suite` | One-liner to run the SLA + soak suite |

## Security notes

- `terraform.tfvars`, `*.tfstate*`, and `.terraform/` are gitignored. State can
  contain the token -- keep it local or use a remote backend.
- Lock `ssh_allowed_cidrs` to your IP for a throwaway host.
- This is a **test host**, not a hardened long-running production deployment.
  For that, see `deploy/vps/README.md` (TLS via Caddy, domain, monitoring).
