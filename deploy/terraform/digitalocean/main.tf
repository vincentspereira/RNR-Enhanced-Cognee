# ===========================================================================
# Enhanced Cognee -- DigitalOcean production-class host (Terraform)
# ===========================================================================
# DigitalOcean equivalent of the Hetzner config. Provisions a CPU-Optimized
# (dedicated-vCPU) droplet, bootstrapped by the shared cloud-init template into
# a running Enhanced Cognee stack for the SLA / soak re-confirmation.
#
# Why CPU-Optimized (c-*): dedicated vCPU -> reproducible p95/p99 (no
# noisy-neighbour jitter). Basic droplets share CPU and muddy the numbers.
#
# Usage:
#   cd deploy/terraform/digitalocean
#   cp terraform.tfvars.example terraform.tfvars   # fill in do_token + ssh key
#   terraform init && terraform apply
#   ssh cognee@$(terraform output -raw ipv4) \
#     'sudo -u cognee /opt/enhanced-cognee/tests/load/run_perf_suite.sh both'
#   terraform destroy
# ===========================================================================

terraform {
  required_version = ">= 1.5"
  required_providers {
    digitalocean = {
      source  = "digitalocean/digitalocean"
      version = "~> 2.40"
    }
  }
}

provider "digitalocean" {
  token = var.do_token
}

resource "digitalocean_ssh_key" "operator" {
  name       = "${var.name}-key"
  public_key = var.ssh_public_key
}

resource "digitalocean_droplet" "ec" {
  name     = var.name
  image    = "ubuntu-24-04-x64"
  size     = var.droplet_size
  region   = var.region
  ssh_keys = [digitalocean_ssh_key.operator.fingerprint]

  user_data = templatefile("${path.module}/../cloud-init.yaml.tftpl", {
    ssh_pubkey       = var.ssh_public_key
    repo_url         = var.repo_url
    repo_ref         = var.repo_ref
    enhanced_api_key = var.enhanced_api_key
  })

  tags = ["enhanced-cognee", "sla-soak"]
}

resource "digitalocean_firewall" "ec" {
  name        = "${var.name}-fw"
  droplet_ids = [digitalocean_droplet.ec.id]

  inbound_rule {
    protocol         = "tcp"
    port_range       = "22"
    source_addresses = var.ssh_allowed_cidrs
  }
  inbound_rule {
    protocol         = "tcp"
    port_range       = "80"
    source_addresses = ["0.0.0.0/0", "::/0"]
  }
  inbound_rule {
    protocol         = "tcp"
    port_range       = "443"
    source_addresses = ["0.0.0.0/0", "::/0"]
  }
  # Optional OFF-box load-gen access to the app port.
  dynamic "inbound_rule" {
    for_each = length(var.app_port_allowed_cidrs) > 0 ? [1] : []
    content {
      protocol         = "tcp"
      port_range       = "8080"
      source_addresses = var.app_port_allowed_cidrs
    }
  }

  # Allow all outbound (package installs, git clone, ACME).
  outbound_rule {
    protocol              = "tcp"
    port_range            = "1-65535"
    destination_addresses = ["0.0.0.0/0", "::/0"]
  }
  outbound_rule {
    protocol              = "udp"
    port_range            = "1-65535"
    destination_addresses = ["0.0.0.0/0", "::/0"]
  }
  outbound_rule {
    protocol              = "icmp"
    destination_addresses = ["0.0.0.0/0", "::/0"]
  }
}
