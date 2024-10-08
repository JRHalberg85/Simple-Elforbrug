"""Simpelt Elforbrug sensorer"""
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity

from .const import DOMAIN, SENSOR_DATA_SCHEMA
from .coordinator import SensorCoordinator


import logging
_LOGGER = logging.getLogger(__name__)

###############################################################################
# Async setup for Elforbrug Sensors

async def async_setup_entry(
    hass: HomeAssistant, 
    config: ConfigEntry, 
    async_add_entities
    ):
    
    """Set up the sensor platform."""
    eloverblik = hass.data[DOMAIN][config.entry_id]

    sensors = [
        Elforbrug(sensor.key, eloverblik) 
        for sensor 
        in SENSOR_DATA_SCHEMA
    ]

    async_add_entities(sensors)

#############################################################################
# Simple Elforbrug Sensors

class Elforbrug(Entity):
    """Representation of an energy sensor."""

    def __init__(self, sensor_type, client):
        """Initialize the sensor."""
        self.coordinator = SensorCoordinator(sensor_type, client)

    @property
    def name(self):
        """Return the name of the sensor."""
        return self.coordinator.name

    @property
    def unique_id(self):
        """Return the unique id of the sensor."""
        return self.coordinator.unique_id

    @property
    def state(self):
        """Return the state of the sensor."""
        return self.coordinator.state

    @property
    def extra_state_attributes(self):
        """Return state attributes."""
        return self.coordinator.extra_state_attributes

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return self.coordinator.unit_of_measurement
    
    @property
    def icon(self):
        """Return the icon of the sensor."""
        return self.coordinator.icon

    def update(self):
        """Update the sensor's state."""
        self.coordinator.update()