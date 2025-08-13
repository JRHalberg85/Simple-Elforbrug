"""Simpelt Elforbrug sensorer"""

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN, SENSOR_DATA_SCHEMA
from .coordinator import SensorCoordinator

import logging
_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, config: ConfigEntry, async_add_entities):
    """Set up the sensor platform."""
    eloverblik = hass.data[DOMAIN][config.entry_id]
    sensors = [Elforbrug(sensor.key, eloverblik) for sensor in SENSOR_DATA_SCHEMA]
    async_add_entities(sensors)


class Elforbrug(RestoreEntity):
    """Representation of an energy sensor."""

    def __init__(self, sensor_type, client):
        """Initialize the sensor."""
        self.coordinator = SensorCoordinator(sensor_type, client)
        self._state = None

    async def async_added_to_hass(self):
        """Restore last state on startup."""
        last_state = await self.async_get_last_state()
        if last_state and last_state.state not in (None, "unknown", "unavailable"):
            try:
                self._state = round(float(last_state.state), 3)
            except ValueError:
                self._state = None

    @property
    def name(self):
        return self.coordinator.name

    @property
    def unique_id(self):
        return self.coordinator.unique_id

    @property
    def state(self):
        return round(self._state or self.coordinator.state, 3)

    @property
    def extra_state_attributes(self):
        return self.coordinator.extra_state_attributes

    @property
    def unit_of_measurement(self):
        return self.coordinator.unit_of_measurement

    @property
    def icon(self):
        return self.coordinator.icon

    def update(self):
        self.coordinator.update()
        self._state = self.coordinator.state