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

### On the Jetson

```bash
cat /etc/nv_tegra_release           # should say R36 (JetPack 6)
gh auth login                       # repo is private (or copy the vitals-pdr folder over on a USB stick)
gh repo clone Blackphenixlord/vitals-pdr
cd vitals-pdr
sudo ./deploy/install.sh jetson     # installs Ollama + llama3.2 + VITALS, starts it on boot
sudo ./deploy/demo-link.sh jetson   # cable address 10.42.0.1
```

When the installer finishes, check:

```bash
ollama ps                                   # PROCESSOR should say GPU (CPU = too slow for a demo)
curl -s http://127.0.0.1:8000/ | head -3    # the login page answers
```

### On the Pi (Raspberry Pi OS **with desktop**)

```bash
# get the cable script from the Jetson, or copy deploy/demo-link.sh over on a USB stick
sudo bash demo-link.sh pi                    # cable address 10.42.0.2
ping -c 3 10.42.0.1                          # must answer
curl -fsSL http://10.42.0.1:8000/install/astronaut | sudo bash
sudo reboot
```

After the reboot the Pi opens the VITALS login full screen by itself.

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
| Pi says it's waiting for the server | Jetson not up yet, or the cable is loose. Check from the Pi with `ping 10.42.0.1` |
| Answers take 30+ seconds every time | Model is on the CPU. On the Jetson, `ollama ps` should say GPU. `sudo nvpmodel -m 1` and restart: `sudo systemctl restart ollama vitals` |
| "Model not found" | Jetson needs internet once: `ollama pull llama3.2` |
| Pi shows a blank or old page | Press `F5`, or `sudo reboot` on the Pi |
| Anything else, no time to fix | Switch to the laptop. Same software, same answers |

Logs on the Jetson: `journalctl -u vitals -f` and `journalctl -u ollama -f`.
