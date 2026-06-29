# ===========================================================================
# RNR Enhanced Cognee -- Hetzner Cloud production-class host (Terraform)
# ===========================================================================
# Provisions a single dedicated-vCPU box on Hetzner Cloud, bootstrapped by
# cloud-init (../cloud-init.yaml.tftpl) into a running RNR Enhanced Cognee stack,
# so the production-hardware SLA re-confirmation is `terraform apply` away.
#
# Why dedicated vCPU (ccx*) and not shared (cx*): SLA numbers must be
# reproducible. Shared-vCPU instances suffer noisy-neighbour jitter that
# muddies p95/p99. The cheap cx22 in deploy/vps/README.md is fine for *serving*
# the workload; for *measuring* it, dedicated vCPU is the right tool.
#
# Usage:
#   cd deploy/terraform/hetzner
#   cp terraform.tfvars.example terraform.tfvars   # fill in hcloud_token + ssh key
#   terraform init && terraform apply
#   # wait ~3-4 min for cloud-init, then:
#   ssh cognee@$(terraform output -raw ipv4) \
#     'sudo -u cognee /opt/enhanced-cognee/tests/load/run_perf_suite.sh both'
#   terraform destroy   # tear down when done (this is a throwaway test host)
# ===========================================================================

terraform {
  required_version = ">= 1.5"
  required_providers {
    hcloud = {
      source  = "hetznercloud/hcloud"
      version = "~> 1.48"
    }
  }
}

provider "hcloud" {
  token = var.hcloud_token
}

resource "hcloud_ssh_key" "operator" {
  name       = "${var.name}-key"
  public_key = var.ssh_public_key
}

resource "hcloud_firewall" "ec" {
  name = "${var.name}-fw"

  # SSH
  rule {
    direction  = "in"
    protocol   = "tcp"
    port       = "22"
    source_ips = var.ssh_allowed_cidrs
  }
  # HTTP (Caddy ACME challenge) + HTTPS
  rule {
    direction  = "in"
    protocol   = "tcp"
    port       = "80"
    source_ips = ["0.0.0.0/0", "::/0"]
  }
  rule {
    direction  = "in"
    protocol   = "tcp"
    port       = "443"
    source_ips = ["0.0.0.0/0", "::/0"]
  }
  # Optional: expose the app port 8080 ONLY to explicit CIDRs, for running the
  # load generator off-box (the gold-standard SLA setup). Empty by default ->
  # no rule, so the app stays internal and load-gen runs on-box.
  dynamic "rule" {
    for_each = length(var.app_port_allowed_cidrs) > 0 ? [1] : []
    content {
      direction  = "in"
      protocol   = "tcp"
      port       = "8080"
      source_ips = var.app_port_allowed_cidrs
    }
  }
}

resource "hcloud_server" "ec" {
  name        = var.name
  server_type = var.server_type
  image       = "ubuntu-24.04"
  location    = var.location
  ssh_keys    = [hcloud_ssh_key.operator.id]
  firewall_ids = [hcloud_firewall.ec.id]

  user_data = templatefile("${path.module}/../cloud-init.yaml.tftpl", {
    ssh_pubkey       = var.ssh_public_key
    repo_url         = var.repo_url
    repo_ref         = var.repo_ref
    enhanced_api_key = var.enhanced_api_key
  })

  labels = {
    project = "enhanced-cognee"
    purpose = "sla-soak"
  }
}
