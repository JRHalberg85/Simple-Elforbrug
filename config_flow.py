import logging
import voluptuous as vol
from homeassistant import config_entries, core, exceptions
from .const import DOMAIN, DATA_SCHEMA

_LOGGER = logging.getLogger(__name__)

def validate_metering_point(metering_point):
    """Validate the metering point."""
    if len(metering_point) != 18 or not metering_point.isdigit():
        raise InvalidMeteringPoint(f"Metering point {metering_point} is invalid.")
    return True

async def validate_input(hass: core.HomeAssistant, data):
    """Validate the user input and return additional information."""
    # Validate the metering point separately
    metering_point = data["metering_point"]
    validate_metering_point(metering_point)

    # Generate a title including the current setup date
    return {"title": f"Simple Elforbrug. Meter point: {metering_point})"}

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Eloverblik."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            try:
                validate_metering_point(user_input["metering_point"])
                info = await validate_input(self.hass, user_input)
                return self.async_create_entry(title=info["title"], data=user_input)
            except InvalidMeteringPoint:
                errors["base"] = "invalid_metering_point"
            except Exception as e:
                _LOGGER.error(f"Unexpected error: {str(e)}")
                errors["base"] = "unknown_error"
            except InvalidMeteringPoint:
                errors["base"] = "invalid_metering_point"
            except Exception as e:
                _LOGGER.error(f"Unexpected error: {str(e)}")
                
        return self.async_show_form(
            step_id="user", 
            data_schema=DATA_SCHEMA, 
            errors=errors,
        )

class InvalidMeteringPoint(exceptions.HomeAssistantError):
    """Error to indicate the metering point is invalid."""

class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""

class InvalidAuth(exceptions.HomeAssistantError):
    """Error to indicate there is invalid auth."""