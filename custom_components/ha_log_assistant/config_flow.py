"""Config flow for Home Assistant Log Assistant integration."""
import logging
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.const import (
    CONF_API_KEY,
    CONF_SCAN_INTERVAL,
)
from homeassistant.helpers import config_validation as cv

from .const import (
    DOMAIN,
    DEFAULT_SCAN_INTERVAL,
    CONF_MODEL_NAME,
    DEFAULT_MODEL_NAME,
    CONF_LOG_PATH,
    DEFAULT_LOG_PATH,
)

_LOGGER = logging.getLogger(__name__)

class LogAssistantConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Home Assistant Log Assistant."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            # Validate the API key (basic validation only)
            if not user_input[CONF_API_KEY].strip():
                errors[CONF_API_KEY] = "api_key_required"
            else:
                # Create entry
                return self.async_create_entry(
                    title="Home Assistant Log Assistant",
                    data=user_input,
                )

        # Show the configuration form to the user
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_API_KEY): str,
                    vol.Optional(CONF_MODEL_NAME, default=DEFAULT_MODEL_NAME): str,
                    vol.Optional(CONF_LOG_PATH, default=DEFAULT_LOG_PATH): str,
                    vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): int,
                }
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return LogAssistantOptionsFlow(config_entry)

class LogAssistantOptionsFlow(config_entries.OptionsFlow):
    """Handle options for the component."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_API_KEY,
                        default=self.config_entry.data.get(CONF_API_KEY, ""),
                    ): str,
                    vol.Optional(
                        CONF_MODEL_NAME,
                        default=self.config_entry.data.get(CONF_MODEL_NAME, DEFAULT_MODEL_NAME),
                    ): str,
                    vol.Optional(
                        CONF_LOG_PATH,
                        default=self.config_entry.data.get(CONF_LOG_PATH, DEFAULT_LOG_PATH),
                    ): str,
                    vol.Optional(
                        CONF_SCAN_INTERVAL,
                        default=self.config_entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
                    ): int,
                }
            ),
        )
