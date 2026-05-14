#!/usr/bin/env python3
"""
Download Xray-core, detect runner IP, generate a VLESS inbound config
with a 6‑hour valid user, and build a QR code.
The server uses fakedns to resolve every non‑Iranian domain to apat.com’s IP.
"""

import json
import os
import socket
import sys
import urllib.request
import uuid
import zipfile
from datetime import datetime, timedelta, timezone

import qrcode

# ----------------------------------------------------------------------
# Configuration
XRAY_VERSION = "v24.12.19"
XRAY_URL = f"https://github.com/XTLS/Xray-core/releases/download/{XRAY_VERSION}/Xray-linux-64.zip"
XRAY_DIR = "/tmp/xray"
SERVER_CONFIG = os.path.join(XRAY_DIR, "config.json")
LINK_FILE = "vless_link.txt"
QR_FILE = "vless_qr.png"

# Top 25 Iranian sites (used to bypass the firewall for domestic traffic)
IRANIAN_SITES = [
    "aparat.com", "digikala.com", "filimo.com", "namasha.com", "varzesh3.com",
    "khabaronline.ir", "tabnak.ir", "yjc.ir", "farsnews.ir", "mehrnews.com",
    "isna.ir", "irna.ir", "tasnimnews.com", "eghtesadonline.com", "boursenews.ir",
    "donya-e-eqtesad.com", "divar.ir", "sheypoor.com", "torob.com", "bamilo.com",
    "snapp.ir", "cafebazaar.ir", "iranserver.com", "blog.ir", "mizanonline.ir",
]

# ----------------------------------------------------------------------
def download_xray():
    """Download and extract Xray-core using only Python stdlib."""
    print(">>> Downloading xray-core ...")
    os.makedirs(XRAY_DIR, exist_ok=True)
    zip_path = "/tmp/xray.zip"
    urllib.request.urlretrieve(XRAY_URL, zip_path)
    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(XRAY_DIR)
    # Make the binary executable
    os.chmod(os.path.join(XRAY_DIR, "xray"), 0o755)
    print(">>> xray-core ready.")

def public_ipv4():
    """Return the runner's public IPv4 address."""
    for url in ("https://api.ipify.org", "https://api64.ipify.org"):
        try:
            with urllib.request.urlopen(url, timeout=5) as r:
                return r.read().decode().strip()
        except Exception:
            continue
    raise RuntimeError("Failed to obtain public IP")

def get_aparat_ip():
    """Resolve aparat.com to an IPv4 address."""
    return socket.gethostbyname("aparat.com")

def generate_user():
    return str(uuid.uuid4())

def create_server_config(ip: str, port: int, user_id: str, aparat_ip: str):
    """
    Write a full Xray server config with a VLESS inbound and a DNS section
    that redirects all non‑Iranian domains to aparat.com.
    """
    # Build the list of "domain:" rules for the Iranian sites
    ir_domain_rules = [f"domain:{site}" for site in IRANIAN_SITES]

    config = {
        "log": {"loglevel": "warning"},
        "inbounds": [
            {
                "port": port,
                "protocol": "vless",
                "settings": {
                    "clients": [
                        {
                            "id": user_id,
                            "level": 0,
                            "email": "user@vless.auto",
                        }
                    ],
                    "decryption": "none",
                },
                "streamSettings": {
                    "network": "tcp",
                    "security": "none",
                },
                "tag": "vless-in",
            }
        ],
        "outbounds": [
            {"tag": "direct", "protocol": "freedom"},
            {"tag": "block", "protocol": "blackhole"},
        ],
        "routing": {
            "domainStrategy": "AsIs",
            "rules": [
                # Allow Iranian sites directly
                {
                    "type": "field",
                    "domain": ir_domain_rules,
                    "outboundTag": "direct",
                },
                # Ensure inbound VLESS traffic can leave
                {
                    "type": "field",
                    "protocol": ["vless"],
                    "outboundTag": "direct",
                },
            ],
        },
        "dns": {
            "servers": [
                {
                    "address": "8.8.8.8",          # Normal DNS for Iranian sites
                    "domains": ir_domain_rules,
                },
                {
                    "address": "fakedns",          # Everything else → aparat.com
                },
            ],
            "fakedns": {
                "ipPool": [f"{aparat_ip}/32"],
                "poolSize": 1,
            },
        },
    }

    with open(SERVER_CONFIG, "w") as f:
        json.dump(config, f, indent=2)
    print(f">>> Server config written to {SERVER_CONFIG}")

def generate_vless_link(ip: str, port: int, user_id: str, valid_hours: int = 6):
    """Return a vless:// share link with an expiry timestamp in the fragment."""
    expiry = (datetime.now(timezone.utc) + timedelta(hours=valid_hours)).strftime("%Y-%m-%dT%H:%M:%SZ")
    fragment = f"IR-VPN-{valid_hours}H-valid"
    return f"vless://{user_id}@{ip}:{port}?security=none&type=tcp#{fragment}"

def generate_qr(link: str, filepath: str):
    img = qrcode.make(link)
    img.save(filepath)
    print(f">>> QR code saved to {filepath}")

# ----------------------------------------------------------------------
def main():
    print("=== VLESS Config Generator (with aparat.com redirect) ===")

    # 1. Prepare Xray
    download_xray()

    # 2. Gather runtime info
    server_ip = public_ipv4()
    print(f">>> Runner public IP: {server_ip}")
    aparat_ip = get_aparat_ip()
    print(f">>> aparat.com resolved to: {aparat_ip}")

    # 3. User and port
    user_uuid = generate_user()
    vless_port = 443      # typical VLESS port

    # 4. Server config (with DNS redirection)
    create_server_config(server_ip, vless_port, user_uuid, aparat_ip)

    # 5. VLESS link & QR
    link = generate_vless_link(server_ip, vless_port, user_uuid, valid_hours=6)
    with open(LINK_FILE, "w") as f:
        f.write(link)
    print(f">>> VLESS link: {link}")
    generate_qr(link, QR_FILE)

    print("\n=== Done ===")
    print("Artifacts: server config.json, vless_link.txt, vless_qr.png")

if __name__ == "__main__":
    main()
