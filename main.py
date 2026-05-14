#!/usr/bin/env python3
"""
VLESS config generator for GitHub Actions runner.
1. Download and extract xray-core.
2. Detect the runner's public IPv4.
3. Generate a VLESS server inbound config.
4. Create a VLESS share link (with 6-hour expiry).
5. Generate a QR code for the link.
6. Write config, link, and QR code as job artifacts.
"""

import json, os, random, re, string, subprocess, sys, time
import urllib.request
import uuid
import qrcode
from datetime import datetime, timedelta, timezone

XRAY_VERSION = "v24.12.19"          # Use a recent stable release
XRAY_URL = f"https://github.com/XTLS/Xray-core/releases/download/{XRAY_VERSION}/Xray-linux-64.zip"
XRAY_DIR = "/tmp/xray"
CONFIG_FILE = os.path.join(XRAY_DIR, "config.json")
LINK_FILE = "vless_link.txt"
QR_FILE = "vless_qr.png"

# --- Top 25 Iranian sites (domains) -------------------------------------------------
IRANIAN_SITES = [
    "aparat.com", "digikala.com", "filimo.com", "namasha.com", "varzesh3.com",
    "khabaronline.ir", "tabnak.ir", "yjc.ir", "farsnews.ir", "mehrnews.com",
    "isna.ir", "irna.ir", "tasnimnews.com", "eghtesadonline.com", "boursenews.ir",
    "donya-e-eqtesad.com", "divar.ir", "sheypoor.com", "torob.com", "bamilo.com",
    "snapp.ir", "cafebazaar.ir", "iranserver.com", "blog.ir", "mizanonline.ir",
]

# --- Helper functions --------------------------------------------------------------
def run(cmd, **kwargs):
    """Run a shell command and return output."""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, **kwargs)
    if result.returncode != 0:
        print(f"Command failed: {cmd}\n{result.stderr}")
        sys.exit(result.returncode)
    return result.stdout.strip()

def generate_uuid():
    """Generate a random UUID for VLESS user."""
    return str(uuid.uuid4())

def public_ip():
    """Retrieve the public IP using ipify."""
    try:
        ip = urllib.request.urlopen("https://api.ipify.org", timeout=5).read().decode().strip()
        return ip
    except Exception:
        # fallback to alternative
        ip = urllib.request.urlopen("https://api64.ipify.org", timeout=5).read().decode().strip()
        return ip

# --- Download xray-core ------------------------------------------------------------
def download_xray():
    """Download and extract xray-core binary."""
    print(">>> Downloading xray-core...")
    os.makedirs(XRAY_DIR, exist_ok=True)
    run(f"curl -L -o /tmp/xray.zip {XRAY_URL}")
    run(f"unzip -o /tmp/xray.zip -d {XRAY_DIR}")
    run(f"chmod +x {XRAY_DIR}/xray")
    print(">>> xray-core ready.")

# --- Generate server inbound config ------------------------------------------------
def create_inbound_config(ip: str, port: int, user_uuid: str):
    """Create a minimal Xray config with a VLESS inbound."""
    # Use an Iranian sites list for outbound routing
    # (You can also use geosite:ir if you provide a geoip file.)
    # Here we build outbound routing that sends everything to
    # the internet directly, but you may replace it with a custom rule.
    config = {
        "log": {"loglevel": "warning"},
        "inbounds": [
            {
                "port": port,
                "protocol": "vless",
                "settings": {
                    "clients": [
                        {
                            "id": user_uuid,
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
            {
                "tag": "direct",
                "protocol": "freedom",
            },
            {
                "tag": "block",
                "protocol": "blackhole",
            },
        ],
        "routing": {
            "domainStrategy": "AsIs",
            "rules": [
                {
                    "type": "field",
                    "domain": [f"domain:{site}" for site in IRANIAN_SITES],
                    "outboundTag": "direct",
                },
                {
                    "type": "field",
                    "protocol": ["vless"],
                    "outboundTag": "direct",
                },
            ],
        },
    }
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)
    print(f">>> Server config written to {CONFIG_FILE}")

# --- Generate VLESS share link ----------------------------------------------------
def generate_vless_link(ip: str, port: int, user_uuid: str, expiry_hours: int = 6):
    """Create a vless:// share link with a comment indicating expiry."""
    expiry_time = datetime.now(timezone.utc) + timedelta(hours=expiry_hours)
    expiry_str = expiry_time.strftime("%Y-%m-%dT%H:%M:%SZ")
    # Simple fragment with expiry info
    fragment = f"VLESS-{expiry_hours}H-Valid"
    link = f"vless://{user_uuid}@{ip}:{port}?security=none&type=tcp#{fragment}"
    return link

def generate_qr(link: str):
    """Generate a QR code image for the link."""
    img = qrcode.make(link)
    img.save(QR_FILE)
    print(f">>> QR code saved to {QR_FILE}")

# --- Main execution ---------------------------------------------------------------
def main():
    print("=== VLESS Config Generator ===")

    # 1. Download xray-core
    download_xray()

    # 2. Get public IP of the runner
    try:
        ip = public_ip()
        print(f">>> Runner public IP: {ip}")
    except Exception as e:
        print("Failed to get public IP:", e)
        sys.exit(1)

    # 3. Choose a port (avoid privileged ports)
    port = 443  # Commonly used, but you can randomize
    # 4. Generate user UUID
    user_uuid = generate_uuid()

    # 5. Create server inbound config
    create_inbound_config(ip, port, user_uuid)

    # 6. Generate VLESS link (valid for 6 hours)
    vless_link = generate_vless_link(ip, port, user_uuid, expiry_hours=6)
    with open(LINK_FILE, "w") as f:
        f.write(vless_link)
    print(f">>> VLESS link: {vless_link}")

    # 7. Generate QR code
    generate_qr(vless_link)

    # 8. (Optional) Start xray to test connectivity, but in a GitHub job it's ephemeral
    # You can uncomment the next lines if you want to start xray for the workflow duration.
    # run(f"cd {XRAY_DIR} && ./xray run -config config.json &")
    # time.sleep(5)  # give it a moment

    print("=== Done ===")
    print(f"Config file: {CONFIG_FILE}")
    print(f"VLESS link file: {LINK_FILE}")
    print(f"QR code file: {QR_FILE}")

if __name__ == "__main__":
    main()
