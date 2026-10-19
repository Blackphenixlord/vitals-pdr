# Deploying VITALS - the Jetson and the three Pis

> **For the PDR demo (one Jetson + one Pi, no internet at the venue): follow [PDR-DEMO.md](PDR-DEMO.md).**

```
                ┌────────────── JETSON  (main server) ──────────────┐
                │  Ollama + model on the GPU    VITALS server :8000 │
                │  knowledge base   saved cases   /status screen    │
                └────────────────────────┬──────────────────────────┘
                          same network (switch or wifi)
          ┌──────────────────────────────┼──────────────────────────────┐
     Pi 1  astronaut (AUI)          Pi 2  ground crew (GCUI)        Pi 3  doctor
     /login?station=astronaut       /login?station=ground           /login?station=doctor
```

**The Jetson does all the work.** The Pis are screens only: each one boots straight
into one full-screen page from the Jetson. Nothing is stored on a Pi, so one can be
unplugged or swapped without losing anything.

One script, `deploy/install.sh`, sets up every machine.

## 1. The Jetson (once)

Needs: JetPack 6 flashed, internet for the first install (it downloads Ollama and
the models, ~6 GB), and a copy of this repo on the Jetson.

```bash
gh auth login          # the repo is private: sign in once (or copy the folder over on a USB stick)
gh repo clone Blackphenixlord/vitals-pdr
cd vitals-pdr
sudo ./deploy/install.sh jetson
```

That installs and starts, in order:

| step | what | why |
|---|---|---|
| power | `nvpmodel -m 1` (25 W) | full GPU speed. The kernel command line is never touched (no `cma=`). |
| Ollama | ollama.com installer, JetPack 6 GPU build | runs the model on the GPU |
| Ollama settings | `OLLAMA_KEEP_ALIVE=24h`, listens on 127.0.0.1 only | model stays loaded; the Pis never talk to the model directly |
| model | `llama3.2` (3B), backup `granite4:micro-h` | the model all tests and missions used; backup only if it will not download |
| VITALS | copied to `/opt/vitals`, Python venv, knowledge base validated | refuses to install a broken knowledge base |
| service | `vitals.service`, port 8000 on all interfaces, starts on boot, restarts if it crashes | the Pis connect here |
| data | cases in `/var/lib/vitals`, settings in `/etc/vitals/vitals.env` | survives updates and reboots |
| check | warms the model and reports whether it is really on the GPU | a CPU fallback is slow and easy to miss |

At the end it prints the Jetson's address and the exact line to run on each Pi.

Options: `--model NAME`, `--fallback NAME`, `--port N`, `--power-mode N|none`,
`--kiosk` (also show the `/status` page full screen on the Jetson's own monitor).

**Give the Jetson a fixed address** (a DHCP reservation on the router). The Pis are
told its address once.

## 2. Each Pi (once each)

Needs: Raspberry Pi OS **with desktop**, on the same network as the Jetson.
On each Pi, run ONE line (use the address the Jetson printed, or read it off
`http://<jetson>:8000/status`):

```bash
curl -fsSL http://192.168.1.50:8000/install/astronaut | sudo bash    # Pi 1
curl -fsSL http://192.168.1.50:8000/install/ground    | sudo bash    # Pi 2
curl -fsSL http://192.168.1.50:8000/install/doctor    | sudo bash    # Pi 3
sudo reboot
```

The Jetson hands out the installer with its own address already filled in. On
the Pi it installs Chromium if needed, sets the Pi to boot to the desktop logged
in, turns off screen blanking, and starts the page full screen at every boot. If
the Jetson is not up yet, the Pi waits for it instead of showing an error page.
If the browser crashes, it comes straight back.

Each Pi is **locked to its role**: the doctor's Pi refuses a ground crew login,
so the full unredacted ground view can never open on the doctor's screen.
Emergency access (no PIN) only exists on the astronaut's Pi.

From a copy of the repo instead: `sudo ./deploy/install.sh doctor --server 192.168.1.50`.
To point a Pi at a different Jetson later: edit `/etc/vitals/station.env`, reboot.

## 3. Logins

Until you add real accounts the server uses the demo ones:
astronaut **1111**, ground crew **2222**, doctor **3333**. Add real people on the Jetson:

```bash
sudo vitals add-account --id astro-1 --name "Alex Rivera" --role astronaut --profile "Height=178 cm"
sudo chgrp vitals /etc/vitals/accounts.json && sudo chmod 640 /etc/vitals/accounts.json
sudo systemctl restart vitals
```

Once `/etc/vitals/accounts.json` exists the demo accounts stop working.

## The flow the three screens run

1. **Astronaut** describes symptoms. Every medical answer is saved on the Jetson as a case.
2. **Ground crew** sees every case and everything VITALS said, can correct the
   astronaut's details, ticks what the doctor must not see (name hidden by
   default), and sends it. The Jetson builds the redacted packet, so hidden
   fields never reach the doctor's Pi. "Print / save as PDF" prints the packet.
3. **Doctor** sees only that packet and replies: I agree / I disagree / my own read.
4. **Ground crew** checks the reply, edits the wording if needed, and releases it.
5. **Astronaut** sees it in the Doctor notes tab (a dot appears on the icon).

## Day to day

| task | command (on the Jetson) |
|---|---|
| is it running | open `http://<jetson>:8000/status` |
| logs | `journalctl -u vitals -f` / `journalctl -u ollama -f` |
| restart | `sudo systemctl restart vitals` |
| update after `git pull` | `sudo ./deploy/install.sh update` (cases and accounts are kept) |
| change model | `sudo ./deploy/install.sh jetson --model NAME` |
| is the model on the GPU | `ollama ps` - PROCESSOR should say GPU |
| run the benchmark | `sudo vitals bench` |

## Not done yet (honest list)

- Not yet run on the real Jetson or Pis. The Pi install was tested end to end in
  a Linux sandbox (stand-in browser), and every screen was driven in a real
  browser against a stand-in model. First run on the board: watch the GPU line.
- Sensors: the astronaut Pi will eventually read the MAX30102 etc. That needs a
  small sensor service on that Pi sending readings to the Jetson - not built.
- No HTTPS between the Pis and the Jetson. Fine on a closed team network; do not
  put the Jetson on the open internet.
