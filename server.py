import json
import urllib.request
import urllib.parse
import os
from http.server import HTTPServer, SimpleHTTPRequestHandler
from datetime import datetime, timedelta


# =========================
# CONFIG
# =========================

API_KEY = "YOUR_API_KEY_HERE"

# Fallback location used when the browser doesn't provide coords
# (e.g. geolocation denied, or accessed without a browser)
FALLBACK_LAT = 38.17811   # Cordelia, CA
FALLBACK_LON = -122.13367

FETCH_INTERVAL = timedelta(minutes=10)

# Cache keyed by (lat, lon) rounded to 2 decimal places
# so nearby coords share a cache entry and don't hammer the API
_cache = {}   # { (lat, lon): { 'data': {...}, 'fetched_at': datetime } }


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

    temp_k = data["main"]["temp"]
    temp_f = (temp_k - 273.15) * 9 / 5 + 32

    wind = data.get("wind", {})
    wind_speed_mps = wind.get("speed", 0)
    wind_gust_mps  = wind.get("gust")

    rain_mm = 0.0
    snow_mm = 0.0

    if "rain" in data:
        rain_mm = (
            data["rain"].get("1h")
            or (data["rain"].get("3h", 0) / 3)
            or 0.0
        )

    if "snow" in data:
        snow_mm = (
            data["snow"].get("1h")
            or (data["snow"].get("3h", 0) / 3)
            or 0.0
        )

    condition = None
    if data.get("weather"):
        condition = data["weather"][0].get("description", "").title() or None

    weather = {
        "temp":      round(temp_f, 1),
        "clouds":    data.get("clouds", {}).get("all", 0),
        "humidity":  data["main"].get("humidity"),
        "sunrise":   data["sys"]["sunrise"],
        "sunset":    data["sys"]["sunset"],
        "windSpeed": round(wind_speed_mps * 2.23694, 1),
        "windGust":  (
            round(wind_gust_mps * 2.23694, 1)
            if wind_gust_mps is not None else None
        ),
        "rain":      round(rain_mm, 2),
        "snow":      round(snow_mm, 2),
        "condition": condition,
        "lat":       round(lat, 4),
        "lon":       round(lon, 4),
        "fetchedAt": datetime.now().isoformat(timespec="seconds"),
    }

    print(
        f"[{weather['fetchedAt']}] ({lat:.3f}, {lon:.3f}) "
        f"Temp: {weather['temp']}°F | "
        f"Condition: {weather['condition']} | "
        f"Wind: {weather['windSpeed']} mph | "
        f"Humidity: {weather['humidity']}%"
    )

    _cache[key] = {'data': weather, 'fetched_at': datetime.now()}
    return weather


class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)

        if parsed.path == "/weather.json":
            params = urllib.parse.parse_qs(parsed.query)

            try:
                # Use browser-provided coords if present, else fallback
                if 'lat' in params and 'lon' in params:
                    lat = float(params['lat'][0])
                    lon = float(params['lon'][0])
                else:
                    lat = FALLBACK_LAT
                    lon = FALLBACK_LON

                weather = fetch_weather(lat, lon)

            except Exception as e:
                print(f"Fetch error: {e}")
                # Try to return any cached value for this key
                key = cache_key(lat, lon)
                weather = _cache.get(key, {}).get('data') or {"error": str(e)}

            body = json.dumps(weather).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type",   "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        super().do_GET()

    def log_message(self, format, *args):
        if "/weather.json" not in args[0]:
            super().log_message(format, *args)


if __name__ == "__main__":
    # Always serve from the script's own directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    server = HTTPServer(("0.0.0.0", 3000), Handler)
    print("Ambient weather → http://localhost:3000")
    server.serve_forever()
