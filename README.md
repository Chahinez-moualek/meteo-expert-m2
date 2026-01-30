# AMSE – Data-Driven Weather App (M2 Software)

**GitHub repository (public):** https://github.com/Chahinez-moualek/meteo-expert-m2

This repository contains a **data-driven weather application** built with:
- **Python 3.11+**
- **pandas** (data manipulation)
- **Streamlit** (UI)
- **Docker** (containerization)

The app is designed to look like a modern **mobile weather app**:
- big hero card (current conditions)
- hourly scroll & daily forecast cards
- embedded radar/satellite map
- **dynamic animated background** (day/night, clouds/rain/snow/fog)

It also ships with a curated list of **French cities** and an option to restrict geocoding to France.

## Group members

- Member 1: Anouar Mecheri
- Member 2: Chahineze Moualek
- Member 3: Asma Belatel

## Data sources

- **Weather forecast & historical data:** Open‑Meteo (forecast + archive APIs)
- **Map:** Windy embedded widget (radar/satellite)

## Project structure

```
Software/
├── app/
│   └── streamlit_app.py          # Streamlit UI
├── src/
│   ├── data.py                   # data collection + cleaning + persistence into ./data
│   ├── open_meteo_api.py         # Open‑Meteo API wrapper (forecast + archive + geocoding)
│   ├── weather_codes.py          # WMO code -> (label, icon) with day/night variants
│   ├── vigilance.py              # computed "vigilance" badge (non-official)
│   └── http_client.py            # requests session + retries
├── data/
│   ├── raw/                      # generated API payloads (JSON)  -> ignored by git
│   ├── processed/                # generated tables (CSV)        -> ignored by git
│   └── README.md
├── requirements.txt
├── Dockerfile
├── .gitignore
├── .dockerignore
```

## Run locally (without Docker)

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

streamlit run app/streamlit_app.py
```

## Run with Docker

Build the image:

```bash
docker build -t projet-meteo-m2 .
```

Run the container (no .env required):

```bash
docker run --rm -p 8501:8501 projet-meteo-m2
```

Open:

http://localhost:8501
