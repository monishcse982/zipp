#!/usr/bin/env bash

set -euo pipefail

if [[ $EUID -ne 0 ]]; then
  echo "Run this installer with sudo." >&2
  exit 1
fi

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
service_name=zipp-port-forwards.service
service_file="$repo_root/deploy/systemd/$service_name"
forward_script="$repo_root/scripts/port-forward-all.sh"

systemctl stop "$service_name" 2>/dev/null || true

occupied_ports=()
for port in 8080 5173 3000 9090 5433 6380; do
  if ss -H -ltn "sport = :$port" | grep --quiet .; then
    occupied_ports+=("$port")
  fi
done

if (( ${#occupied_ports[@]} > 0 )); then
  echo "Cannot install: localhost ports are already in use: ${occupied_ports[*]}" >&2
  echo "Stop any manually running make port-forward-all process and retry." >&2
  exit 1
fi

install -o root -g root -m 0755 \
  "$forward_script" /usr/local/bin/zipp-port-forward-all
install -o root -g root -m 0644 \
  "$service_file" "/etc/systemd/system/$service_name"

systemctl daemon-reload
systemctl enable "$service_name"
systemctl restart "$service_name"

wait_for_endpoint() {
  local name=$1
  local url=$2

  for _ in {1..12}; do
    if curl --fail --silent --show-error --max-time 5 "$url" >/dev/null; then
      echo "$name port-forward is healthy."
      return
    fi
    sleep 5
  done

  echo "$name port-forward did not become healthy: $url" >&2
  systemctl status "$service_name" --no-pager >&2 || true
  journalctl --unit "$service_name" --lines 50 --no-pager >&2 || true
  exit 1
}

wait_for_endpoint "Application" "http://127.0.0.1:8080/health/live"
wait_for_endpoint "Grafana" "http://127.0.0.1:3000/api/health"

echo "Installed and started $service_name."
echo "Status: sudo systemctl status $service_name"
echo "Logs:   sudo journalctl -u $service_name -f"
