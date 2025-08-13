"""Simple Elforbrug coordinator."""
from datetime import datetime
import logging
from .const import SENSOR_DATA_SCHEMA

_LOGGER = logging.getLogger(__name__)


def get_sensor_by_type(sensor_type):
    """Return the sensor object from SENSOR_DATA_SCHEMA based on the key."""
    return next((sensor for sensor in SENSOR_DATA_SCHEMA if sensor.key == sensor_type), None)


class SensorCoordinator:
    """Coordinator class to handle sensor logic."""

    def __init__(self, sensor_type, client):
        """Initialize the coordinator with sensor type and data client."""
        self._sensor_type = sensor_type
        self._data = client
        self._state = 0.000
        self._extra_state_attributes = {}
        self._data_date = None
        self._unique_id = f"{self._data.get_metering_point()}-{sensor_type}"

    @property
    def name(self):
        sensor = get_sensor_by_type(self._sensor_type)
        return sensor.name if sensor else None

    @property
    def unique_id(self):
        return self._unique_id

    @property
    def state(self):
        return self._state

    @property
    def extra_state_attributes(self):
        return self._extra_state_attributes

    @property
    def unit_of_measurement(self):
        sensor = get_sensor_by_type(self._sensor_type)
        if not sensor:
            return None
        # Brug den enhed, som er valgt i config-flow
        return getattr(self._data, "unit_of_measurement", sensor.native_unit_of_measurement)

    @property
    def icon(self):
        sensor = get_sensor_by_type(self._sensor_type)
        return sensor.icon if sensor else None

    # --- Hjælpere ---

    def _convert(self, value: float) -> float:
        """Konverter via clientens helper (lagrer alt i kWh, konverterer først her)."""
        if value is None:
            return None
        # Brug klientens _convert for ensartethed
        if hasattr(self._data, "_convert"):
            return self._data._convert(value)  # pylint: disable=protected-access
        return round(value, 3)

    def _round_attributes(self, attrs):
        """Rund alle numeriske værdier i attributes til 3 decimaler."""
        rounded = {}
        for k, v in attrs.items():
            if isinstance(v, (int, float)):
                rounded[k] = round(v, 3)
            else:
                rounded[k] = v
        return rounded

    # --- Opdatering ---

    def update(self):
        """Update the sensor's state and attributes."""
        self._data.update_energy()
        self._data_date = self._data.get_data_date()

        # DAILY SENSOR
        if self._sensor_type == "daily":
            current_hour = datetime.now().hour
            hourly_data = [self._data.get_usage_hour(h) for h in range(24)]  # rå kWh
            valid = [d for d in hourly_data if d is not None]
            day_sum_kwh = sum(valid[: current_hour + 1]) if valid else 0.0

            # Konverter sum til valgt enhed og rund til 3 dec.
            self._state = self._convert(day_sum_kwh)

            attrs = {
                "Daily Usage": self._state,  # allerede konverteret
                "Metering Point": self._data.get_metering_point(),
                "Metering date": self._data_date,
            }

            # Tilføj uge-historik (allerede konverteret i get_week_data)
            attrs.update(self._data.get_week_data())

            self._extra_state_attributes = self._round_attributes(attrs)
            _LOGGER.debug("Updated daily state: %.3f, attributes: %s", self._state, self._extra_state_attributes)

        # MONTHLY SENSOR
        elif self._sensor_type == "monthly":
            current_day = datetime.now().day
            total_kwh = 0.0
            for day in range(1, current_day + 1):
                daily_sum_kwh = 0.0
                for h in range(24):
                    val = self._data.get_usage_day(day, h)  # rå kWh
                    if val is not None:
                        daily_sum_kwh += val
                total_kwh += daily_sum_kwh

            self._state = self._convert(total_kwh)

            attrs = {
                "Monthly Usage": self._state,
                "Metering Point": self._data.get_metering_point(),
                "Metering Month": datetime.now().strftime("%B %Y"),
            }
            self._extra_state_attributes = self._round_attributes(attrs)
            _LOGGER.debug("Updated monthly total state: %.3f, attributes: %s", self._state, self._extra_state_attributes)

        # YEAR/TOTAL SENSOR
        elif self._sensor_type == "total":
            total_year_kwh = self._data.get_total_year() or 0.0  # rå kWh
            self._state = self._convert(total_year_kwh)

            attrs = {
                "Yearly Consumption": self._state,
                "Metering Point": self._data.get_metering_point(),
                "Metering date": self._data_date,
            }
            self._extra_state_attributes = self._round_attributes(attrs)
            _LOGGER.debug("Updated total state: %.3f, attributes: %s", self._state, self._extra_state_attributes)

        else:
            raise ValueError(f"Unexpected sensor_type: {self._sensor_type}.")