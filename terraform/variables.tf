variable "tenancy_ocid" {
  description = "Your Oracle Cloud tenancy OCID"
  type        = string
}

variable "user_ocid" {
  description = "Your Oracle Cloud user OCID"
  type        = string
}

variable "fingerprint" {
  description = "API key fingerprint (Identity > Users > API Keys)"
  type        = string
}

variable "private_key_path" {
  description = "Path to the OCI API private key PEM"
  type        = string
}

variable "region" {
  description = "OCI region (e.g. me-jeddah-1, me-dubai-1, us-ashburn-1)"
  type        = string
  default     = "me-jeddah-1"
}

variable "compartment_ocid" {
  description = "Compartment OCID to deploy into (root tenancy is fine for free tier)"
  type        = string
}

variable "ssh_public_key_path" {
  description = "Path to the SSH public key to install on the VM"
  type        = string
  default     = "~/.ssh/oracle_rwtd.pub"
}

variable "allowed_ssh_cidr" {
  description = "CIDR allowed to SSH. Use your IP/32 for safety, 0.0.0.0/0 if you accept the risk."
  type        = string
  default     = "0.0.0.0/0"
}

variable "allowed_healthcheck_cidr" {
  description = "CIDR allowed to hit the healthcheck endpoint"
  type        = string
  default     = "0.0.0.0/0"
}

variable "target_ad" {
  description = "Pin to a specific AD name once you've found capacity. Leave empty to try all ADs."
  type        = string
  default     = ""
}

variable "git_repo_url" {
  description = "HTTPS clone URL for the rwtd-cloud-bot repo"
  type        = string
  default     = "https://github.com/YOUR-USERNAME/rwtd-cloud-bot.git"
}
