#!/bin/bash
# Installs Docker Engine + Compose plugin on Debian, Ubuntu, or RHEL-family
# (RHEL/CentOS/Rocky/AlmaLinux/Fedora) hosts, using each vendor's official repo.
set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
    echo "Run as root (sudo $0)."
    exit 1
fi

if [ ! -r /etc/os-release ]; then
    echo "Cannot detect OS: /etc/os-release not found."
    exit 1
fi
# shellcheck disable=SC1091
. /etc/os-release
ID_LIKE="${ID_LIKE:-}"

install_debian_family() {
    echo "==> Installing Docker on $PRETTY_NAME (apt)..."
    apt-get update
    apt-get install -y ca-certificates curl gnupg

    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL "https://download.docker.com/linux/${ID}/gpg" -o /etc/apt/keyrings/docker.asc
    chmod a+r /etc/apt/keyrings/docker.asc

    echo \
        "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/${ID} \
        $(. /etc/os-release && echo "${VERSION_CODENAME}") stable" \
        > /etc/apt/sources.list.d/docker.list

    apt-get update
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
}

install_rhel_family() {
    echo "==> Installing Docker on $PRETTY_NAME (dnf/yum)..."
    PKG_MGR=dnf
    command -v dnf >/dev/null 2>&1 || PKG_MGR=yum

    "$PKG_MGR" -y install dnf-plugins-core 2>/dev/null || "$PKG_MGR" install -y yum-utils

    REPO_ID="$ID"
    case "$ID" in
        rocky|almalinux|centos) REPO_ID=centos ;;
        rhel) REPO_ID=rhel ;;
        fedora) REPO_ID=fedora ;;
    esac

    if [ "$PKG_MGR" = "dnf" ]; then
        dnf config-manager --add-repo "https://download.docker.com/linux/${REPO_ID}/docker-ce.repo"
    else
        yum-config-manager --add-repo "https://download.docker.com/linux/${REPO_ID}/docker-ce.repo"
    fi

    "$PKG_MGR" -y install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
}

case "$ID" in
    ubuntu|debian)
        install_debian_family
        ;;
    rhel|centos|rocky|almalinux|fedora)
        install_rhel_family
        ;;
    *)
        case "$ID_LIKE" in
            *debian*)
                install_debian_family
                ;;
            *rhel*|*fedora*)
                install_rhel_family
                ;;
            *)
                echo "Unsupported distro: ID=$ID ID_LIKE=$ID_LIKE"
                echo "This script supports Debian, Ubuntu, and RHEL-family (RHEL/CentOS/Rocky/AlmaLinux/Fedora) only."
                exit 1
                ;;
        esac
        ;;
esac

systemctl enable --now docker

REAL_USER="${SUDO_USER:-$USER}"
if [ "$REAL_USER" != "root" ]; then
    usermod -aG docker "$REAL_USER"
    echo "Added $REAL_USER to the docker group — log out/in (or run 'newgrp docker') for it to take effect."
fi

echo "==> Docker installed:"
docker --version
docker compose version
