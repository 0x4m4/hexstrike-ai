#!/usr/bin/env bash
# Allow Cursor cloud agent egress IPs through ufw/fail2ban (run ON VPS as root).
#
#   bash scripts/vps-allow-cursor-cloud-ssh.sh
#   # or: curl -fsSL ... | bash
set -euo pipefail
[[ $(id -u) -eq 0 ]] || { echo "run as root"; exit 1; }

# Refresh these if cloud agent still cannot SSH (curl -4 ifconfig.me from agent).
IPS=(
  "52.40.48.127"
  "44.236.205.197"
  "52.13.17.46"
  "54.201.20.43"
)

for ip in "${IPS[@]}"; do
  if command -v ufw >/dev/null 2>&1 && ufw status 2>/dev/null | grep -qi active; then
    ufw allow from "$ip" to any port 22 proto tcp comment "cursor-cloud-agent" || true
    echo "ufw allow $ip:22"
  fi
  if command -v fail2ban-client >/dev/null 2>&1; then
    fail2ban-client set sshd unbanip "$ip" 2>/dev/null || true
    fail2ban-client set ssh unbanip "$ip" 2>/dev/null || true
    echo "fail2ban unban $ip (if was banned)"
  fi
  # hosts.allow soft allow (if tcpwrappers in use)
  if [[ -f /etc/hosts.allow ]]; then
    grep -q "sshd: $ip" /etc/hosts.allow 2>/dev/null || echo "sshd: $ip  # cursor-cloud" >>/etc/hosts.allow
  fi
done

# Drop any iptables DROP for these sources on dport 22 (best-effort)
if command -v iptables >/dev/null 2>&1; then
  for ip in "${IPS[@]}"; do
    iptables -C INPUT -p tcp -s "$ip" --dport 22 -j ACCEPT 2>/dev/null \
      || iptables -I INPUT 1 -p tcp -s "$ip" --dport 22 -j ACCEPT
    echo "iptables ACCEPT $ip:22"
  done
fi

echo "DONE — ask cloud agent to retry: ssh root@$(hostname -I | awk '{print $1}')"
sshd -t 2>/dev/null && systemctl reload sshd 2>/dev/null || systemctl reload ssh 2>/dev/null || true
