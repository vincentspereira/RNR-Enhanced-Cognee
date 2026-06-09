variable "do_token" {
  description = "DigitalOcean API token (API -> Tokens, write scope)."
  type        = string
  sensitive   = true
}

variable "ssh_public_key" {
  description = "SSH public key contents (e.g. file(\"~/.ssh/id_ed25519.pub\"))."
  type        = string
}

variable "name" {
  description = "Droplet + resource name prefix."
  type        = string
  default     = "enhanced-cognee-sla"
}

variable "droplet_size" {
  description = <<-EOT
    DigitalOcean droplet size slug. Defaults to CPU-Optimized (dedicated vCPU)
    for reproducible SLA numbers. Options:
      c-4              4 dedicated vCPU / 8 GB   (recommended)
      c-8              8 dedicated vCPU / 16 GB  (headroom / off-box load-gen)
      g-4vcpu-16gb     4 dedicated vCPU / 16 GB  (more RAM headroom)
      s-2vcpu-4gb      2 shared vCPU / 4 GB      (cheap serving box; NOT for measuring)
  EOT
  type    = string
  default = "c-4"
}

variable "region" {
  description = "DO region: fra1 (Frankfurt), ams3 (Amsterdam), nyc3 (New York), sfo3 (San Francisco), sgp1 (Singapore)."
  type        = string
  default     = "fra1"
}

variable "ssh_allowed_cidrs" {
  description = "CIDRs allowed to SSH in. Lock to your IP for a test host."
  type        = list(string)
  default     = ["0.0.0.0/0", "::/0"]
}

variable "app_port_allowed_cidrs" {
  description = "CIDRs allowed to reach app port 8080 directly (OFF-box load generation). Empty = app internal, load-gen on-box."
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
