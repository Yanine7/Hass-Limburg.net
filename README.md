# Limburg.net Home Assistant Integration

Custom integration that reads Limburg.net CSV exports for waste pickup schedules and exposes sensors in Home Assistant.

## Features
- Config Flow: choose a CSV URL/local path _or_ upload a CSV during setup.
- Sensors:
  - `Next waste pickup`: shows “<type> on <date>” with attributes for date/type/source.
  - Per waste type: `Huisvuil pickup`, `Keukenafval pickup`, `Tuinafval pickup`, `Textiel pickup`, `PMD pickup`, `Papier & Karton pickup`; state is the next date for that type, with attributes for upcoming dates.
- CSV parsing: expects columns `Datum, Ophaling, Verwijderd, Reden`; only future pickups are kept.

## Installation (HACS)
1. In HACS → Integrations → ⋮ → Custom repositories.
2. Add this repository URL as type **Integration**.
3. Find “Limburg.net” in HACS, install, and restart Home Assistant.

## Configuration
1. Settings → Devices & Services → Add Integration → “Limburg.net”.
2. Choose source type:
   - **URL/Path**: enter a CSV URL (http/https) or local file path.
   - **CSV upload**: upload a Limburg.net CSV export directly.
3. Finish to create sensors.

## Notes
- Supported waste types: Huisvuil, Tuinafval, Keukenafval, Textiel, PMD, Papier & Karton.
- Update interval defaults to 12 hours.
- If dates aren’t detected, verify the CSV delimiter (; or ,) and date format (YYYY-MM-DD, DD/MM/YYYY, or DD-MM-YYYY).

## Development
- Coordinator fetch/parse logic: `custom_components/limburgnet/__init__.py`.
- Config flow steps: `config_flow.py`.
- Sensors: `sensor.py`.

---

## Disclaimer

This project is not affiliated with, endorsed by, or officially connected to Limburg.net.  
Limburg.net is a registered trademark of its respective owner.

---

Contributions and suggestions are welcome.

---

## License

MIT License
