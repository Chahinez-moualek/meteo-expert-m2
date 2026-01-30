"""A simple 'vigilance' indicator.

⚠️ Important: this is *not* an official Météo‑France vigilance product.

The goal is to provide a pedagogical 'danger level' computed from forecast
variables (wind gusts, precipitation probability, temperature extremes).

This is useful in a student project to demonstrate:
- feature engineering / business logic on top of raw API data
- a UI element similar to the reference screenshot.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class Vigilance:
    level: str  # "verte", "jaune", "orange", "rouge"
    label: str
    reason: str


def compute_vigilance(forecast: Dict[str, Any]) -> Vigilance:
    """Compute a basic vigilance level from Open‑Meteo forecast payload."""

    daily = forecast.get("daily") or {}

    gusts = _safe_max(daily.get("wind_gusts_10m_max"))
    pprob = _safe_max(daily.get("precipitation_probability_max"))
    tmax = _safe_max(daily.get("temperature_2m_max"))
    tmin = _safe_min(daily.get("temperature_2m_min"))

    # ---- Rules of thumb (can be tweaked) ----
    if gusts is not None and gusts >= 90:
        return Vigilance("rouge", "Vigilance rouge", f"Rafales très fortes ({gusts:.0f} km/h)")
    if tmax is not None and tmax >= 40:
        return Vigilance("rouge", "Vigilance rouge", f"Chaleur extrême (max {tmax:.0f}°C)")

    if gusts is not None and gusts >= 70:
        return Vigilance("orange", "Vigilance orange", f"Rafales fortes ({gusts:.0f} km/h)")
    if pprob is not None and pprob >= 85:
        return Vigilance("orange", "Vigilance orange", f"Risque de pluie très élevé ({pprob:.0f}%)")
    if tmin is not None and tmin <= -7:
        return Vigilance("orange", "Vigilance orange", f"Froid marqué (min {tmin:.0f}°C)")

    if gusts is not None and gusts >= 55:
        return Vigilance("jaune", "Vigilance jaune", f"Rafales modérées ({gusts:.0f} km/h)")
    if pprob is not None and pprob >= 60:
        return Vigilance("jaune", "Vigilance jaune", f"Risque de pluie ({pprob:.0f}%)")
    if tmax is not None and tmax >= 32:
        return Vigilance("jaune", "Vigilance jaune", f"Chaud (max {tmax:.0f}°C)")

    return Vigilance("verte", "Vigilance verte", "Pas de phénomène dangereux détecté")


def _safe_max(values: Optional[list[Any]]) -> Optional[float]:
    if not values:
        return None
    clean = [v for v in values if v is not None]
    return float(max(clean)) if clean else None


def _safe_min(values: Optional[list[Any]]) -> Optional[float]:
    if not values:
        return None
    clean = [v for v in values if v is not None]
    return float(min(clean)) if clean else None
