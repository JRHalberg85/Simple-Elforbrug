"""Simple Elforbrug init-file."""
import asyncio
import logging
import requests
import json
from datetime import datetime, timedelta

from homeassistant.const import UnitOfEnergy
from homeassistant.util import Throttle
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall

from .pyeloverblik.eloverblik import Eloverblik
from .const import DOMAIN, MIN_TIME_BETWEEN_UPDATES, PLATFORMS

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the Eloverblik component."""
    hass.data[DOMAIN] = {}
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up Eloverblik from a config entry."""
    refresh_token = entry.data["refresh_token"]
    metering_point = entry.data["metering_point"]
    unit_of_measurement = entry.data.get("unit_of_measurement", UnitOfEnergy.KILO_WATT_HOUR)

    eloverblik_instance = HassEloverblik(
        refresh_token=refresh_token,
        metering_point=metering_point,
        unit_of_measurement=unit_of_measurement,
    )
    hass.data[DOMAIN][entry.entry_id] = eloverblik_instance

    # Service: Manuel opdatering
    async def handle_manual_update(call: ServiceCall):
        _LOGGER.info("🔄 Manuel opdatering af Eloverblik-data startet via servicecall")
        await hass.async_add_executor_job(eloverblik_instance.update_energy)
        _LOGGER.info("✅ Manuel opdatering af Eloverblik-data færdig")

    hass.services.async_register(DOMAIN, "update_energy", handle_manual_update)

    # Service: Skift enhed (kWh / MWh)
    async def handle_set_unit(call: ServiceCall):
        unit = call.data.get("unit")
        if unit not in ["kWh", "MWh"]:
            _LOGGER.error("❌ Ugyldig enhed: %s. Tilladte værdier er 'kWh' eller 'MWh'", unit)
            return
        eloverblik_instance.unit_of_measurement = unit
        _LOGGER.info("✅ Enhed ændret til: %s", unit)
        # Opdater data straks
        await hass.async_add_executor_job(eloverblik_instance.update_energy)

    hass.services.async_register(DOMAIN, "set_unit", handle_set_unit)

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
    """
    Holder altid rå data i kWh.
    Konvertering til MWh sker først ved udlæsning (get_week_data / koordinatoren).
    """

    def __init__(self, refresh_token, metering_point, unit_of_measurement):
        self._client = Eloverblik(refresh_token)
        self._metering_point = metering_point
        self.unit_of_measurement = unit_of_measurement  # "kWh" eller "MWh"/UnitOfEnergy
        self._day_data = None        # rå timeserier i kWh (sidste dag)
        self._week_data = {}         # dict: "N days ago" -> dagssum i kWh (rå)
        self._year_data = None       # objekt fra klienten (total i kWh)

    # ---------- Hjælpere ----------

    def _is_mwh(self) -> bool:
        return str(self.unit_of_measurement).lower() == "mwh"

    def _convert(self, value: float) -> float:
        """Konverter til valgt enhed først ved præsentation; rund til 3 dec."""
        if value is None:
            return None
        if self._is_mwh():
            return round(value / 1000.0, 3)
        return round(value, 3)

    # ---------- Offentlige “getter” metoder (returnerer KWh rå, undtagen week der konverteres samlet) ----------

    def get_usage_hour(self, hour):
        """Rå timeværdi i kWh (3 dec). Ingen konvertering her."""
        if self._day_data:
            try:
                return round(self._day_data.get_metering_data(hour), 3)
            except IndexError:
                return 0.0
            except Exception as e:
                _LOGGER.debug("Fejl i get_usage_hour: %s", e)
                return None
        _LOGGER.warning("No day data available.")
        return None

    def get_usage_day(self, day, hour):
        """Rå timeværdi i kWh (samme som get_usage_hour; 'day' er ikke i brug)."""
        return self.get_usage_hour(hour)

    def get_total_year(self):
        """Total for året i kWh (rå)."""
        if self._year_data:
            return round(self._year_data.get_total_metering_data(), 3)
        return None

    def get_data_date(self):
        if self._day_data and hasattr(self._day_data, "data_date"):
            try:
                return self._day_data.data_date.date().strftime("%Y-%m-%d")
            except Exception:
                return None
        _LOGGER.debug("No day data available for get_data_date.")
        return None

    def get_metering_point(self):
        return self._metering_point

    def get_week_data(self):
        """
        Returnér uge-opsummering i VALGT enhed (konverter først her).
        Internt ligger `_week_data` altid i kWh.
        """
        out = {}
        for k, v in self._week_data.items():
            out[k] = self._convert(v) if isinstance(v, (int, float)) else v
        return out

    # ---------- Hent/byg data (kører i kWh) ----------

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update_energy(self):
        try:
            _LOGGER.debug("Starter update_energy for metering point %s", self._metering_point)

            # Hent sidste 8 dages time-data (rå i kWh)
            raw = self._client.get_time_series(
                self._metering_point,
                from_date=datetime.now() - timedelta(days=8),
                to_date=datetime.now(),
                aggregation="Hour",
            )

            if raw.status == 200:
                try:
                    json_response = json.loads(raw.body)
                    parsed = self._client._parse_result(json_response)
                except Exception as e:
                    _LOGGER.exception("Kunne ikke parse time-series JSON: %s", e)
                    parsed = {}

                # Map dato -> timeserieobjekt
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

                    # Byg 7 dages historik (RÅ KWH!)
                    wd = {}
                    for i in range(1, 8):
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

                        # Gem ALTID i kWh (rå); konverter først ved udlæsning
                        wd[f"{i} days ago"] = round(day_sum, 3)

                        # Log både kWh og valgt enhed for gennemsigtighed
                        _LOGGER.debug(
                            "📅 Forbrug %s: %.3f kWh (%.3f %s) på dato %s",
                            f"{i} days ago",
                            round(day_sum, 3),
                            self._convert(day_sum),
                            self.unit_of_measurement,
                            target.isoformat(),
                        )

                    self._week_data = wd

                _LOGGER.debug("Uge-data keys: %s", list(self._week_data.keys()))

            else:
                _LOGGER.warning(
                    "Error from Eloverblik when getting time series: %s - %s",
                    raw.status,
                    getattr(raw, "body", None),
                )
                self._week_data = {}

            # Årsdata (objekt; total fås i kWh via get_total_year)
            year_data = self._client.get_per_month(self._metering_point)
            if year_data.status == 200:
                self._year_data = year_data
                _LOGGER.debug(
                    "✅ Årsdata hentet. Total år: %.3f kWh (%.3f %s)",
                    self._year_data.get_total_metering_data() if self._year_data else 0.0,
                    self._convert(self._year_data.get_total_metering_data() if self._year_data else 0.0),
                    self.unit_of_measurement,
                )
            else:
                _LOGGER.warning(
                    "Error from Eloverblik when getting year data: %s - %s",
                    year_data.status,
                    getattr(year_data, "detailed_status", year_data),
                )

        except requests.exceptions.HTTPError as he:
            message = (
                "Unauthorized error while accessing Eloverblik.dk. Wrong or expired refresh token?"
                if he.response.status_code == 401
                else f"Exception: {he}"
            )
            _LOGGER.warning(message)
        except Exception as e:
            _LOGGER.exception("Exception in update_energy(): %s", e)