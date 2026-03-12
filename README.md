# Fair Weather

An ambient weather display for Raspberry Pi. A living, breathing canvas that reflects real local conditions — day/night cycle, wind, clouds, rain, snow, humidity, and temperature — rendered as an organic animated organism.

Built to run 24/7 on a Pi with a vertically-mounted HDMI display and touch input.

![Fair Weather display](assets/fairweather-shot-1.jpg)

---

## How it works

A lightweight Python server fetches current conditions from OpenWeatherMap every 10 minutes and serves them as JSON. The browser-based frontend renders an animated canvas that responds to the data in real time — tendril color shifts with temperature, movement responds to wind and gusts, clouds thicken with cloud cover, fog rolls in with humidity, and rain or snow falls when precipitating. The sky cycles through dawn, day, dusk, and night using actual sunrise/sunset times for your location.

---

## Requirements

- Python 3.9+
- A free [OpenWeatherMap API key](https://openweathermap.org/api)
- Chromium (for kiosk display)
- Any modern browser (for development/testing)

---

## Setup

**1. Clone the repo**

```bash
git clone https://github.com/old-peterhof/fairweather.git
cd fairweather
```

**2. Add your API key**

Open `server.py` and replace the placeholder near the top:

```python
API_KEY = "YOUR_API_KEY_HERE"
```

**3. Set your fallback location**

Also in `server.py`, set the coordinates used when geolocation is unavailable:

```python
FALLBACK_LAT = 38.17811
FALLBACK_LON = -122.13367
```

**4. Run the server**

```bash
python3 server.py
```

Then open `http://localhost:3000` in a browser.

---

## Raspberry Pi kiosk setup

Tested on Raspberry Pi OS 64-bit (Debian Trixie), Pi 4B, with labwc as the Wayland compositor.

**1. Copy files to the Pi**

```bash
scp index.html server.py <user>@raspberrypi.local:/home/<user>/fairweather/
```

**2. Install the systemd service**

Create the service file:

```bash
sudo nano /etc/systemd/system/fairweather.service
```

Paste the following, replacing `<user>` with your username:

```ini
[Unit]
Description=Fair Weather ambient display server
After=network-online.target
Wants=network-online.target

[Service]
User=<user>
WorkingDirectory=/home/<user>/fairweather
ExecStart=/usr/bin/python3 /home/<user>/fairweather/server.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Then enable and start it:

```bash
sudo systemctl daemon-reload
sudo systemctl enable fairweather
sudo systemctl start fairweather
```

**3. Set up kiosk autostart**

Create the autostart directory and desktop entry:

```bash
mkdir -p ~/.config/autostart
nano ~/.config/autostart/fairweather.desktop
```

Paste the following:

```ini
[Desktop Entry]
Type=Application
Name=Fair Weather
Exec=chromium --kiosk --noerrdialogs --disable-infobars --no-first-run --disable-translate --disable-features=TranslateUI --overscroll-history-navigation=0 --password-store=basic --use-mock-keychain http://localhost:3000
X-GNOME-Autostart-enabled=true
```

**4. Rotate the display** *(if needed)*

Go to Raspberry Pi OS Settings → Screen Configuration and set your display rotation there. The OS handles this persistently.

**5. Reboot**

```bash
sudo reboot
```

Chromium will launch in fullscreen kiosk mode on boot, pointed at the local server.

**Troubleshooting**

```bash
# Check server logs
journalctl -u fairweather -f

# Confirm server is running
curl http://localhost:3000/weather.json
```

If Chromium loads before the server is ready, increase the startup delay by prepending `sleep 5 &&` to the `Exec` line in `fairweather.desktop`.

---

## Settings

Tap anywhere on the display to show the HUD. A gear icon appears in the bottom-right corner — tap it to open settings.

| Setting | Description |
|---|---|
| Auto-hide after | How long the HUD stays visible after a tap. Set to 0 to keep it always on. |
| Tendrils | Number of tendril arms, 5–15. Reduce for better performance on lower-powered hardware. |
| Color theme | **Natural** — temperature-driven palette. **B&W** — desaturated greys. **Ember** — deep reds and ambers. |
| Font | Switch between sans-serif (Outfit) and serif (Cormorant Garamond). |
| Location | Search by city name, enter coordinates manually, or use device geolocation. |
| Refresh weather | Force an immediate weather fetch. |
| Restart server | Restarts the Python server process — useful after config changes. |

Settings are saved to `localStorage` and restored on reload.

---

## Project structure

```
fairweather/
├── README.md
├── index.html       # Frontend — canvas animation + HUD + settings
└── server.py        # Python HTTP server + OpenWeatherMap integration
```

---

## License

MIT
