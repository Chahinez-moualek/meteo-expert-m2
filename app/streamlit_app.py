"""AMSE - Data-Driven Weather Application (Streamlit).

The UI is intentionally designed to look like a modern mobile weather app:
- big hero card with current conditions
- horizontally scrollable hourly forecast
- daily forecast cards
- a 'vigilance' badge
- a radar/satellite map (embedded)

Core requirements covered:
- Python + pandas processing
- API integration (Open‑Meteo)
- containerizable with Docker (see Dockerfile)
"""

from __future__ import annotations

import sys
from pathlib import Path

# Streamlit executes the app with the script directory (./app) on sys.path.
# Our modules live in ../src, so we ensure the project root is importable.
ROOT = Path(__file__).resolve().parents[1]  # .../Software
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import logging
import os
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
from typing import Any, Dict, Optional

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

import plotly.graph_objects as go


# Data layer (collection + cleaning)
from src.data import (
    DEFAULT_FAVORITES_FR,
    Location,
    compute_temperature_stats,
    compute_vigilance,
    fetch_forecast,
    fetch_historical_daily,
    geocode_city,
    monthly_means_from_daily,
    to_daily_df,
    to_hourly_df,
)
from src.weather_codes import code_to_visual


# -----------------------------
# App setup
# -----------------------------

load_dotenv()

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)


st.set_page_config(
    page_title="AMSE Weather",
    page_icon="🌦️",
    layout="wide",
    # IMPORTANT: If the user collapses the sidebar once, hiding Streamlit's header
    # makes it impossible to reopen it. We therefore force the sidebar to start expanded.
    initial_sidebar_state="expanded",
)


@st.cache_data(ttl=60 * 60)
def cached_geocode(query: str, country_code: Optional[str]) -> list[Location]:
    return geocode_city(query, country_code=country_code)


@st.cache_data(ttl=10 * 60)
def cached_forecast(location: Location) -> Dict[str, Any]:
    return fetch_forecast(location)


@st.cache_data(ttl=12 * 60 * 60)
def cached_historical_daily(location: Location, start: date, end: date) -> pd.DataFrame:
    return fetch_historical_daily(location, start=start, end=end)


RAIN_CODES = {51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82}
SNOW_CODES = {71, 73, 75, 77, 85, 86}
FOG_CODES = {45, 48}
STORM_CODES = {95, 96, 99}
CLOUDY_CODES = {2, 3}


def _theme_from_conditions(weather_code: Optional[int], is_day: Optional[int]) -> str:
    """Pick a theme name from current conditions."""

    code = int(weather_code) if weather_code is not None else None
    is_night = is_day is not None and int(is_day) == 0

    if code in STORM_CODES:
        return "storm_night" if is_night else "storm_day"
    if code in SNOW_CODES:
        return "snow_night" if is_night else "snow_day"
    if code in RAIN_CODES:
        return "rain_night" if is_night else "rain_day"
    if code in FOG_CODES:
        return "fog_night" if is_night else "fog_day"
    if code in CLOUDY_CODES:
        return "cloudy_night" if is_night else "cloudy_day"
    return "clear_night" if is_night else "clear_day"



def inject_css(theme: str) -> None:
    # --- Theme palette (cartoon-like backgrounds) ---
    # Goal: mimic a modern mobile weather app (like the screenshot the user shared),
    # with a "sky" background that changes with time + weather and has gentle animations.

    palettes: Dict[str, Dict[str, str]] = {
        "clear_day": {
            "sky_top": "#76c8ff",
            "sky_bottom": "#1f78b9",
            "cloud": "rgba(255,255,255,0.92)",
            "cloud_op": "0.35",
            "stars_op": "0",
            "sun_op": "1",
            "moon_op": "0",
        },
        "cloudy_day": {
            "sky_top": "#8bc6e6",
            "sky_bottom": "#2d6f90",
            "cloud": "rgba(255,255,255,0.94)",
            "cloud_op": "0.70",
            "stars_op": "0",
            "sun_op": "0.55",
            "moon_op": "0",
        },
        "rain_day": {
            "sky_top": "#58798a",
            "sky_bottom": "#1b2b34",
            "cloud": "rgba(185,200,214,0.72)",
            "cloud_op": "0.85",
            "stars_op": "0",
            "sun_op": "0",
            "moon_op": "0",
        },
        "snow_day": {
            "sky_top": "#a9ddff",
            "sky_bottom": "#4e95b8",
            "cloud": "rgba(255,255,255,0.90)",
            "cloud_op": "0.72",
            "stars_op": "0",
            "sun_op": "0.25",
            "moon_op": "0",
        },
        "fog_day": {
            "sky_top": "#7f96a3",
            "sky_bottom": "#2f3e47",
            "cloud": "rgba(240,245,248,0.40)",
            "cloud_op": "0.35",
            "stars_op": "0",
            "sun_op": "0",
            "moon_op": "0",
        },
        "storm_day": {
            "sky_top": "#2b3640",
            "sky_bottom": "#0b1015",
            "cloud": "rgba(150,165,180,0.70)",
            "cloud_op": "0.90",
            "stars_op": "0",
            "sun_op": "0",
            "moon_op": "0",
        },
        "clear_night": {
            "sky_top": "#0b1f47",
            "sky_bottom": "#05070f",
            "cloud": "rgba(255,255,255,0.22)",
            "cloud_op": "0.18",
            "stars_op": "0.62",
            "sun_op": "0",
            "moon_op": "1",
        },
        "cloudy_night": {
            "sky_top": "#0b1f47",
            "sky_bottom": "#05070f",
            "cloud": "rgba(255,255,255,0.26)",
            "cloud_op": "0.45",
            "stars_op": "0.20",
            "sun_op": "0",
            "moon_op": "0.65",
        },
        "rain_night": {
            "sky_top": "#132434",
            "sky_bottom": "#050a12",
            "cloud": "rgba(175,190,205,0.55)",
            "cloud_op": "0.82",
            "stars_op": "0",
            "sun_op": "0",
            "moon_op": "0",
        },
        "snow_night": {
            "sky_top": "#10244c",
            "sky_bottom": "#05070f",
            "cloud": "rgba(255,255,255,0.28)",
            "cloud_op": "0.40",
            "stars_op": "0.35",
            "sun_op": "0",
            "moon_op": "0.7",
        },
        "fog_night": {
            "sky_top": "#1b2b34",
            "sky_bottom": "#050a12",
            "cloud": "rgba(255,255,255,0.18)",
            "cloud_op": "0.20",
            "stars_op": "0",
            "sun_op": "0",
            "moon_op": "0",
        },
        "storm_night": {
            "sky_top": "#0a0f14",
            "sky_bottom": "#020409",
            "cloud": "rgba(170,185,200,0.45)",
            "cloud_op": "0.90",
            "stars_op": "0",
            "sun_op": "0",
            "moon_op": "0",
        },
    }

    p = palettes.get(theme, palettes["clear_day"])

    # Pre-compute a few derived CSS values in Python.
    # (CSS calc() does not reliably support multiplication across browsers.)
    _cloud_base = float(p.get("cloud_op", "0") or "0")
    cloud_op_1 = f"{_cloud_base * 0.95:.3f}"
    cloud_op_2 = f"{_cloud_base * 0.80:.3f}"
    cloud_op_3 = f"{_cloud_base * 0.65:.3f}"
    cloud_op_4 = f"{_cloud_base * 0.55:.3f}"
    cloud_op_5 = f"{_cloud_base * 0.70:.3f}"

    show_rain = "rain" in theme or "storm" in theme
    show_snow = "snow" in theme
    show_fog = "fog" in theme
    show_lightning = "storm" in theme

    sky_classes = ["sky", f"theme-{theme}"]
    if show_rain:
        sky_classes.append("rain-on")
    if show_snow:
        sky_classes.append("snow-on")
    if show_fog:
        sky_classes.append("fog-on")
    if show_lightning:
        sky_classes.append("lightning-on")
    if float(p.get("stars_op", "0") or "0") > 0:
        sky_classes.append("stars-on")
    if float(p.get("sun_op", "0") or "0") > 0:
        sky_classes.append("sun-on")
    if float(p.get("moon_op", "0") or "0") > 0:
        sky_classes.append("moon-on")

    sky_class_attr = " ".join(sky_classes)

    # Insert the decorative sky *behind* the Streamlit UI.
    st.markdown(
        f"""
<div class="{sky_class_attr}" aria-hidden="true">
  <div class="stars"></div>
  <div class="sun"></div>
  <div class="moon"></div>

  <div class="cloud c1"></div>
  <div class="cloud c2"></div>
  <div class="cloud c3"></div>
  <div class="cloud c4"></div>
  <div class="cloud c5"></div>

  <div class="rain"></div>
  <div class="snow"></div>
  <div class="fog"></div>
  <div class="lightning"></div>
</div>

<style>
/* Streamlit chrome:
   - hide the menu + footer
   - KEEP the header so the user can reopen the sidebar if it was collapsed
*/
#MainMenu {{visibility: hidden;}}
footer {{visibility: hidden;}}

/* Keep header (sidebar toggle lives here), but make it visually invisible */
header[data-testid="stHeader"] {{
  background: transparent;
  border-bottom: 0;
}}

/* Ensure body doesn't paint over our animated sky */
html, body {{
  background: transparent !important;
}}

/* Global typography (no external fonts required) */
html, body, [class*="css"], .stMarkdown, .stTextInput, .stSelectbox {{
  font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, "Apple Color Emoji", "Segoe UI Emoji";
}}

/* --- Animated background sky (cartoon style) --- */
.sky {{
  position: fixed;
  inset: 0;
  /* Put the animated sky strictly behind all Streamlit layers (incl. sidebar). */
  z-index: -10;
  pointer-events: none;
  overflow: hidden;
  background: linear-gradient(180deg, {p['sky_top']} 0%, {p['sky_bottom']} 100%);
  background-size: 140% 140%;
  animation: skyDrift 18s ease-in-out infinite alternate;
}}

@keyframes skyDrift {{
  from {{ background-position: 0% 0%; }}
  to   {{ background-position: 100% 100%; }}
}}

/* Subtle vignette */
.sky::after {{
  content: "";
  position: absolute;
  inset: 0;
  background: radial-gradient(circle at 50% 40%, rgba(255,255,255,0.06) 0%, rgba(0,0,0,0.35) 75%);
  opacity: 0.9;
}}

/* Stars layer */
.stars {{
  position: absolute;
  inset: 0;
  display: none;
  opacity: {p['stars_op']};
  background-image:
    radial-gradient(1px 1px at 18px 22px, rgba(255,255,255,0.95) 0 60%, transparent 61%),
    radial-gradient(1px 1px at 90px 120px, rgba(255,255,255,0.85) 0 60%, transparent 61%),
    radial-gradient(2px 2px at 140px 60px, rgba(255,255,255,0.75) 0 60%, transparent 61%),
    radial-gradient(1px 1px at 40px 160px, rgba(255,255,255,0.70) 0 60%, transparent 61%),
    radial-gradient(1px 1px at 180px 170px, rgba(255,255,255,0.65) 0 60%, transparent 61%);
  background-size: 220px 220px;
  background-repeat: repeat;
  animation: starsDrift 90s linear infinite, starsTwinkle 5.5s ease-in-out infinite alternate;
}}

.sky.stars-on .stars {{ display: block; }}

@keyframes starsTwinkle {{
  from {{ filter: brightness(0.9); }}
  to   {{ filter: brightness(1.25); }}
}}

@keyframes starsDrift {{
  from {{ transform: translateX(0px); }}
  to   {{ transform: translateX(44px); }}
}}

/* Sun */
.sun {{
  position: absolute;
  width: 180px;
  height: 180px;
  border-radius: 50%;
  top: 6.5%;
  left: 7.5%;
  opacity: {p['sun_op']};
  display: none;
  background: radial-gradient(circle at 30% 30%, #fff6d6 0%, #ffd36e 35%, #ff9a1a 72%, #ff7a00 100%);
  box-shadow: 0 0 90px rgba(255, 190, 90, 0.42);
  animation: floatSlow 7s ease-in-out infinite;
}}

.sun::after {{
  content: "";
  position: absolute;
  inset: -28px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(255,255,255,0.20) 0%, rgba(255,255,255,0.0) 60%);
  opacity: 0.9;
}}

.sky.sun-on .sun {{ display: block; }}

/* Moon */
.moon {{
  position: absolute;
  width: 160px;
  height: 160px;
  border-radius: 50%;
  top: 7.5%;
  left: 8.5%;
  opacity: {p['moon_op']};
  display: none;
  background: radial-gradient(circle at 35% 35%, #ffffff 0%, #f6f2d8 45%, #d9d4b8 100%);
  box-shadow: 0 0 70px rgba(255,255,255,0.18);
  overflow: hidden;
  animation: floatSlow 8s ease-in-out infinite;
}}

.moon::after {{
  content: "";
  position: absolute;
  width: 160px;
  height: 160px;
  border-radius: 50%;
  top: 10px;
  left: 52px;
  background: linear-gradient(180deg, {p['sky_top']} 0%, {p['sky_bottom']} 100%);
}}

.sky.moon-on .moon {{ display: block; }}

@keyframes floatSlow {{
  0%   {{ transform: translateY(0px); }}
  50%  {{ transform: translateY(-10px); }}
  100% {{ transform: translateY(0px); }}
}}

/* Clouds (several independent elements, cartoon style) */
.cloud {{
  position: absolute;
  left: -38vw;
  top: 18%;
  width: 280px;
  height: 86px;
  background: {p['cloud']};
  border-radius: 999px;
  opacity: {p['cloud_op']};
  filter: blur(0.2px);
  animation: cloudDrift var(--dur, 62s) linear infinite;
  transform: translateX(0) scale(var(--s, 1));
}}

.cloud::before,
.cloud::after {{
  content: "";
  position: absolute;
  background: inherit;
  border-radius: 50%;
}}

.cloud::before {{
  width: 48%;
  height: 150%;
  top: -70%;
  left: 12%;
}}

.cloud::after {{
  width: 58%;
  height: 175%;
  top: -95%;
  left: 42%;
}}

.cloud.c1 {{ top: 18%; --dur: 58s; --s: 1.05; opacity: {cloud_op_1}; }}
.cloud.c2 {{ top: 34%; --dur: 74s; --s: 0.92; opacity: {cloud_op_2}; }}
.cloud.c3 {{ top: 52%; --dur: 82s; --s: 0.78; opacity: {cloud_op_3}; }}
.cloud.c4 {{ top: 14%; --dur: 96s; --s: 0.70; opacity: {cloud_op_4}; }}
.cloud.c5 {{ top: 60%; --dur: 64s; --s: 0.88; opacity: {cloud_op_5}; }}

.cloud.c2 {{ animation-delay: -18s; }}
.cloud.c3 {{ animation-delay: -38s; }}
.cloud.c4 {{ animation-delay: -52s; }}
.cloud.c5 {{ animation-delay: -26s; }}

@keyframes cloudDrift {{
  from {{ transform: translateX(0) translateY(0) scale(var(--s, 1)); }}
  to   {{ transform: translateX(165vw) translateY(-12px) scale(var(--s, 1)); }}
}}

/* Rain */
.rain {{
  position: absolute;
  inset: 0;
  display: none;
  opacity: 0.42;
  background-image: repeating-linear-gradient(-20deg,
    rgba(255,255,255,0.25) 0,
    rgba(255,255,255,0.25) 2px,
    transparent 2px,
    transparent 18px);
  background-size: 340px 340px;
  animation: rainFall 0.75s linear infinite;
}}

.sky.rain-on .rain {{ display: block; }}

@keyframes rainFall {{
  from {{ background-position: 0 0; }}
  to   {{ background-position: -160px 420px; }}
}}

/* Snow */
.snow {{
  position: absolute;
  inset: 0;
  display: none;
  opacity: 0.35;
  background-image: radial-gradient(rgba(255,255,255,0.90) 1.25px, transparent 1.35px);
  background-size: 95px 95px;
  animation: snowFall 12s linear infinite;
}}

.sky.snow-on .snow {{ display: block; }}

@keyframes snowFall {{
  from {{ background-position: 0 0; }}
  to   {{ background-position: 0 420px; }}
}}

/* Fog */
.fog {{
  position: absolute;
  inset: -10% -10% -10% -10%;
  display: none;
  opacity: 0.75;
  background:
    radial-gradient(circle at 25% 60%, rgba(255,255,255,0.22) 0 30%, transparent 60%),
    radial-gradient(circle at 70% 50%, rgba(255,255,255,0.18) 0 35%, transparent 62%),
    radial-gradient(circle at 50% 70%, rgba(255,255,255,0.14) 0 40%, transparent 65%);
  filter: blur(10px);
  animation: fogDrift 12s ease-in-out infinite alternate;
}}

.sky.fog-on .fog {{ display: block; }}

@keyframes fogDrift {{
  from {{ transform: translateX(-10px); }}
  to   {{ transform: translateX(14px); }}
}}

/* Lightning */
.lightning {{
  position: absolute;
  inset: 0;
  display: none;
  background: rgba(255,255,255,0.12);
  opacity: 0;
  animation: lightningFlash 8s linear infinite;
}}

.sky.lightning-on .lightning {{ display: block; }}

@keyframes lightningFlash {{
  0%, 78%, 100% {{ opacity: 0; }}
  80% {{ opacity: 0.35; }}
  81% {{ opacity: 0.00; }}
  83% {{ opacity: 0.48; }}
  84% {{ opacity: 0.00; }}
}}

/* --- Bring content above background --- */
.stApp {{
  background: transparent;
  color: rgba(255,255,255,0.96);
}}

/* --- Bring content above background --- */
[data-testid="stAppViewContainer"] {{
  background: transparent;
  color: rgba(255,255,255,0.96);
}}

/* Sidebar: keep it above everything (defensive z-index),
   but DO NOT override the collapsed transform state.
   Overriding aria-expanded="false" breaks the ability to collapse it. */
section[data-testid="stSidebar"] {{
  position: relative;
  z-index: 9999 !important;
}}

/* Ensure sidebar content can scroll (some custom CSS can accidentally kill it). */
section[data-testid="stSidebar"] > div:first-child {{
  max-height: 100vh !important;
  overflow-y: auto !important;
  overflow-x: hidden !important;
}}

section[data-testid="stSidebar"] [data-testid="stSidebarContent"] {{
  max-height: 100vh !important;
  overflow-y: auto !important;
}}

/* Header (contains the sidebar toggle) should also stay on top */
header[data-testid="stHeader"] {{
  z-index: 99999 !important;
}}

/* Sidebar: dark glass panel */
[data-testid="stSidebar"] > div:first-child {{
  background: rgba(12, 16, 22, 0.66);
  border-right: 1px solid rgba(255,255,255,0.08);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
}}

/* Make the page feel like a mobile app */
section.main > div {{
  padding-top: 1.2rem;
}}

/* Glass cards */
.glass {{
  background: rgba(255, 255, 255, 0.09);
  border: 1px solid rgba(255, 255, 255, 0.14);
  border-radius: 18px;
  padding: 18px 18px;
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  box-shadow: 0 16px 40px rgba(0,0,0,0.18);
  transition: transform 180ms ease, background 180ms ease;
}}

.glass:hover {{
  transform: translateY(-2px);
  background: rgba(255, 255, 255, 0.11);
}}

.hero {{
  padding: 22px 22px;
}}

.city {{
  font-size: 1.05rem;
  letter-spacing: 0.2px;
  opacity: 0.95;
}}

.desc {{
  font-size: 0.95rem;
  opacity: 0.78;
  margin-top: 2px;
}}

.hero-top {{
  display:flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}}

.hero-icon {{
  font-size: 3.1rem;
  animation: floaty 4.5s ease-in-out infinite;
}}

@keyframes floaty {{
  0% {{ transform: translateY(0); }}
  50% {{ transform: translateY(-7px); }}
  100% {{ transform: translateY(0); }}
}}

.hero-temp {{
  font-size: 4.2rem;
  font-weight: 700;
  line-height: 1;
  margin-top: 8px;
}}

.hero-minmax {{
  margin-top: 6px;
  font-size: 0.95rem;
  opacity: 0.8;
}}

/* Hourly scroll */
.hourly-scroll {{
  display:flex;
  gap: 10px;
  overflow-x: auto;
  padding-bottom: 6px;
}}
.hourly-scroll::-webkit-scrollbar {{ height: 7px; }}
.hourly-scroll::-webkit-scrollbar-thumb {{
  background: rgba(255,255,255,0.22);
  border-radius: 999px;
}}

.hour-card {{
  min-width: 86px;
  padding: 12px 10px;
  border-radius: 16px;
  background: rgba(255,255,255,0.09);
  border: 1px solid rgba(255,255,255,0.12);
  text-align: center;
}}
.hour-time {{ font-size: 0.9rem; opacity: 0.82; }}
.hour-icon {{ font-size: 1.5rem; margin: 6px 0; }}
.hour-temp {{ font-size: 1.1rem; font-weight: 650; }}
.hour-pp {{ font-size: 0.78rem; opacity: 0.7; margin-top: 4px; }}

/* Daily list */
.daily-row {{
  display:flex;
  align-items:center;
  justify-content: space-between;
  padding: 10px 4px;
  border-bottom: 1px solid rgba(255,255,255,0.09);
}}
.daily-row:last-child {{ border-bottom: none; }}
.daily-left {{ display:flex; align-items:center; gap: 10px; }}
.daily-day {{ width: 64px; opacity: 0.9; }}
.daily-icon {{ font-size: 1.3rem; }}
.daily-right {{ opacity: 0.92; }}
.daily-min {{ opacity: 0.7; margin-left: 10px; }}

/* Vigilance badge */
.badge {{
  display:inline-block;
  padding: 6px 10px;
  border-radius: 999px;
  font-size: 0.85rem;
  border: 1px solid rgba(255,255,255,0.18);
  background: rgba(255,255,255,0.08);
}}

.v-verte {{ background: rgba(0, 200, 120, 0.18); }}
.v-jaune {{ background: rgba(255, 215, 0, 0.18); }}
.v-orange {{ background: rgba(255, 140, 0, 0.18); }}
.v-rouge {{ background: rgba(255, 70, 70, 0.18); }}

/* Small helper text */
.muted {{ opacity: 0.72; }}

/* Tabs: mobile segmented control (no emojis in the tab titles) */
.stTabs [data-baseweb="tab-list"] {{
  gap: 6px;
}}
.stTabs [data-baseweb="tab"] {{
  height: 40px;
  padding-left: 14px;
  padding-right: 14px;
  border-radius: 999px;
  background: rgba(255,255,255,0.08);
  border: 1px solid rgba(255,255,255,0.12);
}}
.stTabs [aria-selected="true"] {{
  background: rgba(255,255,255,0.16);
  border: 1px solid rgba(255,255,255,0.22);
}}
</style>
""",
        unsafe_allow_html=True,
    )


def _format_day_fr(ts: pd.Timestamp) -> str:
    # Monday=0
    days = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]
    return days[int(ts.dayofweek)]


def _format_hour_fr(ts: pd.Timestamp) -> str:
    return ts.strftime("%Hh")

def _format_day_date_fr(ts: pd.Timestamp) -> str:
    jours = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]
    mois = [
        "janv.", "févr.", "mars", "avr.", "mai", "juin",
        "juil.", "août", "sept.", "oct.", "nov.", "déc."
    ]
    ts = pd.to_datetime(ts)
    return f"{jours[ts.dayofweek]} {ts.day} {mois[ts.month - 1]}"


def _month_label_fr(m: int) -> str:
    mois = ["Jan", "Fév", "Mar", "Avr", "Mai", "Juin", "Juil", "Aoû", "Sep", "Oct", "Nov", "Déc"]
    return mois[m - 1] if 1 <= m <= 12 else str(m)


def _safe_round(x: Any) -> str:
    """Round numeric values for display.

    Returns "–" if the value is missing or not numeric.
    """

    try:
        return str(int(round(float(x))))
    except Exception:
        return "–"
    
def _format_date_fr(d: date) -> str:
    jours = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
    mois = [
        "janvier", "février", "mars", "avril", "mai", "juin",
        "juillet", "août", "septembre", "octobre", "novembre", "décembre",
    ]
    return f"{jours[d.weekday()]} {d.day} {mois[d.month - 1]} {d.year}"



# -----------------------------
# Sidebar (city selection)
# -----------------------------

# Default list (France-first) comes from the data layer.
DEFAULT_FAVORITES = list(DEFAULT_FAVORITES_FR)

if "favorites" not in st.session_state:
    st.session_state.favorites = list(DEFAULT_FAVORITES)

if "city_query" not in st.session_state:
    st.session_state.city_query = st.session_state.favorites[0]

if "reset_favs" not in st.session_state:
    st.session_state.reset_favs = False


def _ask_reset_favorites() -> None:
    st.session_state.reset_favs = True


def _use_favorite_city() -> None:
    st.session_state.city_query = st.session_state.fav_city


def _use_popular_city() -> None:
    st.session_state.city_query = st.session_state.popular_city


with st.sidebar:
    # ⚠️ Reset AVANT de créer les widgets
    if st.session_state.reset_favs:
        st.session_state.favorites = list(DEFAULT_FAVORITES)
        st.session_state.city_query = st.session_state.favorites[0]

        # IMPORTANT: supprimer les clés des widgets pour repartir proprement
        for k in ("fav_city", "popular_city"):
            if k in st.session_state:
                del st.session_state[k]

        st.session_state.reset_favs = False
        st.rerun()

    st.markdown("## Localisation")

    only_fr = st.toggle("France uniquement", value=True)
    country_code = "FR" if only_fr else None

    st.selectbox(
        "Villes en France (rapide)",
        options=DEFAULT_FAVORITES,
        index=0,
        key="popular_city",
        on_change=_use_popular_city,
    )

    city_query = st.text_input("Rechercher une ville", key="city_query")
    geo_results = cached_geocode(city_query, country_code) if city_query else []
    if geo_results:
        labels = [loc.label for loc in geo_results]
        selected_label = st.selectbox("Résultats", labels, index=0)
        location = geo_results[labels.index(selected_label)]
    else:
        # Fallback to Paris coordinates if geocoding fails
        location = Location(
            name=city_query or "Paris",
            country="France",
            latitude=48.8566,
            longitude=2.3522,
            timezone="Europe/Paris",
        )

    st.markdown("---")
    st.markdown("## Favoris")
    st.selectbox(
        "Accès rapide",
        st.session_state.favorites,
        index=0,
        key="fav_city",
        on_change=_use_favorite_city,
    )

    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("Ajouter"):
            name = (city_query or "").strip()
            if name and name not in st.session_state.favorites:
                st.session_state.favorites.insert(0, name)
    with col_b:
        st.button("Réinitialiser", on_click=_ask_reset_favorites)

    st.markdown("---")
    st.caption("Données météo : Open-Meteo (API)\n\nCarte : Windy embed")


# -----------------------------
# Data loading
# -----------------------------

forecast = cached_forecast(location)
current = (forecast.get("current") or {}) if forecast else {}

current_code = current.get("weather_code")
current_is_day = current.get("is_day")
theme = _theme_from_conditions(current_code, current_is_day)
inject_css(theme)

if not forecast:
    st.error("Impossible de récupérer la météo pour le moment. Réessayez.")
    st.stop()


df_hourly = to_hourly_df(forecast)
df_daily = to_daily_df(forecast)
vigilance = compute_vigilance(forecast)


# -----------------------------
# Header
# -----------------------------

visual = code_to_visual(current_code, current_is_day)
tz = ZoneInfo(location.timezone) if getattr(location, "timezone", None) else None
today_local = datetime.now(tz).date() if tz else date.today()
today_str = _format_date_fr(today_local)

st.markdown(
    f"""
<div class="glass hero">
  <div class="hero-top">
    <div>
      <div class="city">{location.label}</div>
      <div class="muted" style="margin-top:2px; font-size:0.95rem;">{today_str}</div>
      <div class="desc">{visual.label_fr}</div>
      <div style="margin-top:10px;">
        <span class="badge v-{vigilance.level}">{vigilance.label}</span>
        <span class="muted" style="margin-left:8px; font-size:0.85rem;">{vigilance.reason}</span>
      </div>
    </div>
    <div class="hero-icon">{visual.icon}</div>
  </div>

  <div class="hero-temp">{_safe_round(current.get('temperature_2m'))}°</div>
  <div class="hero-minmax">
    Ressenti {_safe_round(current.get('apparent_temperature'))}° · Vent {_safe_round(current.get('wind_speed_10m'))} km/h · Rafales {_safe_round(current.get('wind_gusts_10m'))} km/h
  </div>
</div>
""",
    unsafe_allow_html=True,
)


# -----------------------------
# Tabs (like the reference screenshot)
# -----------------------------

tab_today, tab_forecast, tab_map, tab_climate = st.tabs(["Aujourd’hui", "Prévisions", "Carte", "Climat & stats"])


with tab_today:
    st.markdown("### Prochaines heures")

    if df_hourly.empty:
        st.info("Données horaires indisponibles.")
    else:
        now = pd.to_datetime(current.get("time")) if current.get("time") else df_hourly["time"].min()
        df_next = df_hourly[df_hourly["time"] >= now].head(14).copy()

        cards = []
        for _, r in df_next.iterrows():
            icon = code_to_visual(r.get("weather_code"), r.get("is_day")).icon
            cards.append(
                f"""
<div class="hour-card">
  <div class="hour-time">{_format_hour_fr(pd.to_datetime(r['time']))}</div>
  <div class="hour-icon">{icon}</div>
  <div class="hour-temp">{_safe_round(r.get('temperature_2m'))}°</div>
  <div class="hour-pp">Précip. {_safe_round(r.get('precipitation_probability'))}%</div>
</div>
"""
            )

        st.markdown(
            f"""
<div class="glass">
  <div class="hourly-scroll">
    {''.join(cards)}
  </div>
</div>
""",
            unsafe_allow_html=True,
        )

    st.markdown("### Détails")
    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Humidité", f"{_safe_round(current.get('relative_humidity_2m'))}%")
    col2.metric("Précip.", f"{_safe_round(current.get('precipitation'))} mm")
    col3.metric("Direction du vent", f"{_safe_round(current.get('wind_direction_10m'))}°")
    col4.metric("Altitude", f"{_safe_round(forecast.get('elevation'))} m")


with tab_forecast:
    st.markdown("### Prochains jours")
    if df_daily.empty:
        st.info("Données journalières indisponibles.")
    else:
        # Date locale (même logique que la hero card)
        tz = ZoneInfo(location.timezone) if getattr(location, "timezone", None) else None
        today_local = datetime.now(tz).date() if tz else date.today()

        # df_daily["time"] -> normaliser en date
        df_daily2 = df_daily.copy()
        df_daily2["day"] = pd.to_datetime(df_daily2["time"]).dt.date

        # Garder uniquement aujourd'hui et les jours futurs, puis prendre les 7 prochains
        df_daily_next = df_daily2[df_daily2["day"] > today_local].head(7)

        rows = []
        for _, r in df_daily_next.iterrows():
            day = _format_day_date_fr(pd.to_datetime(r["time"]))
            icon = code_to_visual(r.get("weather_code")).icon
            tmax = _safe_round(r.get("temperature_2m_max"))
            tmin = _safe_round(r.get("temperature_2m_min"))
            pmax = _safe_round(r.get("precipitation_probability_max"))
            rows.append(
                f"""
<div class="daily-row">
  <div class="daily-left">
    <div class="daily-day">{day}</div>
    <div class="daily-icon">{icon}</div>
    <div class="muted">Précip. {pmax}%</div>
  </div>
  <div class="daily-right">
    <span>{tmax}°</span>
    <span class="daily-min">{tmin}°</span>
  </div>
</div>
"""
            )


        st.markdown(
            f"""
<div class="glass">
  {''.join(rows)}
</div>
""",
            unsafe_allow_html=True,
        )

        st.markdown("### Température (48h)")
        if not df_hourly.empty:
            now = pd.to_datetime(current.get("time")) if current.get("time") else pd.to_datetime(df_hourly["time"].min())

            df_48 = df_hourly.copy()
            df_48["time"] = pd.to_datetime(df_48["time"])
            df_48 = df_48[df_48["time"] >= now].head(48).copy()

            temp = pd.to_numeric(df_48.get("temperature_2m"), errors="coerce")
            feel = pd.to_numeric(df_48.get("apparent_temperature"), errors="coerce")

            fig = go.Figure()

            fig.add_trace(go.Scatter(
                x=df_48["time"], y=temp,
                mode="lines+markers",
                name="Température (°C)",
                line=dict(color="#00E5FF", width=2),     # <- couleur 1
                marker=dict(color="#00E5FF"),
                hovertemplate="%{x|%a %d %b · %Hh}<br>Température: %{y:.1f}°C<extra></extra>",
            ))

            fig.add_trace(go.Scatter(
                x=df_48["time"], y=feel,
                mode="lines+markers",
                name="Ressenti (°C)",
                line=dict(color="#FFB300", width=2, dash="dash"),  # <- couleur 2
                marker=dict(color="#FFB300"),
                hovertemplate="%{x|%a %d %b · %Hh}<br>Ressenti: %{y:.1f}°C<extra></extra>",
            ))

            fig.add_vline(x=now, line_dash="dot", opacity=0.7)

            fig.update_layout(
                height=360,
                margin=dict(l=10, r=10, t=10, b=10),
                template="plotly_dark",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
                hovermode="x unified",
            )

            fig.update_xaxes(tickformat="%Hh", dtick=3 * 60 * 60 * 1000, showgrid=True)
            fig.update_yaxes(title="°C", showgrid=True, zeroline=False)

            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Données horaires indisponibles.")




with tab_map:
    st.markdown("### Satellite / Radar")

    overlay_label = st.selectbox(
        "Couche",
        ["Satellite", "Radar", "Vent", "Nuages"],
        index=0,
        help="Source : widget Windy",
    )

    overlay_map = {
        "Satellite": "satellite",
        "Radar": "radar",
        "Vent": "wind",
        "Nuages": "clouds",
    }

    overlay = overlay_map[overlay_label]

    zoom = st.slider("Zoom", min_value=3, max_value=11, value=6)

    windy_url = (
        "https://embed.windy.com/embed2.html"
        f"?lat={location.latitude:.4f}&lon={location.longitude:.4f}"
        f"&detailLat={location.latitude:.4f}&detailLon={location.longitude:.4f}"
        f"&width=650&height=450&zoom={zoom}&level=surface&overlay={overlay}"
        "&product=ecmwf&menu=&message=true&marker=true"
    )

    st.components.v1.iframe(windy_url, height=520)
    st.caption("La carte est intégrée via le widget Windy (embed).")



with tab_climate:
    st.markdown("### Analyse rapide")

    # 30 days historical daily for small stats
    end = date.today()
    start = end - timedelta(days=30)
    hist = cached_historical_daily(location, start, end)

    if hist.empty:
        st.info("Historique indisponible pour cette localisation.")
    else:
        hist = hist.copy()
        hist["tmean"] = (pd.to_numeric(hist["tmax"], errors="coerce") + pd.to_numeric(hist["tmin"], errors="coerce")) / 2.0
        stats = compute_temperature_stats(hist["tmean"])

        col1, col2, col3, col4 = st.columns(4)
        if stats:
            col1.metric("Moyenne (30j)", f"{stats.mean:.1f}°C")
            col2.metric("Min (30j)", f"{stats.minimum:.1f}°C")
            col3.metric("Max (30j)", f"{stats.maximum:.1f}°C")
            col4.metric("Volatilité", f"{stats.std:.1f}")

        st.markdown("#### Température moyenne journalière (30 jours)")
        df_plot = hist[["date", "tmean"]].dropna().copy()
        df_plot["date"] = pd.to_datetime(df_plot["date"])
        df_plot["tmean"] = pd.to_numeric(df_plot["tmean"], errors="coerce")
        df_plot = df_plot.dropna().sort_values("date")

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df_plot["date"],
            y=df_plot["tmean"],
            mode="lines+markers",
            name="T° moyenne (°C)",
            line=dict(color="#7C4DFF", width=2),   # <- couleur
            marker=dict(color="#7C4DFF"),
            hovertemplate="%{x|%a %d %b %Y}<br>T° moyenne: %{y:.1f}°C<extra></extra>",
        ))

        fig.update_layout(
            height=360,
            margin=dict(l=10, r=10, t=10, b=10),
            template="plotly_dark",
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        )
        fig.update_xaxes(tickformat="%d %b", showgrid=True)
        fig.update_yaxes(title="°C", showgrid=True, zeroline=False)

        st.plotly_chart(fig, use_container_width=True)



    st.markdown("---")
    st.markdown("### Climat (Open‑Meteo archive)")
    st.caption("Pas de scraping externe : on utilise uniquement l'archive Open‑Meteo pour construire des moyennes mensuelles.")

    end12 = date.today()
    start12 = end12 - timedelta(days=365)
    hist12 = cached_historical_daily(location, start12, end12)
    month12 = monthly_means_from_daily(hist12)

    if month12.empty:
        st.info("Impossible de calculer des moyennes mensuelles (historique indisponible).")
    else:
        st.markdown("#### Moyennes mensuelles (12 derniers mois)")

        m12 = month12.copy()
        m12["tmean"] = pd.to_numeric(m12.get("tmean"), errors="coerce")

        if "month" not in m12.columns:
            st.info("Format mensuel inattendu (colonne 'month' manquante).")
        else:
            # 1) Fabriquer un axe X propre et triable
            if pd.api.types.is_integer_dtype(m12["month"]) or pd.api.types.is_numeric_dtype(m12["month"]):
                # month = 1..12 (pas une vraie date) -> on trace en catégorie
                m12["month_num"] = m12["month"].astype(int)
                m12 = m12.dropna(subset=["tmean", "month_num"]).sort_values("month_num")
                x = m12["month_num"].apply(_month_label_fr)
            else:
                # month est date-like -> on trace en vrai datetime
                m12["month_dt"] = pd.to_datetime(m12["month"], errors="coerce")
                m12 = m12.dropna(subset=["tmean", "month_dt"]).sort_values("month_dt")
                x = m12["month_dt"]

            # 2) Graphe Plotly
            if not m12.empty:
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=x,
                    y=m12["tmean"],
                    mode="lines+markers",
                    name="T° moyenne mensuelle (°C)",
                    line=dict(color="#00C853", width=2),   # <- couleur
                    marker=dict(color="#00C853"),
                    hovertemplate="%{x}<br>T°: %{y:.1f}°C<extra></extra>",
                ))

                fig.update_layout(
                    height=320,
                    margin=dict(l=10, r=10, t=10, b=10),
                    template="plotly_dark",
                    hovermode="x unified",
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
                )
                fig.update_yaxes(title="°C", showgrid=True, zeroline=False)
                fig.update_xaxes(showgrid=True)

                st.plotly_chart(fig, use_container_width=True)



    st.markdown("#### Normales approximatives (5 dernières années)")

    start5y = end - timedelta(days=5 * 365)
    hist5y = cached_historical_daily(location, start5y, end)
    month5y = monthly_means_from_daily(hist5y)

    if month5y.empty:
        st.info("Historique 5 ans indisponible pour cette localisation.")
    else:
        m5 = month5y.copy()
        m5["month"] = pd.to_datetime(m5["month"], errors="coerce")
        m5["tmean"] = pd.to_numeric(m5["tmean"], errors="coerce")
        m5 = m5.dropna(subset=["month", "tmean"]).sort_values("month")

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=m5["month"],
            y=m5["tmean"],
            mode="lines",
            name="Normale approx (°C)",
            line=dict(color="#FF5252", width=2),
            hovertemplate="%{x|%b %Y}<br>T°: %{y:.1f}°C<extra></extra>",
        ))

        fig.update_layout(
            height=320,
            margin=dict(l=10, r=10, t=10, b=10),
            template="plotly_dark",
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        )
        fig.update_xaxes(tickformat="%b\n%Y", dtick="M6", showgrid=True)
        fig.update_yaxes(title="°C", showgrid=True, zeroline=False)

        st.plotly_chart(fig, use_container_width=True)



