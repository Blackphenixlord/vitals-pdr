#!/usr/bin/env bash
# =============================================================================
#  VITALS installer - ONE script for every machine in the system.
#
#     JETSON (main server)                 Raspberry Pis (screens only)
#     Ollama + model, VITALS server,       Pi 1  astronaut screen (AUI)
#     knowledge base, saved cases          Pi 2  ground crew screen (GCUI)
#                                          Pi 3  doctor screen
#
#  JETSON - from a copy of the repo, on the Jetson itself:
#     sudo ./deploy/install.sh jetson
#     sudo ./deploy/install.sh jetson --kiosk        # also show /status on the Jetson's own screen
#     sudo ./deploy/install.sh update                # after a git pull: copy new code, restart
#
#  EACH PI - one line, the Jetson hands out this script with its own address
#  already filled in (replace 192.168.1.50 with the address the Jetson prints):
#     curl -fsSL http://192.168.1.50:8000/install/astronaut | sudo bash
#     curl -fsSL http://192.168.1.50:8000/install/ground    | sudo bash
#     curl -fsSL http://192.168.1.50:8000/install/doctor    | sudo bash
#  or, with a copy of the repo on the Pi:
#     sudo ./deploy/install.sh astronaut --server 192.168.1.50
#
#  Safe to run again: every step checks what is already there.
#
#  JETSON RULES THIS SCRIPT FOLLOWS (learned the hard way, do not "fix" them):
#   - Ollama comes from ollama.com's installer, which detects JetPack 6 and
#     adds the JetPack 6 GPU build. Not the plain arm64 build, not a container.
#   - It NEVER touches the kernel command line. Never set cma= on this board.
#   - OLLAMA_KEEP_ALIVE=24h so the model stays loaded between questions.
#   - Power mode 25 W (nvpmodel -m 1) unless you pass --power-mode.
#   - Ollama listens on 127.0.0.1 only. The Pis talk to VITALS on :8000,
#     never to the model directly.
# =============================================================================
set -euo pipefail

# ---- settings (flags below override; the Jetson's /install/<role> sets the first two)
ROLE="${VITALS_ROLE:-}"
SERVER="${VITALS_SERVER:-}"
MODEL="${VITALS_OLLAMA_MODEL:-llama3.2}"                    # primary: 3B, ~2 GB - the model every test and mission used
FALLBACK_MODEL="${VITALS_FALLBACK_MODEL:-granite4:micro-h}"   # ~1.9 GB, used if the primary will not pull
PORT="${VITALS_PORT:-8000}"
POWER_MODE="1"                 # nvpmodel mode; 1 = 25 W on the Orin Nano
KIOSK=0                        # jetson: also run a full-screen /status page on its own display
KIOSK_USER=""                  # whose desktop the kiosk runs in (default: the user who ran sudo)
MODEL_SET=0

APP_DIR=/opt/vitals
CONF_DIR=/etc/vitals
DATA_DIR=/var/lib/vitals
SERVICE_USER=vitals

# ---- output ----------------------------------------------------------------
if [ -t 1 ]; then B=$'\e[1m'; G=$'\e[32m'; Y=$'\e[33m'; R=$'\e[31m'; N=$'\e[0m'; else B=; G=; Y=; R=; N=; fi
step() { echo; echo "${B}==> $*${N}"; }
ok()   { echo "    ${G}ok${N}  $*"; }
warn() { echo "    ${Y}!!${N}  $*"; }
die()  { echo; echo "${R}${B}STOPPED:${N} $*" >&2; exit 1; }

usage() {
    cat <<EOF
VITALS installer - one script for the Jetson and all three Pis.

  sudo ./deploy/install.sh jetson [--model NAME] [--fallback NAME] [--port N]
                                  [--power-mode N|none] [--kiosk] [--user NAME]
  sudo ./deploy/install.sh update            (Jetson, after a git pull)
  sudo ./deploy/install.sh astronaut|ground|doctor --server ADDRESS [--user NAME]

  On a Pi, easiest:  curl -fsSL http://<jetson-ip>:8000/install/astronaut | sudo bash
EOF
    exit "${1:-0}"
}

# ---- arguments -------------------------------------------------------------
if [ $# -gt 0 ] && [[ "$1" != --* ]]; then ROLE="$1"; shift; fi
while [ $# -gt 0 ]; do
    case "$1" in
        --server)     SERVER="${2:?--server needs an address}"; shift 2 ;;
        --model)      MODEL="${2:?--model needs a name}"; MODEL_SET=1; shift 2 ;;
        --fallback)   FALLBACK_MODEL="${2:?}"; shift 2 ;;
        --port)       PORT="${2:?}"; shift 2 ;;
        --power-mode) POWER_MODE="${2:?}"; shift 2 ;;
        --kiosk)      KIOSK=1; shift ;;
        --user)       KIOSK_USER="${2:?}"; shift 2 ;;
        -h|--help)    usage 0 ;;
        *)            echo "Unknown option: $1"; usage 1 ;;
    esac
done
[ -n "$ROLE" ] || usage 1
[ "$(id -u)" -eq 0 ] || die "run it with sudo:  sudo $0 $ROLE ..."

KIOSK_USER="${KIOSK_USER:-${SUDO_USER:-}}"
if [ -z "$KIOSK_USER" ] || [ "$KIOSK_USER" = "root" ]; then
    KIOSK_USER="$(getent passwd 1000 | cut -d: -f1 || true)"
fi

export DEBIAN_FRONTEND=noninteractive
APT_UPDATED=0
apt_install() {
    local missing=() pkg
    for pkg in "$@"; do dpkg -s "$pkg" >/dev/null 2>&1 || missing+=("$pkg"); done
    [ ${#missing[@]} -eq 0 ] && return 0
    echo "    ..  installing ${missing[*]}"
    if [ "$APT_UPDATED" -eq 0 ]; then apt-get update -qq >/dev/null; APT_UPDATED=1; fi
    apt-get install -y -qq "${missing[@]}" >/dev/null
}

# Wait for a URL to answer. wait_for URL SECONDS
wait_for() {
    local url="$1" seconds="${2:-60}" i=0
    until curl -fsS --max-time 3 "$url" >/dev/null 2>&1; do
        i=$((i + 1)); [ "$i" -ge "$seconds" ] && return 1; sleep 1
    done
}

model_present() {
    ollama list 2>/dev/null | awk 'NR>1 {print $1}' | grep -qx -e "$1" -e "$1:latest"
}

# =============================================================================
#  KIOSK - shared by the Pis and (optionally) the Jetson's own screen
# =============================================================================
setup_kiosk() {
    local url="$1" label="$2"
    [ -n "$KIOSK_USER" ] || die "could not tell which user's desktop to use - pass --user NAME"
    local home; home="$(getent passwd "$KIOSK_USER" | cut -d: -f6)"
    [ -d "$home" ] || die "user $KIOSK_USER has no home folder"

    step "Full-screen browser for the $label screen (user: $KIOSK_USER)"
    local browser="" b
    for b in chromium-browser chromium google-chrome; do
        command -v "$b" >/dev/null 2>&1 && { browser="$(command -v "$b")"; break; }
    done
    if [ -z "$browser" ]; then
        apt_install chromium-browser 2>/dev/null || apt_install chromium || true
        for b in chromium-browser chromium; do
            command -v "$b" >/dev/null 2>&1 && { browser="$(command -v "$b")"; break; }
        done
    fi
    [ -n "$browser" ] || die "could not install Chromium. Install it by hand, then run this again."
    ok "browser: $browser"
    apt_install curl
    apt_install unclutter 2>/dev/null || true

    mkdir -p "$CONF_DIR"
    cat > "$CONF_DIR/station.env" <<EOF
# Written by deploy/install.sh. Edit and reboot to point this screen somewhere else.
VITALS_STATION=$ROLE
VITALS_URL=$url
VITALS_BROWSER=$browser
EOF
    chmod 644 "$CONF_DIR/station.env"

    # The launcher: wait for the Jetson, then open the page full screen.
    # If the browser ever closes or crashes, it comes straight back.
    cat > /usr/local/bin/vitals-kiosk <<'EOF'
#!/usr/bin/env bash
# VITALS station screen. Started at login by the desktop. Settings: /etc/vitals/station.env
. /etc/vitals/station.env
base="${VITALS_URL%%/login*}"
base="${base%%/status*}"
xset s off -dpms s noblank 2>/dev/null || true          # never blank the screen (X11)
command -v unclutter >/dev/null && { unclutter -idle 3 >/dev/null 2>&1 & }
profile="$HOME/.config/vitals-kiosk"
while true; do
    # Wait for the Jetson. Until it answers, Chromium would only show an error page.
    until curl -fsS --max-time 3 "$base/api/health" >/dev/null 2>&1; do sleep 2; done
    # A power cut leaves "Chromium didn't shut down correctly" behind. Clear it.
    sed -i 's/"exited_cleanly":false/"exited_cleanly":true/; s/"exit_type":"[^"]*"/"exit_type":"Normal"/' \
        "$profile/Default/Preferences" 2>/dev/null || true
    "$VITALS_BROWSER" --kiosk --user-data-dir="$profile" \
        --noerrdialogs --disable-infobars --disable-session-crashed-bubble \
        --disable-features=Translate,TranslateUI --no-first-run --password-store=basic \
        --check-for-update-interval=31536000 --overscroll-history-navigation=0 \
        --disable-pinch "$VITALS_URL" >/dev/null 2>&1
    sleep 2
done
EOF
    chmod 755 /usr/local/bin/vitals-kiosk
    ok "launcher: /usr/local/bin/vitals-kiosk -> $url"

    # Start it when the desktop starts. Raspberry Pi OS uses labwc (newest) or
    # wayfire (early Bookworm); Ubuntu on the Jetson uses GNOME. Each reads a
    # different file, so write the one this machine actually uses.
    local cfg="$home/.config"
    mkdir -p "$cfg/autostart"
    if [ -d /etc/xdg/labwc ] || command -v labwc >/dev/null 2>&1; then
        mkdir -p "$cfg/labwc"
        # A user autostart file REPLACES the desktop's own, so the taskbar and
        # desktop never load - exactly right for a single-purpose screen.
        echo "/usr/local/bin/vitals-kiosk &" > "$cfg/labwc/autostart"
        ok "autostart: labwc ($cfg/labwc/autostart)"
    elif [ -f "$cfg/wayfire.ini" ] || command -v wayfire >/dev/null 2>&1; then
        touch "$cfg/wayfire.ini"
        if ! grep -q '^vitals = ' "$cfg/wayfire.ini"; then
            grep -q '^\[autostart\]' "$cfg/wayfire.ini" || printf '\n[autostart]\n' >> "$cfg/wayfire.ini"
            sed -i '/^\[autostart\]/a vitals = /usr/local/bin/vitals-kiosk' "$cfg/wayfire.ini"
        fi
        ok "autostart: wayfire ($cfg/wayfire.ini)"
    else
        cat > "$cfg/autostart/vitals-kiosk.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=VITALS $label screen
Exec=/usr/local/bin/vitals-kiosk
X-GNOME-Autostart-enabled=true
EOF
        ok "autostart: $cfg/autostart/vitals-kiosk.desktop"
    fi
    chown -R "$KIOSK_USER:" "$cfg"

    # Raspberry Pi: boot straight to the desktop, logged in, and never blank.
    if command -v raspi-config >/dev/null 2>&1; then
        if raspi-config nonint do_boot_behaviour B4 >/dev/null 2>&1; then
            ok "boots to the desktop, logged in"
        else
            warn "could not set desktop auto-login - set it in raspi-config > System > Boot"
        fi
        raspi-config nonint do_blanking 1 >/dev/null 2>&1 && ok "screen blanking off" || true
    else
        warn "turn on automatic login for $KIOSK_USER in the desktop settings, or the screen waits at a login prompt"
        if command -v gsettings >/dev/null 2>&1 && command -v dbus-launch >/dev/null 2>&1; then
            sudo -u "$KIOSK_USER" dbus-launch gsettings set org.gnome.desktop.session idle-delay 0 2>/dev/null || true
            sudo -u "$KIOSK_USER" dbus-launch gsettings set org.gnome.desktop.screensaver lock-enabled false 2>/dev/null || true
        fi
    fi
}

# =============================================================================
#  RASPBERRY PI - a screen for one role
# =============================================================================
install_station() {
    local role="$1" label=""
    case "$role" in
        astronaut) label="astronaut (AUI)" ;;
        ground)    label="ground crew (GCUI)" ;;
        doctor)    label="doctor" ;;
    esac
    [ -n "$SERVER" ] || die "which Jetson? add --server <its address>, e.g. --server 192.168.1.50"

    # Accept 192.168.1.50, 192.168.1.50:8000, vitals.local or a full http:// URL.
    SERVER="${SERVER%/}"
    [[ "$SERVER" == http://* || "$SERVER" == https://* ]] || SERVER="http://$SERVER"
    [[ "${SERVER#*://}" == *:* ]] || SERVER="$SERVER:$PORT"

    step "VITALS $label screen -> server $SERVER"
    apt_install curl
    if wait_for "$SERVER/api/health" 5; then
        ok "the Jetson answers"
    else
        warn "the Jetson did not answer at $SERVER. Installing anyway - the screen waits for it at boot."
        warn "check: same network? Jetson on? 'systemctl status vitals' on the Jetson."
    fi

    setup_kiosk "$SERVER/login?station=$role" "$label"

    step "Done"
    echo "    This Pi now opens the $label screen, full screen, every time it boots."
    echo "    It only accepts $role logins - other roles are refused on this screen."
    echo "    Reboot now:   sudo reboot"
    echo "    Point it at a different Jetson: edit $CONF_DIR/station.env, then reboot."
}

# =============================================================================
#  JETSON - the main server
# =============================================================================
find_repo() {
    local here
    here="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd || true)"
    REPO_DIR="$(cd "$here/.." 2>/dev/null && pwd || true)"
    [ -f "$REPO_DIR/src/vitals/__init__.py" ] \
        || die "run this from a copy of the repo on the Jetson:  cd vitals-pdr && sudo ./deploy/install.sh jetson"
}

copy_app() {
    step "Copying VITALS to $APP_DIR"
    apt_install rsync python3-venv
    mkdir -p "$APP_DIR"
    rsync -a --delete \
        --exclude .git --exclude .venv --exclude venv --exclude data --exclude accounts.json \
        --exclude __pycache__ --exclude .pytest_cache --exclude '*.egg-info' \
        "$REPO_DIR/" "$APP_DIR/"
    ok "code copied ($(cd "$REPO_DIR" && git rev-parse --short HEAD 2>/dev/null || echo 'no git'))"

    [ -x "$APP_DIR/.venv/bin/python" ] || python3 -m venv "$APP_DIR/.venv"
    "$APP_DIR/.venv/bin/pip" install -q --upgrade pip
    "$APP_DIR/.venv/bin/pip" install -q "PyYAML>=6.0" "jsonschema>=4.20"
    ok "python packages installed"

    PYTHONPATH="$APP_DIR/src" "$APP_DIR/.venv/bin/python" -m vitals validate >/dev/null \
        || die "the knowledge base did not validate - fix it before deploying (python -m vitals validate)"
    ok "knowledge base valid"
}

install_jetson() {
    find_repo
    step "Checking the board"
    [ "$(uname -m)" = "aarch64" ] || warn "this is $(uname -m), not a Jetson (aarch64). Continuing anyway."
    if [ -f /etc/nv_tegra_release ]; then
        local l4t; l4t="$(head -n1 /etc/nv_tegra_release)"
        if [[ "$l4t" == *R36* ]]; then ok "JetPack 6 ($l4t)"; else warn "not JetPack 6: $l4t - the GPU build of Ollama expects JetPack 6"; fi
    else
        warn "no /etc/nv_tegra_release - not a Jetson? Ollama will run on the CPU."
    fi

    apt_install python3 python3-venv python3-pip curl ca-certificates avahi-daemon
    systemctl enable --now avahi-daemon >/dev/null 2>&1 || true
    ok "base packages (the Jetson is also reachable as $(hostname).local)"

    # Power mode. Only nvpmodel - the kernel command line (cma= etc.) is left alone.
    if [ "$POWER_MODE" != "none" ] && command -v nvpmodel >/dev/null 2>&1; then
        if nvpmodel -m "$POWER_MODE" >/dev/null 2>&1; then
            ok "power mode $POWER_MODE ($(nvpmodel -q 2>/dev/null | head -n1 | sed 's/^NV Power Mode: //'))"
        else
            warn "nvpmodel -m $POWER_MODE was refused. List the modes with: nvpmodel -p --verbose"
        fi
    fi

    # ---- Ollama -----------------------------------------------------------
    step "Ollama (runs the language model)"
    if command -v ollama >/dev/null 2>&1; then
        ok "already installed: $(ollama --version 2>/dev/null | tail -n1)"
    else
        # ollama.com's installer detects JetPack 6 from /etc/nv_tegra_release and
        # installs the JetPack 6 GPU libraries alongside the arm64 build.
        curl -fsSL https://ollama.com/install.sh | sh
        ok "installed"
    fi
    mkdir -p /etc/systemd/system/ollama.service.d
    cat > /etc/systemd/system/ollama.service.d/vitals.conf <<EOF
# Written by deploy/install.sh
[Service]
Environment="OLLAMA_KEEP_ALIVE=24h"
Environment="OLLAMA_HOST=127.0.0.1:11434"
EOF
    systemctl daemon-reload
    systemctl enable ollama >/dev/null 2>&1 || true
    systemctl restart ollama
    wait_for http://127.0.0.1:11434/api/tags 60 || die "Ollama did not start. Look at: journalctl -u ollama -n 50"
    ok "running, model kept loaded for 24h, local only"

    # ---- the model --------------------------------------------------------
    step "Model: $MODEL (backup: $FALLBACK_MODEL)"
    local use_model="$MODEL"
    if model_present "$MODEL"; then
        ok "$MODEL already downloaded"
    elif ollama pull "$MODEL"; then
        ok "$MODEL downloaded"
    else
        warn "$MODEL would not download"
        use_model=""
    fi
    if [ -n "$FALLBACK_MODEL" ] && [ "$FALLBACK_MODEL" != "none" ]; then
        if model_present "$FALLBACK_MODEL" || ollama pull "$FALLBACK_MODEL"; then
            ok "backup $FALLBACK_MODEL ready"
            [ -n "$use_model" ] || { use_model="$FALLBACK_MODEL"; warn "using the backup model instead"; }
        else
            warn "backup $FALLBACK_MODEL would not download"
        fi
    fi
    [ -n "$use_model" ] || die "no model could be downloaded. Check the internet connection, then run this again."

    # ---- VITALS ------------------------------------------------------------
    copy_app

    step "VITALS service"
    id "$SERVICE_USER" >/dev/null 2>&1 || useradd --system --home "$DATA_DIR" --shell /usr/sbin/nologin "$SERVICE_USER"
    mkdir -p "$CONF_DIR" "$DATA_DIR"
    chown -R "$SERVICE_USER:" "$DATA_DIR"
    chmod 750 "$DATA_DIR"

    local env_file="$CONF_DIR/vitals.env"
    if [ ! -f "$env_file" ]; then
        cat > "$env_file" <<EOF
# VITALS server settings. Edit, then: sudo systemctl restart vitals
VITALS_OLLAMA_MODEL=$use_model
OLLAMA_HOST=http://127.0.0.1:11434
VITALS_DATA_DIR=$DATA_DIR
VITALS_ACCOUNTS=$CONF_DIR/accounts.json
VITALS_PORT=$PORT
EOF
        ok "settings: $env_file"
    else
        # Keep the existing settings. Change the model only if asked to, or if
        # the one on file is not actually downloaded.
        local current; current="$(sed -n 's/^VITALS_OLLAMA_MODEL=//p' "$env_file")"
        if [ "$MODEL_SET" -eq 1 ] || ! model_present "$current"; then
            sed -i "s|^VITALS_OLLAMA_MODEL=.*|VITALS_OLLAMA_MODEL=$use_model|" "$env_file"
        fi
        if grep -q '^VITALS_PORT=' "$env_file"; then
            sed -i "s|^VITALS_PORT=.*|VITALS_PORT=$PORT|" "$env_file"
        else
            echo "VITALS_PORT=$PORT" >> "$env_file"
        fi
        ok "settings kept: $env_file"
    fi
    chgrp "$SERVICE_USER" "$CONF_DIR" "$env_file"; chmod 750 "$CONF_DIR"; chmod 640 "$env_file"
    if [ -f "$CONF_DIR/accounts.json" ]; then
        chgrp "$SERVICE_USER" "$CONF_DIR/accounts.json"; chmod 640 "$CONF_DIR/accounts.json"
    fi

    # `vitals` command for the Jetson's terminal, using the service's settings.
    cat > /usr/local/bin/vitals <<EOF
#!/bin/sh
# VITALS command line with the server's settings, e.g.
#   sudo vitals add-account --id astro-1 --name "Alex Rivera" --role astronaut
set -a; . $CONF_DIR/vitals.env; set +a
PYTHONPATH=$APP_DIR/src exec $APP_DIR/.venv/bin/python -m vitals "\$@"
EOF
    chmod 755 /usr/local/bin/vitals

    cat > /etc/systemd/system/vitals.service <<EOF
# Written by deploy/install.sh
[Unit]
Description=VITALS medical decision support server
Wants=network-online.target ollama.service
After=network-online.target ollama.service

[Service]
User=$SERVICE_USER
Group=$SERVICE_USER
EnvironmentFile=$CONF_DIR/vitals.env
Environment=PYTHONPATH=$APP_DIR/src
Environment=PYTHONUNBUFFERED=1
WorkingDirectory=$APP_DIR
ExecStart=$APP_DIR/.venv/bin/python -m vitals serve --host 0.0.0.0 --port \${VITALS_PORT} --no-open
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF
    systemctl daemon-reload
    systemctl enable vitals >/dev/null 2>&1
    systemctl restart vitals
    wait_for "http://127.0.0.1:$PORT/api/health" 30 || die "VITALS did not start. Look at: journalctl -u vitals -n 50"
    ok "running on port $PORT, starts on every boot"

    if command -v ufw >/dev/null 2>&1 && ufw status 2>/dev/null | grep -q "Status: active"; then
        ufw allow "$PORT/tcp" >/dev/null && ok "firewall: port $PORT open for the Pis"
    fi

    # ---- warm up and check the GPU -----------------------------------------
    step "Loading the model onto the GPU (the first load can take a minute)"
    curl -fsS --max-time 300 http://127.0.0.1:11434/api/generate \
        -d "{\"model\":\"$use_model\",\"prompt\":\"ok\",\"stream\":false,\"keep_alive\":\"24h\",\"options\":{\"num_predict\":1}}" \
        >/dev/null 2>&1 || warn "warm-up request failed - the first question will be slow"
    local processor
    processor="$(ollama ps 2>/dev/null | awk 'NR>1 {for (i=1;i<=NF;i++) if ($i=="GPU" || $i=="CPU" || $i ~ /GPU$|CPU$/) {print $(i-1), $i; exit}}')"
    if [[ "$processor" == *GPU* ]]; then
        ok "model is on the GPU ($processor)"
    else
        warn "model is NOT on the GPU (${processor:-unknown}). Answers will be slow. Check: journalctl -u ollama | grep -i -e cuda -e gpu"
    fi

    if [ "$KIOSK" -eq 1 ]; then
        setup_kiosk "http://localhost:$PORT/status" "Jetson status"
    fi

    # ---- what to do next ---------------------------------------------------
    local first
    first="$(hostname -I 2>/dev/null | tr ' ' '\n' | grep -E '^[0-9]+\.' | grep -v '^127\.' | head -n1 || true)"
    first="${first:-<jetson-ip>}"
    step "Done - the Jetson is the VITALS server"
    echo "    Status page:   http://$first:$PORT/status    (or http://$(hostname).local:$PORT/status)"
    echo
    echo "    Now set up each Raspberry Pi. Run ONE line on each:"
    echo "      Pi 1, astronaut:   curl -fsSL http://$first:$PORT/install/astronaut | sudo bash"
    echo "      Pi 2, ground crew: curl -fsSL http://$first:$PORT/install/ground    | sudo bash"
    echo "      Pi 3, doctor:      curl -fsSL http://$first:$PORT/install/doctor    | sudo bash"
    echo
    if [ ! -f "$CONF_DIR/accounts.json" ]; then
        warn "Using the DEMO logins (astronaut 1111, ground 2222, doctor 3333). Add real people with:"
        echo "      sudo vitals add-account --id astro-1 --name \"Alex Rivera\" --role astronaut"
        echo "      sudo chgrp $SERVICE_USER $CONF_DIR/accounts.json && sudo chmod 640 $CONF_DIR/accounts.json"
        echo "      sudo systemctl restart vitals"
    fi
    echo "    Give the Jetson a fixed address (DHCP reservation on the router) so the Pis always find it."
    echo "    Logs:  journalctl -u vitals -f        Restart:  sudo systemctl restart vitals"
}

update_jetson() {
    find_repo
    [ -f /etc/systemd/system/vitals.service ] || die "VITALS is not installed here yet - run: sudo $0 jetson"
    PORT="$(sed -n 's/^VITALS_PORT=//p' "$CONF_DIR/vitals.env" 2>/dev/null || true)"
    PORT="${PORT:-8000}"
    copy_app
    systemctl restart vitals
    wait_for "http://127.0.0.1:$PORT/api/health" 30 || die "VITALS did not come back. Look at: journalctl -u vitals -n 50"
    step "Updated and restarted. Cases and accounts were not touched."
}

# =============================================================================
case "$ROLE" in
    jetson|server)              install_jetson ;;
    update)                     update_jetson ;;
    astronaut|ground|doctor)    install_station "$ROLE" ;;
    *)                          echo "Unknown machine: $ROLE"; usage 1 ;;
esac
