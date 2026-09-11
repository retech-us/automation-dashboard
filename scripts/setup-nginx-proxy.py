#!/usr/bin/env python3
"""
Automated Nginx configuration updater for Intelligent Reset Runner on EC2.
Ensures /api/ routes are reverse-proxied to runner_server.py on http://127.0.0.1:8085.
"""

import os
import sys
import subprocess
from pathlib import Path

PROXY_BLOCK = """
    # Forward /api/ calls to Python runner_server on port 8085
    location /api/ {
        proxy_pass http://127.0.0.1:8085;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 300s;
        proxy_connect_timeout 300s;
    }
"""

def find_target_conf() -> Path:
    # Check conf.d first
    conf_d = Path("/etc/nginx/conf.d")
    if conf_d.is_dir():
        confs = list(conf_d.glob("*.conf"))
        if confs:
            return confs[0]

    # Check sites-available / sites-enabled
    sites_enabled = Path("/etc/nginx/sites-enabled")
    if sites_enabled.is_dir():
        confs = list(sites_enabled.glob("*"))
        if confs:
            return confs[0]

    # Default to /etc/nginx/nginx.conf
    return Path("/etc/nginx/nginx.conf")


def configure_nginx():
    conf_path = find_target_conf()
    print(f"🔍 Inspecting Nginx config at: {conf_path}")

    if not conf_path.exists():
        print(f"❌ Configuration file {conf_path} not found.")
        sys.exit(1)

    content = conf_path.read_text(encoding="utf-8")

    if "proxy_pass http://127.0.0.1:8085" in content or "proxy_pass http://localhost:8085" in content:
        print("✅ Nginx already configured to proxy /api/ to port 8085!")
    else:
        # Look for location / or server { to insert the proxy block
        if "location /" in content:
            # Insert before location / or after location /
            loc_idx = content.find("location /")
            # Find the closing brace of location /
            brace_idx = content.find("}", loc_idx)
            if brace_idx != -1:
                new_content = content[:brace_idx + 1] + "\n" + PROXY_BLOCK + content[brace_idx + 1:]
            else:
                new_content = content.replace("server {", "server {\n" + PROXY_BLOCK, 1)
        elif "server {" in content:
            new_content = content.replace("server {", "server {\n" + PROXY_BLOCK, 1)
        else:
            print("⚠️ Could not find a server block in " + str(conf_path))
            print("Creating dedicated /etc/nginx/conf.d/runner-proxy.conf...")
            proxy_conf = Path("/etc/nginx/conf.d/runner-proxy.conf")
            proxy_conf.write_text(f"server {{\n    listen 80;\n    server_name _;\n    root /var/www/automation-dashboard;\n{PROXY_BLOCK}\n}}\n")
            new_content = None

        if new_content:
            # Backup original
            backup_path = conf_path.with_suffix(conf_path.suffix + ".bak")
            backup_path.write_text(content, encoding="utf-8")
            print(f"📦 Backup created at: {backup_path}")

            conf_path.write_text(new_content, encoding="utf-8")
            print(f"✅ Added /api/ proxy block to {conf_path}")

    # Test nginx configuration
    res = subprocess.run(["nginx", "-t"], capture_output=True, text=True)
    if res.returncode == 0:
        print("✅ Nginx syntax test PASSED.")
        subprocess.run(["systemctl", "reload", "nginx"], check=True)
        print("🚀 Nginx reloaded successfully!")
    else:
        print(f"❌ Nginx syntax test failed:\n{res.stderr}")
        sys.exit(1)


if __name__ == "__main__":
    if os.geteuid() != 0:
        print("⚠️ This script must be run with sudo privileges:")
        print("   sudo python3 scripts/setup-nginx-proxy.py")
        sys.exit(1)
    configure_nginx()
