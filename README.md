# Limburg.net Home Assistant Integration

Custom Home Assistant integration that reads Limburg.net CSV exports for waste pickup schedules and exposes sensors.

## Features
- Config Flow: choose a CSV URL/local path or upload a CSV during setup.
- Sensors:
  - Next waste pickup: shows "<type> on <date>" with attributes for date/type/source.
  - Per waste type: Huisvuil, Keukenafval, Tuinafval, Textiel, PMD, Papier & Karton; state is the next date for that type, attributes include upcoming dates.
- CSV parsing: expects columns `Datum, Ophaling, Verwijderd, Reden`; only future pickups are kept.

## Installation (HACS)
1. In HACS → Integrations → ⋮ → Custom repositories.
2. Add this repository URL as type **Integration**.
3. Find **Limburg.net** in HACS, install, and restart Home Assistant.

## Configuration
1. Settings → Devices & Services → Add Integration → search for **Limburg.net**.
2. Choose source type:
   - **URL/Path**: enter a CSV URL (http/https) or local file path.
   - **CSV upload**: upload a Limburg.net CSV export directly.
3. Finish to create the sensors.

## Notes
- Supported waste types: Huisvuil, Tuinafval, Keukenafval, Textiel, PMD, Papier & Karton.
- Update interval defaults to 12 hours.
- If dates are not detected, check delimiter (; or ,) and date format (YYYY-MM-DD, DD/MM/YYYY, or DD-MM-YYYY).

## Development
- Coordinator fetch/parse logic: `custom_components/limburgnet/__init__.py`
- Config flow: `custom_components/limburgnet/config_flow.py`
- Sensors: `custom_components/limburgnet/sensor.py`
