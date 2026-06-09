output "ipv4" {
  description = "Public IPv4 of the droplet."
  value       = digitalocean_droplet.ec.ipv4_address
}

output "ssh" {
  description = "SSH command (login as the unprivileged cognee user)."
  value       = "ssh cognee@${digitalocean_droplet.ec.ipv4_address}"
}

output "run_sla_suite" {
  description = "One-liner to run the SLA + soak suite once cloud-init finishes (~3-4 min)."
  value       = "ssh cognee@${digitalocean_droplet.ec.ipv4_address} 'sudo -u cognee /opt/enhanced-cognee/tests/load/run_perf_suite.sh both'"
}

output "droplet_size" {
  description = "Provisioned droplet size."
  value       = digitalocean_droplet.ec.size_slug
}
