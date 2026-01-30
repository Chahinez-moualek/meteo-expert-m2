# data/

This folder stores **all datasets used/produced by the app**, as requested by the project guidelines.

- `raw/`: raw API payloads (JSON) fetched from Open‑Meteo (geocoding, forecast).
- `processed/`: cleaned/tabular datasets (CSV) used by the Streamlit UI (hourly/daily/historical summaries).

These files are generated automatically when you run the app.

✅ In this repository, the generated datasets (`data/raw/*` and `data/processed/*`) are **ignored by Git**
to avoid committing large or frequently changing files. Only the folder skeleton (`.gitkeep`) and this
README are tracked.
