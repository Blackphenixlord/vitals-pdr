#!/usr/bin/env bash
# =============================================================================
#  demo-link.sh - wire ONE Jetson and ONE Pi together with a single Ethernet
#  cable, no router, no internet. Fixed addresses, so it works the same at home
#  and at the PDR table.
#
#     on the Jetson:   sudo ./deploy/demo-link.sh jetson     -> 10.42.0.1
#     on the Pi:       sudo ./deploy/demo-link.sh pi         -> 10.42.0.2
#
#  Uses NetworkManager (JetPack 6 and Raspberry Pi OS Bookworm both have it).
#  Only the WIRED port is changed; Wi-Fi is left alone, so the boards can still
#  reach the internet over Wi-Fi at home while the cable link is up.
#  Undo:  sudo nmcli connection delete vitals-link
# =============================================================================
set -euo pipefail
ROLE="${1:-}"
case "$ROLE" in
  jetson) ADDR=10.42.0.1 ;;
  pi)     ADDR=10.42.0.2 ;;
  *) echo "usage: sudo $0 jetson|pi"; exit 1 ;;
esac
[ "$(id -u)" = 0 ] || { echo "run with sudo"; exit 1; }
command -v nmcli >/dev/null || { echo "NetworkManager (nmcli) not found"; exit 1; }

IFACE="$(nmcli -t -f DEVICE,TYPE device | awk -F: '$2=="ethernet"{print $1; exit}')"
[ -n "$IFACE" ] || { echo "no wired Ethernet port found (nmcli device)"; exit 1; }

nmcli connection delete vitals-link >/dev/null 2>&1 || true
nmcli connection add type ethernet ifname "$IFACE" con-name vitals-link \
    ipv4.method manual ipv4.addresses "$ADDR/24" ipv4.never-default yes \
    ipv6.method ignore connection.autoconnect yes connection.autoconnect-priority 100 >/dev/null
nmcli connection up vitals-link >/dev/null 2>&1 || echo "  (cable not plugged in yet - it will come up when it is)"

echo "ok  $ROLE is $ADDR on $IFACE (cable link only; Wi-Fi untouched)"
if [ "$ROLE" = pi ]; then
  echo "    test:  ping -c 3 10.42.0.1      then open  http://10.42.0.1:8000"
else
  echo "    test from the Pi:  ping -c 3 10.42.0.1"
fi
