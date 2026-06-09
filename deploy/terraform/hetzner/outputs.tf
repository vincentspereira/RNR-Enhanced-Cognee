output "ipv4" {
  description = "Public IPv4 of the host."
  value       = hcloud_server.ec.ipv4_address
}

output "ipv6" {
  description = "Public IPv6 of the host."
  value       = hcloud_server.ec.ipv6_address
}

output "ssh" {
  description = "SSH command (login as the unprivileged cognee user)."
  value       = "ssh cognee@${hcloud_server.ec.ipv4_address}"
}

output "run_sla_suite" {
  description = "One-liner to run the SLA + soak suite once cloud-init finishes (~3-4 min)."
  value       = "ssh cognee@${hcloud_server.ec.ipv4_address} 'sudo -u cognee /opt/enhanced-cognee/tests/load/run_perf_suite.sh both'"
}

output "server_type" {
  description = "Provisioned server type."
  value       = hcloud_server.ec.server_type
}
