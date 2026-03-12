import json
import os
import sys
import threading
import urllib.request
import urllib.parse
from http.server import HTTPServer, SimpleHTTPRequestHandler
from datetime import datetime, timedelta


# =========================
# CONFIG
# =========================

API_KEY = "YOUR_API_KEY_HERE"

FALLBACK_LAT = 38.17811   # Cordelia, CA
FALLBACK_LON = -122.13367

FETCH_INTERVAL = timedelta(minutes=10)

_cache = {}  # { (lat, lon): { 'data': {...}, 'fetched_at': datetime } }


def cache_key(lat, lon):
    return (round(lat, 2), round(lon, 2))


def fetch_weather(lat, lon):
    key = cache_key(lat, lon)
    entry = _cache.get(key)

    if entry and datetime.now() - entry['fetched_at'] < FETCH_INTERVAL:
        return entry['data']

    url = (
        "https://api.openweathermap.org/data/2.5/weather"
        f"?lat={lat}&lon={lon}&appid={API_KEY}"
    )

    with urllib.request.urlopen(url, timeout=10) as response:
        data = json.loads(response.read().decode())

    temp_f = (data["main"]["temp"] - 273.15) * 9 / 5 + 32
    wind   = data.get("wind", {})

    rain_mm = 0.0
    snow_mm = 0.0
    if "rain" in data:
        rain_mm = data["rain"].get("1h") or (data["rain"].get("3h", 0) / 3) or 0.0
    if "snow" in data:
        snow_mm = data["snow"].get("1h") or (data["snow"].get("3h", 0) / 3) or 0.0

    condition = None
    if data.get("weather"):
        condition = data["weather"][0].get("description", "").title() or None

    gust_mps = wind.get("gust")

    weather = {
        "temp":      round(temp_f, 1),
        "clouds":    data.get("clouds", {}).get("all", 0),
        "humidity":  data["main"].get("humidity"),
        "sunrise":   data["sys"]["sunrise"],
        "sunset":    data["sys"]["sunset"],
        "windSpeed": round(wind.get("speed", 0) * 2.23694, 1),
        "windGust":  round(gust_mps * 2.23694, 1) if gust_mps is not None else None,
        "rain":      round(rain_mm, 2),
        "snow":      round(snow_mm, 2),
        "condition": condition,
        "lat":       round(lat, 4),
        "lon":       round(lon, 4),
        "fetchedAt": datetime.now().isoformat(timespec="seconds"),
    }

    print(
        f"[{weather['fetchedAt']}] ({lat:.3f}, {lon:.3f}) "
        f"{weather['temp']}°F | {weather['condition']} | "
        f"Wind: {weather['windSpeed']} mph | Humidity: {weather['humidity']}%"
    )

    _cache[key] = {'data': weather, 'fetched_at': datetime.now()}
    return weather


def geocode(query):
    """Resolve a city/place name to lat/lon via OWM geocoding API."""
    url = (
        "http://api.openweathermap.org/geo/1.0/direct"
        f"?q={urllib.parse.quote(query)}&limit=1&appid={API_KEY}"
    )
    with urllib.request.urlopen(url, timeout=10) as response:
        results = json.loads(response.read().decode())

    if not results:
        return {"error": f"No results found for '{query}'"}

    r = results[0]
    return {
        "lat":     round(r["lat"], 5),
        "lon":     round(r["lon"], 5),
        "name":    r.get("name", query),
        "country": r.get("country", ""),
        "state":   r.get("state", ""),
    }


class Handler(SimpleHTTPRequestHandler):

    def send_json(self, data, status=200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)

        # ── Weather endpoint ──
        if parsed.path == "/weather.json":
            try:
                if 'lat' in params and 'lon' in params:
                    lat = float(params['lat'][0])
                    lon = float(params['lon'][0])
                else:
                    lat, lon = FALLBACK_LAT, FALLBACK_LON

                self.send_json(fetch_weather(lat, lon))

            except Exception as e:
                print(f"Weather fetch error: {e}")
                key = cache_key(lat, lon)
                cached = _cache.get(key, {}).get('data')
                self.send_json(cached or {"error": str(e)},
                               status=200 if cached else 500)
            return

        # ── Geocode endpoint ──
        if parsed.path == "/geocode":
            q = params.get('q', [''])[0].strip()
            if not q:
                self.send_json({"error": "No query provided"}, status=400)
                return
            try:
                self.send_json(geocode(q))
            except Exception as e:
                self.send_json({"error": str(e)}, status=500)
            return

        super().do_GET()

    def do_POST(self):
        # ── Restart endpoint ──
        if self.path == "/restart":
            self.send_json({"status": "restarting"})
            def _restart():
                import time; time.sleep(0.8)
                os.execv(sys.executable, [sys.executable] + sys.argv)
            threading.Thread(target=_restart, daemon=True).start()
            return

        self.send_response(404)
        self.end_headers()

    def log_message(self, format, *args):
        if args and isinstance(args[0], str) and any(x in args[0] for x in ["/weather.json", "/geocode", "/restart"]):
            return
        super().log_message(format, *args)


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    server = HTTPServer(("0.0.0.0", 3000), Handler)
    print("Ambient weather → http://localhost:3000")
    server.serve_forever()
