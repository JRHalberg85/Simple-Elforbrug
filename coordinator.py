"""Simple Elforbrug coordinator."""
from datetime import datetime
from .const import SENSOR_DATA_SCHEMA
import logging

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
        self._state = 0
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
        return sensor.native_unit_of_measurement if sensor else None

    @property
    def icon(self):
        sensor = get_sensor_by_type(self._sensor_type)
        return sensor.icon if sensor else None

    def update(self):
        """Update the sensor's state and attributes."""

        self._data.update_energy()
        self._data_date = self._data.get_data_date()

        # DAILY SENSOR
        if self._sensor_type == 'daily':
            current_hour = datetime.now().hour
            hourly_data = [self._data.get_usage_hour(h) for h in range(24)]
            valid_hourly_data = [d for d in hourly_data if d is not None]
            self._state = sum(valid_hourly_data[:current_hour + 1]) if valid_hourly_data else 0

            # Grundlæggende attributter
            attrs = {
                "Daily Usage": self._state,
                "Metering Point": self._data.get_metering_point(),
                "Metering date": self._data_date,
            }

            # Tilføj uge-historik hvis tilgængelig (fra HassEloverblik.update_energy)
            if hasattr(self._data, "_week_data") and self._data._week_data:

                attrs.update(self._data._week_data)

            self._extra_state_attributes = attrs
            _LOGGER.debug("Updated daily state: %s, attributes: %s", self._state, self._extra_state_attributes)

        # MONTHLY SENSOR
        elif self._sensor_type == 'monthly':
            current_day = datetime.now().day
            total_monthly_usage = 0
            for day in range(1, current_day + 1):
                daily_usage = sum(self._data.get_usage_day(day, h) for h in range(24) if self._data.get_usage_day(day, h) is not None)
                total_monthly_usage += daily_usage

            self._state = total_monthly_usage
            self._extra_state_attributes = {
                'Monthly Usage': self._state,
                'Metering Point': self._data.get_metering_point(),
                'Metering Month': datetime.now().strftime('%B %Y'),
            }
            _LOGGER.debug("Updated monthly total state: %s, attributes: %s", self._state, self._extra_state_attributes)

        # YEAR/TOTAL SENSOR
        elif self._sensor_type == 'total':
            self._state = self._data.get_total_year() or 0
            self._extra_state_attributes = {
                'Yearly Consumption': self._state,
                'Metering Point': self._data.get_metering_point(),
                'Metering date': self._data_date,
            }
            _LOGGER.debug("Updated total state: %s, attributes: %s", self._state, self._extra_state_attributes)

        else:
            raise ValueError(f"Unexpected sensor_type: {self._sensor_type}.")