"""Open-Meteo API wrapper.

We use Open-Meteo because:
- no API key is required for non-commercial use (ideal for a student project)
- it provides current conditions + hourly + daily forecasts
- it also provides a Historical Weather API to compute climate statistics

Docs:
- Forecast: https://open-meteo.com/en/docs
- Geocoding: https://open-meteo.com/en/docs/geocoding-api
- Historical weather: https://open-meteo.com/en/docs/historical-weather-api
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date
from typing import Any, Dict, Optional

import pandas as pd

from .http_client import build_session

logger = logging.getLogger(__name__)


FORECAST_BASE_URL = "https://api.open-meteo.com/v1/forecast"
GEOCODING_BASE_URL = "https://geocoding-api.open-meteo.com/v1/search"
ARCHIVE_BASE_URL = "https://archive-api.open-meteo.com/v1/archive"


@dataclass(frozen=True)
class Location:
    """A resolved location from the geocoding API."""

    name: str
    country: str
    latitude: float
    longitude: float
    timezone: str
    elevation: Optional[float] = None

    @property
    def label(self) -> str:
        """Human-friendly label for UI."""

        base = f"{self.name}"
        if self.country:
            base += f", {self.country}"
        return base


def geocode_city(
    name: str,
    *,
    language: str = "fr",
    count: int = 10,
    country_code: Optional[str] = None,
    timeout_s: int = 10,
) -> list[Location]:
    """Search for a city and return candidate locations."""

    if not name or len(name.strip()) < 2:
        return []

    session = build_session()
    params: Dict[str, Any] = {
        "name": name.strip(),
        "count": count,
        "format": "json",
        "language": language,
    }
    if country_code:
        params["countryCode"] = country_code

    try:
        resp = session.get(GEOCODING_BASE_URL, params=params, timeout=timeout_s)
        resp.raise_for_status()
        payload = resp.json()
    except Exception as exc:  # noqa: BLE001 - project-level: log and return empty
        logger.exception("Geocoding failed (%s)", exc)
        return []

    results = payload.get("results") or []
    locations: list[Location] = []
    for r in results:
        try:
            locations.append(
                Location(
                    name=str(r.get("name", "")),
                    country=str(r.get("country", r.get("country_code", ""))),
                    latitude=float(r["latitude"]),
                    longitude=float(r["longitude"]),
                    timezone=str(r.get("timezone", "auto")),
                    elevation=float(r["elevation"]) if r.get("elevation") is not None else None,
                )
            )
        except Exception:
            # Skip malformed record
            continue

    return locations


def fetch_forecast(
    location: Location,
    *,
    forecast_days: int = 7,
    past_days: int = 1,
    timeout_s: int = 10,
) -> Dict[str, Any]:
    """Fetch current + hourly + daily forecast for a location."""

    session = build_session()

    # Open‑Meteo uses the `current=`, `hourly=` and `daily=` parameters.
    params: Dict[str, Any] = {
        "latitude": location.latitude,
        "longitude": location.longitude,
        "timezone": location.timezone or "auto",
        "forecast_days": int(forecast_days),
        "past_days": int(past_days),
        "wind_speed_unit": "kmh",
        "temperature_unit": "celsius",
        "precipitation_unit": "mm",
        "current": ",".join(
            [
                "temperature_2m",
                "relative_humidity_2m",
                "apparent_temperature",
                "is_day",
                "precipitation",
                "rain",
                "showers",
                "snowfall",
                "weather_code",
                "cloud_cover",
                "wind_speed_10m",
                "wind_direction_10m",
                "wind_gusts_10m",
            ]
        ),
        "hourly": ",".join(
            [
                "temperature_2m",
                "apparent_temperature",
                "precipitation_probability",
                "precipitation",
                "is_day",
                "weather_code",
                "wind_speed_10m",
                "wind_gusts_10m",
            ]
        ),
        "daily": ",".join(
            [
                "weather_code",
                "temperature_2m_max",
                "temperature_2m_min",
                "precipitation_sum",
                "precipitation_probability_max",
                "wind_speed_10m_max",
                "wind_gusts_10m_max",
                "sunrise",
                "sunset",
            ]
        ),
    }

    try:
        resp = session.get(FORECAST_BASE_URL, params=params, timeout=timeout_s)
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:  # noqa: BLE001
        logger.exception("Forecast API failed (%s)", exc)
        return {}


def fetch_historical_daily(
    location: Location,
    *,
    start: date,
    end: date,
    timeout_s: int = 15,
) -> pd.DataFrame:
    """Fetch historical *daily* data for a location.

    Returns a tidy dataframe with columns:
    - date
    - tmax, tmin, precip_sum
    """

    session = build_session()
    params: Dict[str, Any] = {
        "latitude": location.latitude,
        "longitude": location.longitude,
        "timezone": location.timezone or "auto",
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "daily": ",".join(
            [
                "temperature_2m_max",
                "temperature_2m_min",
                "precipitation_sum",
                "weather_code",
            ]
        ),
        "wind_speed_unit": "kmh",
        "temperature_unit": "celsius",
        "precipitation_unit": "mm",
    }

    try:
        resp = session.get(ARCHIVE_BASE_URL, params=params, timeout=timeout_s)
        resp.raise_for_status()
        payload = resp.json()
    except Exception as exc:  # noqa: BLE001
        logger.exception("Historical API failed (%s)", exc)
        return pd.DataFrame()

    daily = payload.get("daily")
    if not daily:
        return pd.DataFrame()

    df = pd.DataFrame(
        {
            "date": pd.to_datetime(daily.get("time")),
            "tmax": daily.get("temperature_2m_max"),
            "tmin": daily.get("temperature_2m_min"),
            "precip_sum": daily.get("precipitation_sum"),
            "weather_code": daily.get("weather_code"),
        }
    )
    return df
