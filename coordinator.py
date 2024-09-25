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
        """Return the name of the sensor."""
        sensor = get_sensor_by_type(self._sensor_type)
        return sensor.name if sensor else None

    @property
    def unique_id(self):
        """Return the unique id of the sensor."""
        return self._unique_id

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def extra_state_attributes(self):
        """Return state attributes."""
        return self._extra_state_attributes

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        sensor = get_sensor_by_type(self._sensor_type)
        return sensor.native_unit_of_measurement if sensor else None
    
    @property
    def icon(self):
        """Return the icon of the sensor."""
        sensor = get_sensor_by_type(self._sensor_type)
        return sensor.icon if sensor else None

    def update(self):
        """Update the sensor's state and attributes."""
        self._data.update_energy()
        self._data_date = self._data.get_data_date()

        if self._sensor_type == 'daily':
            current_hour = datetime.now().hour
            hourly_data = [self._data.get_usage_hour(h) for h in range(24)]

            valid_hourly_data = [data for data in hourly_data if data is not None]
            self._state = sum(valid_hourly_data[:current_hour + 1]) if valid_hourly_data else 0

            self._extra_state_attributes = {
                'Daily Usage': f"{self._state} {self.unit_of_measurement}",
                'Metering Point': self._data.get_metering_point(),
                'Metering date': self._data_date,
            }
            _LOGGER.debug(f"Updated daily state: {self._state}, attributes: {self._extra_state_attributes}")
          
        elif self._sensor_type == 'monthly':
            hourly_data = [self._data.get_usage_hour(hour) for hour in range(24)]
            
            total_monthly_usage = 0
            for day in range(1, 32):  
                daily_usage = sum(self._data.get_usage_day(day, hour) for hour in range(24) if self._data.get_usage_day(day, hour) is not None)
                total_monthly_usage += daily_usage

            self._state = total_monthly_usage
            self._extra_state_attributes = {
                'Monthly Usage': f"{self._state} {self.unit_of_measurement}",
                'Metering Point': self._data.get_metering_point(),
                'Metering Month': datetime.now().strftime('%B %Y'),
            }
            _LOGGER.debug(f"Updated monthly total state: {self._state}, attributes: {self._extra_state_attributes}")

        elif self._sensor_type == 'total':
            self._state = self._data.get_total_year() or 0
            self._extra_state_attributes = {
                'Yearly Consumption': f"{self._state} {self.unit_of_measurement}",
                'Metering Point': self._data.get_metering_point(),
                'Metering date': self._data_date,
            }
            _LOGGER.debug(f"Updated total state: {self._state}, attributes: {self._extra_state_attributes}")

        else:
            raise ValueError(f"Unexpected sensor_type: {self._sensor_type}.")
