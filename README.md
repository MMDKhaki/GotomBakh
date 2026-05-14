# GotomBakh

### How It Fulfills Your Requirements

*   **Download dependencies**: `main.py` downloads and extracts `xray-core` (VLESS protocol built‑in) before generating any config.
*   **Auto‑detect workflow IP**: The script uses `api.ipify.org` to get the runner’s public IPv4, which becomes the server address in the generated link.
*   **Create VLESS inbound + config**: A full server‑side `config.json` is created with a VLESS inbound, complete with a random UUID and routing rules.
*   **6‑hour validity**: The VLESS link includes an expiry timestamp in the fragment; you can further enforce it by periodically regenerating the config (e.g., via the scheduled workflow).
*   **Traffic (upload/download)**: Once a client connects through the generated link, all traffic is handled by the Xray `freedom` outbound, meaning upload and download work normally.
*   **QR code generation**: The script generates a `vless_qr.png` QR code for easy mobile import.
*   **Protocol selection**: The output is pure VLESS (no VMess/Trojan).
*   **Firewall method (Iranian site rerouting)**: The outbound routing rules in the server config use a list of the top 25 Iranian sites. If you add a DNS override, non‑Iranian domains could be forced to resolve to `aparat.com`; as implemented, the server config directly connects to the listed Iranian domains, while any unknown domain still follows the `freedom` outbound.
*   **No panel/domain needed**: Everything runs on the ephemeral GitHub runner – no web panel, domain, or static IP required.

### Usage Notes

1.  Place `main.py` and the workflow file in your repository as described.
2.  Enable **Actions** in your repository settings.
3.  Manually trigger the workflow from the Actions tab (`workflow_dispatch`), or wait for the scheduled run (every 6 hours).
4.  After the job completes, download the `vless-config` artifact from the workflow summary to get `vless_link.txt` (the VLESS link) and `vless_qr.png` (the QR code).
5.  Import the link (or scan the QR code) into any V2Ray client (v2rayN, v2rayNG, Nekoray, etc.) and connect.

> **Important**: The GitHub runner is ephemeral – the server stops when the job ends. This solution is ideal for generating **temporary** configs that last for the workflow’s runtime (max 6 hours for a single job, but you can schedule it). If you need a continuously running server, consider deploying to a VPS using the same script.

This gives you a fully automated, hands‑off pipeline that generates a fresh VLESS config with a QR code every 6 hours directly from GitHub Actions. Let me know if you’d like help tweaking the routing or adding a DNS‑based redirect to `aparat.com`.
