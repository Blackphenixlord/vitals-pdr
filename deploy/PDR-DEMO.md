# PDR demo: Jetson + one Pi, no internet

What the judges see: you type a symptom on the **Pi's screen**, the **Jetson** (the real flight
computer) answers, and nothing is connected to the internet.

```
 [ Pi + monitor + keyboard ] ──── one Ethernet cable ──── [ Jetson ]
   astronaut screen                                         VITALS server + AI model
   10.42.0.2                                                10.42.0.1
```

The laptop still comes as the backup. It runs the same thing (`python -m vitals serve`).

---

## Tonight, at home (needs internet, about 1 hour, mostly downloading)

Plug both boards into your home network over **Wi-Fi**, and connect them to each other with the
**Ethernet cable**. The cable link and the Wi-Fi work at the same time.

> **Do the Jetson FIRST, then the Pi.** The Pi downloads its installer from the Jetson, so the
> Pi's step 3 fails until the Jetson is set up and running.

### On the Jetson (do this first; needs internet, a monitor and keyboard, cable plugged into the Pi)

**Step 1: check the Jetson's software version**

```bash
cat /etc/nv_tegra_release
```

It should show **R36** somewhere (that's JetPack 6). If it shows anything else, stop and ask before
going on.

**Step 2: download VITALS**

```bash
git clone https://github.com/Blackphenixlord/vitals-pdr.git
cd vitals-pdr
```

**Step 3: install it (the long one, about 20 to 40 minutes)**

```bash
sudo ./deploy/install.sh jetson
```

This installs Ollama and the llama3.2 AI model, sets up VITALS, and starts it every time the
Jetson boots. Most of the time is the model downloading. Let it finish. It ends with a summary
showing the Jetson's address.

**Step 4: give the Jetson its cable address**

```bash
sudo ./deploy/demo-link.sh jetson
```

You should see `ok  jetson is 10.42.0.1`.

**Step 5: check it works**

```bash
ollama ps
curl -s http://127.0.0.1:8000/api/health
```

- `ollama ps` → the PROCESSOR column should say **GPU**. If it says CPU, answers will be too slow
  for a demo; see "If something goes wrong" below.
- The `curl` line should print some text starting with `{`. If it prints nothing, VITALS isn't
  running: `systemctl status vitals`.

If anything prints red text or `STOPPED:`, take a photo of it. The message says what went wrong.

### On the Pi (Raspberry Pi OS **with desktop**)

> **Order matters.** Step 1 can be done any time. Steps 2 and 3 only work after the Jetson has
> finished `install.sh jetson` **and** `demo-link.sh jetson`, with the cable plugged in. Keep the
> Pi's Wi-Fi on the whole time so it still has internet.

**Step 1: get the cable script and give the Pi its cable address**

```bash
curl -fsSLO https://raw.githubusercontent.com/Blackphenixlord/vitals-pdr/main/deploy/demo-link.sh
sudo bash demo-link.sh pi
```

You should see `ok  pi is 10.42.0.2`. If the cable isn't plugged in yet it says so; that's fine,
the link comes up by itself once it is.

**Step 2: check the Pi can reach the Jetson**

```bash
ping -c 3 10.42.0.1
```

- Replies like `64 bytes from 10.42.0.1` → good, go to step 3.
- `Destination Host Unreachable` → the Jetson isn't finished yet, `demo-link.sh jetson` wasn't
  run, or the cable is loose.

**Step 3: install the astronaut screen and reboot**

```bash
curl -fsSL http://10.42.0.1:8000/install/astronaut | sudo bash
sudo reboot
```

After the reboot the Pi opens the VITALS login full screen by itself. Log in with PIN **1111**.

If any step prints red text or `STOPPED:`, copy the whole message. It says what went wrong.

### Then test it the way it will run on Wednesday

1. **Unplug the internet**: turn the Wi-Fi off on both boards (or unplug the router).
2. Turn both boards off. Turn on the Jetson, wait about 1 minute, then turn on the Pi.
3. On the Pi: PIN **1111** → type
   *"bad pain in my right side, comes in waves, goes toward my groin, blood when I pee"*
4. You should get **URGENT — kidney stone** with sources. Time it: the first answer is slower
   (the model is loading); the second should take a few seconds.
5. Try the emergency button and the *Wrong?* button too.

If all five work with the Wi-Fi off, you're done.

---

## Wednesday at the table

1. Plug in: Jetson power, Pi power, Pi monitor + keyboard + mouse, **the Ethernet cable between them**.
2. Turn on the Jetson first. Give it about a minute, then turn on the Pi.
3. Ask one warm-up question before judges arrive so the model is already loaded.
4. Keep the laptop next to it, already running `python -m vitals serve`, in case anything fails.

**What to say:** "This is the real setup. The Jetson is the server with the AI and the NASA
research on it, and the Pi is the astronaut's screen. There's no internet here. The ground crew
and doctor screens are planned; they'll be two more Pis on the same cable network."

---

## If something goes wrong

| Problem | Fix |
|---|---|
| Pi step 3 fails / does nothing | The Jetson isn't set up or isn't on. Do the Jetson steps first, then run Pi step 3 again |
| Pi says it's waiting for the server | Jetson not up yet, or the cable is loose. Check from the Pi with `ping 10.42.0.1` |
| Answers take 30+ seconds every time | Model is on the CPU. On the Jetson, `ollama ps` should say GPU. `sudo nvpmodel -m 1` and restart: `sudo systemctl restart ollama vitals` |
| "Model not found" | Jetson needs internet once: `ollama pull llama3.2` |
| Pi shows a blank or old page | Press `F5`, or `sudo reboot` on the Pi |
| Anything else, no time to fix | Switch to the laptop. Same software, same answers |

Logs on the Jetson: `journalctl -u vitals -f` and `journalctl -u ollama -f`.
