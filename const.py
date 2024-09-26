"""Simple Elforbrug Constants integration."""
from datetime import timedelta
from dataclasses import dataclass
from homeassistant.const import UnitOfEnergy

import voluptuous as vol
import logging

_LOGGER = logging.getLogger(__name__)

###############################################################################
# NESSESARY SETTINGS FOR FUNCTIONS

DEFAULT_NAME = "Simple Elforrug"
DOMAIN = "eloverblik"
PLATFORMS = ["sensor"]
MIN_TIME_BETWEEN_UPDATES = timedelta(minutes=60)
CONFIG_SCHEMA = vol.Schema({DOMAIN: vol.Schema({})}, extra=vol.ALLOW_EXTRA)
DATA_SCHEMA = vol.Schema({
    vol.Required("refresh_token", description="Token"): str,
    vol.Required("metering_point", description="Metering Point"): str,
    vol.Optional("unit_of_measurement", default=UnitOfEnergy.KILO_WATT_HOUR): vol.In([UnitOfEnergy.KILO_WATT_HOUR, UnitOfEnergy.MEGA_WATT_HOUR])
})

###############################################################################
# SENSOR DESIGN SCHEMA
@dataclass
class SensorType:
    key: str
    name: str
    entity_registry_enabled_default: bool
    native_unit_of_measurement: str
    icon: str

SENSOR_DATA_SCHEMA = (
    SensorType(
        key="daily",
        name="Simple Elforbrug Daily",
        entity_registry_enabled_default=True,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        icon="mdi:calendar-today",
    ),
    SensorType(
        key="monthly",
        name="Simple Elforbrug Monthly",
        entity_registry_enabled_default=True,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        icon="mdi:calendar-month",
    ),
    SensorType(
        key="total",
        name="Simple Elforbrug Total",
        entity_registry_enabled_default=True,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        icon="mdi:calendar-multiple-check",
    )
)