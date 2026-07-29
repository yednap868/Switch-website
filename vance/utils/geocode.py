"""
Async geocoding utility using OpenStreetMap Nominatim.
Free, no API key needed. Rate limit: 1 request/second.
"""

import asyncio

import aiohttp

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
HEADERS = {"User-Agent": "SwitchApp/1.0 (job-geocoder)"}


async def geocode_location(location: str, city: str = "") -> tuple[float, float] | None:
    """Geocode a location string. Returns (lat, lng) or None."""
    location = (location or "").strip()
    city = (city or "").strip()
    if not location and not city:
        return None

    queries = []
    if location and city:
        queries.append(f"{location}, {city}, India")
    if location:
        queries.append(f"{location}, India")
    if city:
        queries.append(f"{city}, India")

    async with aiohttp.ClientSession() as session:
        for query in queries:
            try:
                async with session.get(
                    NOMINATIM_URL,
                    params={"q": query, "format": "json", "limit": 1, "countrycodes": "in"},
                    headers=HEADERS,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    results = await resp.json()
                    if results:
                        return float(results[0]["lat"]), float(results[0]["lon"])
            except Exception as e:
                print(f"[GEOCODE] Error for '{query}': {e}")
            await asyncio.sleep(1.1)

    return None
