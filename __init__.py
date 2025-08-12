"""Simple Elforbrug init-file."""
import asyncio
import logging
import requests
import json
from datetime import datetime, timedelta

from homeassistant.util import Throttle
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from .pyeloverblik.eloverblik import Eloverblik

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

    eloverblik_instance = HassEloverblik(refresh_token, metering_point)
    hass.data[DOMAIN][entry.entry_id] = eloverblik_instance

    # Service
    async def handle_manual_update(call: ServiceCall):
        _LOGGER.info("🔄 Manuel opdatering af Eloverblik-data startet via servicecall")
        await hass.async_add_executor_job(eloverblik_instance.update_energy)
        _LOGGER.info("✅ Manuel opdatering af Eloverblik-data færdig")

    hass.services.async_register(DOMAIN, "update_energy", handle_manual_update)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
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
        self._week_data = {}
        self._year_data = None


    def get_usage_hour(self, hour):
        if self._day_data:
            try:
                return round(self._day_data.get_metering_data(hour), 2)
            except IndexError:
                return 0
            except Exception as e:
                _LOGGER.debug("Fejl i get_usage_hour: %s", e)
                return None
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
            except Exception as e:
                _LOGGER.debug("Fejl i get_usage_day: %s", e)
                return None
        else:
            _LOGGER.warning("No day data available.")
            return None


    def get_total_year(self):
        if self._year_data:
            return round(self._year_data.get_total_metering_data(), 2)
        else:
            return None

    def get_data_date(self):
        if self._day_data and hasattr(self._day_data, "data_date"):
            try:
                return self._day_data.data_date.date().strftime('%Y-%m-%d')
            except Exception:
                return None
        else:
            _LOGGER.debug("No day data available for get_data_date.")
            return None


    def get_metering_point(self):
        return self._metering_point


##############################################################################

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update_energy(self):

        try:
            _LOGGER.debug("Starter update_energy for metering point %s", self._metering_point)

            raw = self._client.get_time_series(
                self._metering_point,
                from_date=datetime.now() - timedelta(days=8),
                to_date=datetime.now(),
                aggregation='Hour'
            )

            if raw.status == 200:
                try:
                    json_response = json.loads(raw.body)
                    parsed = self._client._parse_result(json_response)
                except Exception as e:
                    _LOGGER.exception("Kunne ikke parse time-series JSON: %s", e)
                    parsed = {}

                date_map = {}
                for k, ts in parsed.items():
                    if isinstance(k, datetime):
                        date_map[k.date()] = ts

                if not date_map:
                    _LOGGER.debug("Ingen daglige time-serier fundet i API-respons.")
                    self._week_data = {}
                else:
                    last_date = max(date_map.keys())
                    self._day_data = date_map.get(last_date)

                    wd = {}
                    for i in range(1, 8):  # 1..7
                        target = last_date - timedelta(days=i)
                        ts = date_map.get(target)
                        if ts is None:
                            wd[f"{i} days ago"] = None
                            _LOGGER.debug("Ingen data for %s (target=%s)", f"{i} days ago", target.isoformat())
                            continue

                        day_sum = 0.0
                        for h in range(24):
                            try:
                                val = ts.get_metering_data(h)
                            except Exception:
                                val = None
                            if val is None:
                                continue
                            day_sum += float(val)
                        wd[f"{i} days ago"] = round(day_sum, 3)
                        _LOGGER.debug("📅 Forbrug %s: %.3f kWh (dato: %s)", f"{i} days ago", day_sum, target.isoformat())

                    self._week_data = wd

                _LOGGER.debug("Uge-data keys: %s", list(self._week_data.keys()))

            else:
                _LOGGER.warning("Error from Eloverblik when getting time series: %s - %s", raw.status, getattr(raw, "body", None))
                self._week_data = {}

            year_data = self._client.get_per_month(self._metering_point)
            if year_data.status == 200:
                self._year_data = year_data
                _LOGGER.debug("✅ Årsdata hentet. Total år: %.2f kWh", self._year_data.get_total_metering_data() if self._year_data else 0)
            else:
                _LOGGER.warning("Error from Eloverblik when getting year data: %s - %s", year_data.status, getattr(year_data, "detailed_status", year_data))

        except requests.exceptions.HTTPError as he:
            message = "Unauthorized error while accessing Eloverblik.dk. Wrong or expired refresh token?" if he.response.status_code == 401 else f"Exception: {he}"
            _LOGGER.warning(message)
        except Exception as e:
            _LOGGER.exception("Exception in update_energy(): %s", e)


    