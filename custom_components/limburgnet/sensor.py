"""Sensor platform for Limburg.net waste pickup."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, WASTE_TYPES
from . import LimburgNetCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Limburg.net sensors based on a config entry."""
    coordinator: LimburgNetCoordinator = hass.data[DOMAIN][entry.entry_id]
    sensors: list[SensorEntity] = [
        LimburgNetNextPickupSensor(
            coordinator=coordinator,
            entry_id=entry.entry_id,
            name="Next waste pickup",
        )
    ]

    for waste_type in sorted(WASTE_TYPES):
        sensors.append(
            LimburgNetWasteTypeSensor(
                coordinator=coordinator,
                entry_id=entry.entry_id,
                waste_type=waste_type,
            )
        )

    async_add_entities(sensors)


class LimburgNetNextPickupSensor(CoordinatorEntity[LimburgNetCoordinator], SensorEntity):
    """Representation of the next waste pickup sensor."""

    _attr_icon = "mdi:delete-variant"

    def __init__(
        self,
        coordinator: LimburgNetCoordinator,
        entry_id: str,
        name: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_name = name
        self._attr_unique_id = f"{entry_id}_next_pickup"

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        # Trigger state update when the coordinator refreshes.
        self.async_write_ha_state()

    @property
    def native_value(self) -> str | None:
        """Return the next pickup description."""
        next_pickup = self._next_pickup
        if not next_pickup:
            return None
        waste_type = next_pickup.get("waste_type")
        pickup_date = next_pickup.get("date")
        if waste_type and pickup_date:
            try:
                formatted_date = datetime.fromisoformat(pickup_date).date().isoformat()
            except ValueError:
                formatted_date = pickup_date
            return f"{waste_type} on {formatted_date}"
        return waste_type or None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra attributes."""
        next_pickup = self._next_pickup or {}
        return {
            "pickup_date": next_pickup.get("date"),
            "waste_type": next_pickup.get("waste_type"),
            "source": self.coordinator.data.get("source_url"),
        }

    @property
    def _next_pickup(self) -> dict[str, Any] | None:
        """Return next pickup from coordinator data."""
        return self.coordinator.data.get("next_pickup")


class LimburgNetWasteTypeSensor(
    CoordinatorEntity[LimburgNetCoordinator], SensorEntity
):
    """Sensor representing the next pickup date for a specific waste type."""

    _attr_icon = "mdi:calendar-range"

    def __init__(
        self,
        coordinator: LimburgNetCoordinator,
        entry_id: str,
        waste_type: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._waste_type = waste_type
        self._attr_name = f"{waste_type} pickup"
        uid_type = waste_type.lower().replace(" ", "_").replace("&", "and")
        self._attr_unique_id = f"{entry_id}_{uid_type}"

    @property
    def native_value(self) -> str | None:
        """Return the next pickup date for this waste type."""
        pickup = self._next_pickup_for_type
        return pickup.get("date") if pickup else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra attributes for this waste type."""
        pickup = self._next_pickup_for_type or {}
        upcoming = [
            p.get("date")
            for p in self.coordinator.data.get("pickups", [])
            if p.get("waste_type") == self._waste_type
        ]
        return {
            "waste_type": self._waste_type,
            "next_pickup_date": pickup.get("date"),
            "source": self.coordinator.data.get("source_url"),
            "upcoming_dates": upcoming,
        }

    @property
    def _next_pickup_for_type(self) -> dict[str, Any] | None:
        """Return the next pickup for this waste type."""
        for item in self.coordinator.data.get("pickups", []):
            if item.get("waste_type") == self._waste_type:
                return item
        return None
