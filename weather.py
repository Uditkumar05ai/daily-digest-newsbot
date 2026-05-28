import logging

import requests

logger = logging.getLogger(__name__)

WEATHER_CODES = {
    0: "Clear Sky",
    1: "Partly Cloudy",
    2: "Partly Cloudy",
    3: "Partly Cloudy",
    45: "Foggy",
    48: "Foggy",
    51: "Rainy",
    53: "Rainy",
    55: "Rainy",
    61: "Rainy",
    63: "Rainy",
    65: "Rainy",
    71: "Snowy",
    73: "Snowy",
    75: "Snowy",
    80: "Heavy Showers",
    81: "Heavy Showers",
    82: "Heavy Showers",
    95: "Thunderstorm",
    96: "Thunderstorm",
    99: "Thunderstorm",
}


def get_delhi_weather():
    """Return a one-line Delhi weather summary string, or None on failure."""
    try:
        r = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": 28.6139,
                "longitude": 77.2090,
                "current": "temperature_2m,weathercode,windspeed_10m",
                "timezone": "Asia/Kolkata",
            },
            timeout=10,
        )
        r.raise_for_status()
        cur = r.json()["current"]
        temp = round(cur["temperature_2m"])
        code = int(cur["weathercode"])
        wind = round(cur["windspeed_10m"])
        desc = WEATHER_CODES.get(code, "Cloudy")
        return f"🌤 Delhi: {temp}°C · {desc} · Wind {wind} km/h"
    except Exception as e:
        logger.warning("Weather fetch failed: %s", e)
        return None
