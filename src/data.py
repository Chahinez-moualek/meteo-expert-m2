"""Data layer: collection + cleaning helpers.

The project is split in two parts:
1) *Collection* (API calls): Open‑Meteo endpoints
2) *Cleaning/structuring*: convert JSON payloads to tidy pandas DataFrames

This module groups the most important "data" operations in one place so that
the Streamlit UI (app/streamlit_app.py) stays focused on presentation.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Dict, Optional

import pandas as pd

from .open_meteo_api import Location, fetch_forecast as _fetch_forecast, fetch_historical_daily as _fetch_historical_daily, geocode_city as _geocode_city
from .vigilance import compute_vigilance

from pathlib import Path
import json

# -----------------------------
# Data folder (raw + processed)
# -----------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
for _d in (DATA_DIR, RAW_DIR, PROCESSED_DIR):
    _d.mkdir(parents=True, exist_ok=True)

def _normalize_dates(values) -> pd.Series:
    """Return a normalized date Series from list/Index/Series of datetimes."""
    dt = pd.to_datetime(values, errors='coerce')
    # pd.to_datetime(list) may return a DatetimeIndex (no .dt accessor)
    if hasattr(dt, 'dt'):
        return dt.dt.normalize()
    return pd.DatetimeIndex(dt).normalize().to_series(index=range(len(dt)))

def _slug(loc: Location) -> str:
    s = f"{loc.name}-{loc.country}".lower()
    s = ''.join(ch if ch.isalnum() else '-' for ch in s)
    s = '-'.join([p for p in s.split('-') if p])
    return s[:80] or 'location'

def save_raw_json(filename: str, payload: Dict[str, Any]) -> None:
    try:
        (RAW_DIR / filename).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    except Exception:
        # Never crash the UI because of filesystem issues.
        return

def save_processed_csv(filename: str, df: pd.DataFrame) -> None:
    try:
        df.to_csv(PROCESSED_DIR / filename, index=False)
    except Exception:
        return



# -----------------------------
# Collection wrappers (save payloads to ./data)
# -----------------------------

def geocode_city(name: str, *, country_code: Optional[str] = None, language: str = 'fr', count: int = 10) -> list[Location]:
    """Geocode a city name and persist results in data/raw (for reproducibility)."""
    locs = _geocode_city(name, country_code=country_code, language=language, count=count)
    try:
        payload = [loc.__dict__ for loc in locs]
        save_raw_json(f"geocode_{name.strip().lower()[:40]}.json", payload)
    except Exception:
        pass
    return locs

def fetch_forecast(location: Location) -> Dict[str, Any]:
    """Fetch forecast JSON and save it to data/raw."""
    payload = _fetch_forecast(location)
    save_raw_json(f"forecast_{_slug(location)}.json", payload)
    # Also save the tidy tables for grading / debug
    h = to_hourly_df(payload)
    d = to_daily_df(payload)
    if not h.empty:
        save_processed_csv(f"hourly_{_slug(location)}.csv", h)
    if not d.empty:
        save_processed_csv(f"daily_{_slug(location)}.csv", d)
    return payload

def fetch_historical_daily(location: Location, *, start: date, end: date) -> pd.DataFrame:
    """Fetch historical daily data and save it to data/raw + data/processed."""
    df = _fetch_historical_daily(location, start=start, end=end)
    if not df.empty:
        save_processed_csv(f"historical_daily_{_slug(location)}_{start}_{end}.csv", df)
    return df

# -----------------------------
# Default cities (France-first)
# -----------------------------

# A curated list of popular French cities to match the "weather app" experience.
DEFAULT_FAVORITES_FR: list[str] = [
    "Paris",
    "Marseille",
    "Lyon",
    "Toulouse",
    "Nice",
    "Nantes",
    "Montpellier",
    "Strasbourg",
    "Bordeaux",
    "Lille",
    "Rennes",
    "Reims",
    "Le Havre",
    "Saint-Étienne",
    "Toulon",
    "Grenoble",
    "Dijon",
    "Angers",
    "Nîmes",
    "Villeurbanne",
    "Clermont-Ferrand",
    "Le Mans",
    "Aix-en-Provence",
    "Brest",
    "Tours",
    "Amiens",
    "Limoges",
    "Annecy",
    "Perpignan",
    "Metz",
    "Besançon",
    "Orléans",
    "Caen",
    "Rouen",
    "Mulhouse",
    "Nancy",
    "Avignon",
    "Chambéry",
    "Quimper",
    "Ajaccio",
    "Biarritz",
    "La Rochelle",
    "Saint-Malo",
]


# -----------------------------
# JSON -> DataFrame
# -----------------------------


def to_hourly_df(payload: Dict[str, Any]) -> pd.DataFrame:
    """Convert Open‑Meteo forecast payload to an hourly DataFrame."""

    hourly = payload.get("hourly") or {}
    if not hourly:
        return pd.DataFrame()

    df = pd.DataFrame(hourly)
    if "time" in df.columns:
        df["time"] = pd.to_datetime(df["time"], errors="coerce")

    # Ensure we can display *night* icons for hourly cards.
    # Open‑Meteo provides `is_day` in the current weather, but not always in hourly.
    # We derive it from the daily sunrise/sunset times (already requested in the API).
    if "is_day" not in df.columns and "time" in df.columns:
        daily = payload.get("daily") or {}
        if daily and ("sunrise" in daily) and ("sunset" in daily) and ("time" in daily):
            sun = pd.DataFrame(
                {
                    "date": _normalize_dates(daily.get("time")),
                    "sunrise": pd.to_datetime(daily.get("sunrise"), errors="coerce").to_numpy(),
                    "sunset": pd.to_datetime(daily.get("sunset"), errors="coerce").to_numpy(),
                }
            ).dropna(subset=["date"])

            if not sun.empty:
                df["date"] = df["time"].dt.normalize()
                df = df.merge(sun[["date", "sunrise", "sunset"]], on="date", how="left")
                is_day = (df["time"] >= df["sunrise"]) & (df["time"] < df["sunset"])
                df["is_day"] = is_day.astype("Int64")
                df = df.drop(columns=["sunrise", "sunset", "date"], errors="ignore")

    return df


def to_daily_df(payload: Dict[str, Any]) -> pd.DataFrame:
    """Convert Open‑Meteo forecast payload to a daily DataFrame."""

    daily = payload.get("daily") or {}
    if not daily:
        return pd.DataFrame()

    df = pd.DataFrame(daily)
    if "time" in df.columns:
        df["time"] = pd.to_datetime(df["time"], errors="coerce")
    return df


# -----------------------------
# "Climat" helpers (historical)
# -----------------------------


@dataclass(frozen=True)
class TemperatureStats:
    """Basic descriptive statistics for a temperature series."""

    mean: float
    minimum: float
    maximum: float
    std: float


def compute_temperature_stats(series: pd.Series) -> Optional[TemperatureStats]:
    """Compute descriptive stats for a numeric series."""

    s = pd.to_numeric(series, errors="coerce").dropna()
    if s.empty:
        return None

    return TemperatureStats(
        mean=float(s.mean()),
        minimum=float(s.min()),
        maximum=float(s.max()),
        std=float(s.std(ddof=1)) if len(s) > 1 else 0.0,
    )


def monthly_means_from_daily(df_daily: pd.DataFrame) -> pd.DataFrame:
    """Aggregate a daily dataframe to monthly mean temperature.

    Expects at least columns: date, tmax, tmin.
    Returns a dataframe with columns: month, tmean.
    """

    if df_daily.empty:
        return pd.DataFrame()

    df = df_daily.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"])
    if df.empty:
        return pd.DataFrame()

    df["tmean"] = (pd.to_numeric(df["tmax"], errors="coerce") + pd.to_numeric(df["tmin"], errors="coerce")) / 2.0
    df = df.dropna(subset=["tmean"])
    if df.empty:
        return pd.DataFrame()

    df["month"] = df["date"].dt.to_period("M").dt.to_timestamp()
    out = df.groupby("month", as_index=False)["tmean"].mean().sort_values("month").reset_index(drop=True)
    return out