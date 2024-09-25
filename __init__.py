"""Simple Elforbrug init-file."""
import asyncio
import logging
#import json
#from datetime import timedelta
import requests
#import voluptuous as vol
from homeassistant.util import Throttle
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from pyeloverblik.eloverblik import Eloverblik

from .const import DOMAIN, MIN_TIME_BETWEEN_UPDATES, PLATFORMS, CONFIG_SCHEMA

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the Eloverblik component."""
    hass.data[DOMAIN] = {}
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up Eloverblik from a config entry."""
    refresh_token = entry.data['refresh_token']
    metering_point = entry.data['metering_point']
    
    hass.data[DOMAIN][entry.entry_id] = HassEloverblik(refresh_token, metering_point)

    for component in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, component)
        )

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, component)
                for component in PLATFORMS
            ]
        )
    )
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok

class HassEloverblik:
    def __init__(self, refresh_token, metering_point):
        self._client = Eloverblik(refresh_token)
        self._metering_point = metering_point

        self._day_data = None
        self._year_data = None

    def get_total_year(self):
        if self._year_data:
            return round(self._year_data.get_total_metering_data(), 2)
        else:
            return None

    def get_usage_hour(self, hour):
        if self._day_data:
            try:
                return round(self._day_data.get_metering_data(hour), 2)
            except IndexError:
                return 0
        else:
            _LOGGER.warning("No day data available.")
            return None
        
    def get_usage_day(self, day, hour):
        """Return the energy usage for a specific day and hour."""
        if self._day_data:
            try:
                return round(self._day_data.get_metering_data(hour), 2)
            except IndexError:
                return 0
        else:
            _LOGGER.warning("No day data available.")
            return None

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update_energy(self):
        try: 
            day_data = self._client.get_latest(self._metering_point)
            if day_data.status == 200:
                self._day_data = day_data
            else:
                _LOGGER.warning(f"Error from Eloverblik when getting day data: {day_data.status} - {day_data.detailed_status}")

            year_data = self._client.get_per_month(self._metering_point)
            if year_data.status == 200:
                self._year_data = year_data
            else:
                _LOGGER.warning(f"Error from Eloverblik when getting year data: {year_data.status} - {year_data.detailed_status}")
        except requests.exceptions.HTTPError as he:
            message = f"Unauthorized error while accessing Eloverblik.dk. Wrong or expired refresh token?" if he.response.status_code == 401 else f"Exception: {he}"
            _LOGGER.warning(message)
        except Exception as e: 
            _LOGGER.warning(f"Exception: {e}")

    def get_data_date(self):
        if self._day_data:
            return self._day_data.data_date.date().strftime('%Y-%m-%d')
        else:
            _LOGGER.warning("No day data available.")
            return None

    def get_metering_point(self):
        return self._metering_point
