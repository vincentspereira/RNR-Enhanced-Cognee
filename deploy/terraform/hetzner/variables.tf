variable "hcloud_token" {
  description = "Hetzner Cloud API token (Project -> Security -> API Tokens, read/write)."
  type        = string
  sensitive   = true
}

variable "ssh_public_key" {
  description = "SSH public key contents (e.g. file(\"~/.ssh/id_ed25519.pub\"))."
  type        = string
}

variable "name" {
  description = "Server + resource name prefix."
  type        = string
  default     = "enhanced-cognee-sla"
}

variable "server_type" {
  description = <<-EOT
    Hetzner server type. Defaults to a dedicated-vCPU box for reproducible
    SLA numbers. Options:
      ccx13  2 dedicated vCPU / 8 GB   (on-box load-gen tight but workable)
      ccx23  4 dedicated vCPU / 16 GB  (recommended: stack + on-box locust)
      ccx33  8 dedicated vCPU / 32 GB  (headroom; off-box load-gen)
      cx22   2 shared vCPU / 4 GB      (cheap serving box; NOT for measuring)
  EOT
  type    = string
  default = "ccx23"
}

variable "location" {
  description = "Hetzner location: fsn1 (Falkenstein), nbg1 (Nuremberg), hel1 (Helsinki), ash (Ashburn US), hil (Hillsboro US)."
  type        = string
  default     = "fsn1"
}

variable "ssh_allowed_cidrs" {
  description = "CIDRs allowed to SSH in. Lock to your IP for a test host."
  type        = list(string)
  default     = ["0.0.0.0/0", "::/0"]
}

variable "app_port_allowed_cidrs" {
  description = "CIDRs allowed to reach app port 8080 directly (for OFF-box load generation). Empty = app stays internal, load-gen runs on-box."
  type        = list(string)
  default     = []
}

variable "repo_url" {
  description = "Git URL to clone Enhanced Cognee from."
  type        = string
  default     = "https://github.com/vincentspereira/Enhanced-Cognee.git"
}

variable "repo_ref" {
  description = "Git branch/tag/ref to deploy."
  type        = string
  default     = "main"
}

variable "enhanced_api_key" {
  description = "Optional ENHANCED_API_KEY. Leave empty to auto-generate one on the box (saved to /root/enhanced-cognee-api-key.txt)."
  type        = string
  default     = ""
  sensitive   = true
}
