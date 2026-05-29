# Oracle Cloud Free Tier — Always Free Ampere ARM VM for redroid + bot.
#
# This provisions:
#   - 1x VM.Standard.A1.Flex (4 OCPU, 24 GB RAM)
#   - Ubuntu 22.04 ARM image
#   - VCN with public subnet
#   - Security list opening 22 (SSH) and 8080 (healthcheck)
#
# NOTE on capacity: Oracle's Always Free ARM shapes are heavily in demand.
# `terraform apply` may return "Out of host capacity". Re-run periodically;
# you may wait hours or days. Once allocated, the VM is yours.

terraform {
  required_version = ">= 1.5"
  required_providers {
    oci = {
      source  = "oracle/oci"
      version = ">= 5.0"
    }
  }
}

provider "oci" {
  tenancy_ocid     = var.tenancy_ocid
  user_ocid        = var.user_ocid
  fingerprint      = var.fingerprint
  private_key_path = var.private_key_path
  region           = var.region
}

# --- Networking ---

resource "oci_core_vcn" "vcn" {
  compartment_id = var.compartment_ocid
  cidr_blocks    = ["10.0.0.0/16"]
  display_name   = "rwtd-vcn"
  dns_label      = "rwtdvcn"
}

resource "oci_core_internet_gateway" "igw" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.vcn.id
  display_name   = "rwtd-igw"
}

resource "oci_core_route_table" "rt" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.vcn.id
  display_name   = "rwtd-rt"
  route_rules {
    destination       = "0.0.0.0/0"
    destination_type  = "CIDR_BLOCK"
    network_entity_id = oci_core_internet_gateway.igw.id
  }
}

resource "oci_core_security_list" "sl" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.vcn.id
  display_name   = "rwtd-sl"

  egress_security_rules {
    destination = "0.0.0.0/0"
    protocol    = "all"
  }

  # SSH - restrict to your IP via var.allowed_ssh_cidr if you want extra safety
  ingress_security_rules {
    protocol = "6" # TCP
    source   = var.allowed_ssh_cidr
    tcp_options {
      min = 22
      max = 22
    }
  }

  # Healthcheck endpoint
  ingress_security_rules {
    protocol = "6"
    source   = var.allowed_healthcheck_cidr
    tcp_options {
      min = 8080
      max = 8080
    }
  }
}

resource "oci_core_subnet" "subnet" {
  compartment_id    = var.compartment_ocid
  vcn_id            = oci_core_vcn.vcn.id
  cidr_block        = "10.0.1.0/24"
  display_name      = "rwtd-subnet"
  dns_label         = "rwtdsub"
  route_table_id    = oci_core_route_table.rt.id
  security_list_ids = [oci_core_security_list.sl.id]
}

# --- Compute ---

data "oci_identity_availability_domains" "ads" {
  compartment_id = var.tenancy_ocid
}

locals {
  ad_names = [for ad in data.oci_identity_availability_domains.ads.availability_domains : ad.name]

  cloud_init = <<-CLOUD_INIT
    #!/usr/bin/env bash
    set -euxo pipefail

    # --- Install Docker from Docker's official APT repo ---
    # Ubuntu's docker.io package lacks the modern `docker compose` plugin,
    # and `docker-compose-plugin` only exists in Docker's repo, not Ubuntu's.
    apt-get update
    apt-get install -y ca-certificates curl gnupg git
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
      | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    chmod a+r /etc/apt/keyrings/docker.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" \
      > /etc/apt/sources.list.d/docker.list
    apt-get update
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

    # --- Kernel modules for redroid ---
    apt-get install -y linux-modules-extra-$(uname -r) || true
    modprobe binder_linux devices="binder,hwbinder,vndbinder" || true
    modprobe ashmem_linux || true

    echo binder_linux > /etc/modules-load.d/redroid.conf
    echo ashmem_linux >> /etc/modules-load.d/redroid.conf
    echo 'options binder_linux devices=binder,hwbinder,vndbinder' > /etc/modprobe.d/redroid.conf

    # --- Firewall: healthcheck only, NOT ADB ---
    iptables -I INPUT -p tcp --dport 8080 -j ACCEPT || true

    # --- Clone repo + scaffold .env ---
    sudo -u ubuntu git clone ${var.git_repo_url} /home/ubuntu/rwtd-cloud-bot || true
    cd /home/ubuntu/rwtd-cloud-bot
    [ -f .env ] || cp .env.example .env

    # --- Give ubuntu user docker access ---
    usermod -aG docker ubuntu

    # --- Keep-alive cron to prevent Oracle from reclaiming the VM ---
    echo "*/30 * * * * /usr/bin/head -c 1M /dev/zero | /usr/bin/md5sum > /dev/null" \
      | crontab -u ubuntu -

    # --- NOTE: We intentionally do NOT auto-start the docker stack. ---
    # First-boot of redroid + kernel modules has wedged VMs in the past.
    # SSH in and run `cd ~/rwtd-cloud-bot && docker compose -f docker/docker-compose.yml up -d`
    # with eyes on the logs. See docs/oracle-setup.md.
  CLOUD_INIT
}

data "oci_core_images" "ubuntu" {
  compartment_id           = var.compartment_ocid
  operating_system         = "Canonical Ubuntu"
  operating_system_version = "22.04"
  shape                    = "VM.Standard.A1.Flex"
  sort_by                  = "TIMECREATED"
  sort_order               = "DESC"
}

# Try every AD in the region. Oracle Free Tier ARM capacity is scarce —
# most ADs will fail with "Out of host capacity". Terraform will create
# whichever one(s) succeed. After first success, remove the others or
# set var.target_ad to pin to the working AD.
resource "oci_core_instance" "vm" {
  for_each = var.target_ad != "" ? toset([var.target_ad]) : toset(local.ad_names)

  availability_domain = each.value
  compartment_id      = var.compartment_ocid
  display_name        = "rwtd-bot-${each.key}"
  shape               = "VM.Standard.A1.Flex"

  shape_config {
    ocpus         = 4
    memory_in_gbs = 24
  }

  create_vnic_details {
    subnet_id        = oci_core_subnet.subnet.id
    assign_public_ip = true
  }

  source_details {
    source_id   = data.oci_core_images.ubuntu.images[0].id
    source_type = "image"
    boot_volume_size_in_gbs = 100
  }

  metadata = {
    ssh_authorized_keys = file(var.ssh_public_key_path)
    user_data           = base64encode(local.cloud_init)
  }
}

output "vm_public_ips" {
  value = { for k, v in oci_core_instance.vm : k => v.public_ip }
}
