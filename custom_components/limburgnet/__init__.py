"""Limburg.net custom integration for Home Assistant."""

from __future__ import annotations

import csv
import io
import logging
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import (
    CONF_CSV_CONTENT,
    CONF_SOURCE_TYPE,
    CONF_SOURCE_URL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    PLATFORMS,
    SOURCE_TYPE_UPLOAD,
    SOURCE_TYPE_URL,
    WASTE_TYPES,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the integration from configuration.yaml (not used)."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Limburg.net from a config entry."""
    coordinator = LimburgNetCoordinator(
        hass=hass,
        source_url=entry.data.get(CONF_SOURCE_URL),
        source_type=entry.data.get(CONF_SOURCE_TYPE),
        csv_content=entry.data.get(CONF_CSV_CONTENT),
        update_interval=DEFAULT_SCAN_INTERVAL,
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok and entry.entry_id in hass.data.get(DOMAIN, {}):
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


class LimburgNetCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator for fetching Limburg.net pickup data."""

    def __init__(
        self,
        hass: HomeAssistant,
        source_url: str | None,
        source_type: str | None,
        csv_content: str | None,
        update_interval: timedelta,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name="Limburg.net waste pickup",
            update_interval=update_interval,
        )
        self._source_url = source_url
        self._source_type = source_type or SOURCE_TYPE_URL
        self._csv_content = csv_content

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from Limburg.net CSV endpoint."""
        try:
            return await self._fetch_pickup_data()
        except Exception as err:  # pylint: disable=broad-except
            raise UpdateFailed(f"Error updating Limburg.net data: {err}") from err

    async def _fetch_pickup_data(self) -> dict[str, Any]:
        """Download and parse pickup data.

        CSV columns: Datum, Ophaling, Verwijderd, Reden.
        """
        if self._source_type == SOURCE_TYPE_UPLOAD:
            _LOGGER.debug("Fetching Limburg.net pickup data from uploaded CSV")
        else:
            _LOGGER.debug("Fetching Limburg.net pickup data from %s", self._source_url)
        content = await self._load_csv()
        pickups = self._parse_csv(content)

        today = dt_util.now().date()
        upcoming_pickups = [
            item for item in pickups if item.get("date_obj") and item["date_obj"] >= today
        ]
        next_pickup = (
            min(upcoming_pickups, key=lambda item: item["date_obj"])
            if upcoming_pickups
            else None
        )

        return {
            "source_url": self._source_url,
            "next_pickup": _clean_pickup(next_pickup),
            "pickups": [_clean_pickup(item) for item in upcoming_pickups],
        }

    async def _load_csv(self) -> str:
        """Load CSV content from a URL or local file."""
        if self._source_type == SOURCE_TYPE_UPLOAD and self._csv_content:
            return self._csv_content

        if not self._source_url:
            raise HomeAssistantError("No CSV source configured.")

        parsed = urlparse(self._source_url)
        if parsed.scheme in ("http", "https"):
            session = async_get_clientsession(self.hass)
            async with session.get(self._source_url) as resp:
                if resp.status != 200:
                    raise HomeAssistantError(
                        f"Failed to download CSV (status {resp.status})"
                    )
                return await resp.text()

        # Treat as local file path
        path = Path(self.hass.config.path(self._source_url))
        try:
            return await self.hass.async_add_executor_job(
                path.read_text, "utf-8"
            )
        except FileNotFoundError as err:
            raise HomeAssistantError(f"CSV file not found: {path}") from err

    def _parse_csv(self, content: str) -> list[dict[str, Any]]:
        """Parse Limburg.net CSV content into structured pickups."""
        if not content:
            return []

        # Detect delimiter to handle common comma or semicolon separated files.
        try:
            dialect = csv.Sniffer().sniff(content.splitlines()[0])
        except csv.Error:
            dialect = csv.excel
            dialect.delimiter = ";"

        reader = csv.DictReader(io.StringIO(content), dialect=dialect)

        pickups: list[dict[str, Any]] = []
        for row in reader:
            date_str = row.get("Datum") or ""
            waste_type = (row.get("Ophaling") or "").strip()
            date_obj = _parse_date(date_str)

            if waste_type not in WASTE_TYPES:
                _LOGGER.debug("Skipping unknown waste type: %s", waste_type)
                continue

            pickups.append(
                {
                    "date": date_obj.isoformat() if date_obj else date_str,
                    "date_obj": date_obj,
                    "waste_type": waste_type,
                }
            )

        pickups.sort(key=lambda item: item["date_obj"] or date.min)
        return pickups


def _parse_date(value: str) -> date | None:
    """Parse a date string into a date object."""
    value = value.strip()
    if not value:
        return None

    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue

    _LOGGER.debug("Unable to parse date: %s", value)
    return None


def _clean_pickup(item: dict[str, Any] | None) -> dict[str, Any] | None:
    """Remove internal fields and return public pickup dict."""
    if not item:
        return None
    return {
        "date": item.get("date"),
        "waste_type": item.get("waste_type"),
    }
