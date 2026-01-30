"""Mapping between Open‑Meteo/WMO weather codes and UI labels.

Open‑Meteo uses WMO weather interpretation codes ("weather_code").

We map them to a short French label and an icon for the UI.

Important UX detail:
- some icons should change between day and night (e.g. sun -> moon)
- Open‑Meteo provides `is_day` for the current weather and we derive it for
  hourly forecasts from sunrise/sunset.

The mapping below is intentionally "small but useful" for a student project.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WeatherVisual:
    label_fr: str
    icon: str


_DEFAULT = ("Inconnu", "❓", None, None)


# code -> (label_day, icon_day, label_night, icon_night)
#
# UX goal for this project:
# - At night, we still want a visible "night" cue (moon) even when the weather
#   is cloudy/rainy/snowy/etc.
# - We therefore provide explicit *night variants* for most codes.
_CODE_MAP: dict[int, tuple[str, str, str | None, str | None]] = {
    0: ("Ciel dégagé", "☀️", "Nuit claire", "🌙"),
    1: ("Plutôt dégagé", "🌤️", "Nuit plutôt dégagée", "🌙"),
    2: ("Partiellement nuageux", "⛅", "Nuit partiellement nuageuse", "🌙☁️"),
    3: ("Couvert", "☁️", "Couvert (nuit)", "🌙☁️"),
    45: ("Brouillard", "🌫️", "Brouillard (nuit)", "🌙🌫️"),
    48: ("Brouillard givrant", "🌫️", "Brouillard givrant (nuit)", "🌙🌫️"),
    51: ("Bruine faible", "🌦️", "Bruine faible (nuit)", "🌙🌦️"),
    53: ("Bruine modérée", "🌦️", "Bruine modérée (nuit)", "🌙🌦️"),
    55: ("Bruine forte", "🌧️", "Bruine forte (nuit)", "🌙🌧️"),
    56: ("Bruine verglaçante faible", "🌧️", "Bruine verglaçante faible (nuit)", "🌙🌧️"),
    57: ("Bruine verglaçante forte", "🌧️", "Bruine verglaçante forte (nuit)", "🌙🌧️"),
    61: ("Pluie faible", "🌧️", "Pluie faible (nuit)", "🌙🌧️"),
    63: ("Pluie modérée", "🌧️", "Pluie modérée (nuit)", "🌙🌧️"),
    65: ("Pluie forte", "🌧️", "Pluie forte (nuit)", "🌙🌧️"),
    66: ("Pluie verglaçante faible", "🌧️", "Pluie verglaçante faible (nuit)", "🌙🌧️"),
    67: ("Pluie verglaçante forte", "🌧️", "Pluie verglaçante forte (nuit)", "🌙🌧️"),
    71: ("Neige faible", "🌨️", "Neige faible (nuit)", "🌙🌨️"),
    73: ("Neige modérée", "🌨️", "Neige modérée (nuit)", "🌙🌨️"),
    75: ("Neige forte", "❄️", "Neige forte (nuit)", "🌙❄️"),
    77: ("Grains de neige", "❄️", "Grains de neige (nuit)", "🌙❄️"),
    80: ("Averses faibles", "🌦️", "Averses faibles (nuit)", "🌙🌦️"),
    81: ("Averses modérées", "🌧️", "Averses modérées (nuit)", "🌙🌧️"),
    82: ("Averses fortes", "⛈️", "Averses fortes (nuit)", "🌙⛈️"),
    85: ("Averses de neige faibles", "🌨️", "Averses de neige faibles (nuit)", "🌙🌨️"),
    86: ("Averses de neige fortes", "❄️", "Averses de neige fortes (nuit)", "🌙❄️"),
    95: ("Orage", "⛈️", "Orage (nuit)", "🌙⛈️"),
    96: ("Orage + grêle", "⛈️", "Orage + grêle (nuit)", "🌙⛈️"),
    99: ("Orage + forte grêle", "⛈️", "Orage + forte grêle (nuit)", "🌙⛈️"),
}


def code_to_visual(code: int | None, is_day: int | bool | None = None) -> WeatherVisual:
    """Convert a WMO weather code to a UI visual (label + icon).

    Args:
        code: WMO weather code (Open‑Meteo `weather_code`).
        is_day: 1/True for day, 0/False for night. If None, uses day icon.
    """

    if code is None:
        label_day, icon_day, label_night, icon_night = _DEFAULT
    else:
        label_day, icon_day, label_night, icon_night = _CODE_MAP.get(int(code), _DEFAULT)

    night = False
    if is_day is not None:
        try:
            night = int(is_day) == 0
        except Exception:
            night = False

    label = label_night if (night and label_night) else label_day
    icon = icon_night if (night and icon_night) else icon_day
    return WeatherVisual(label_fr=label, icon=icon)
