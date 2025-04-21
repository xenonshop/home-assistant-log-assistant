"""Home Assistant Log Assistant Integration.

This integration monitors Home Assistant logs for issues and provides
suggestions for fixes using OpenAI's models.
"""
import logging
import asyncio
import os
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.const import (
    CONF_API_KEY,
    CONF_SCAN_INTERVAL,
)
from homeassistant.helpers.typing import ConfigType
import homeassistant.helpers.config_validation as cv
from homeassistant.exceptions import HomeAssistantError

from .const import (
    DOMAIN,
    DEFAULT_SCAN_INTERVAL,
    CONF_MODEL_NAME,
    DEFAULT_MODEL_NAME,
    CONF_LOG_PATH,
    DEFAULT_LOG_PATH,
    SERVICE_ANALYZE_LOGS,
    SERVICE_CLEAR_ISSUES,
    SERVICE_GET_ISSUES,
    ATTR_ISSUE_TYPE,
    ATTR_LIMIT,
)
from .log_monitor import LogMonitor

_LOGGER = logging.getLogger(__name__)

# Schema for the analyze_logs service
ANALYZE_LOGS_SCHEMA = vol.Schema({})

# Schema for the clear_issues service
CLEAR_ISSUES_SCHEMA = vol.Schema({})

# Schema for the get_issues service
GET_ISSUES_SCHEMA = vol.Schema({
    vol.Optional(ATTR_ISSUE_TYPE): cv.string,
    vol.Optional(ATTR_LIMIT): cv.positive_int,
})

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_API_KEY): cv.string,
                vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): cv.positive_int,
                vol.Optional(CONF_MODEL_NAME, default=DEFAULT_MODEL_NAME): cv.string,
                vol.Optional(CONF_LOG_PATH, default=DEFAULT_LOG_PATH): cv.string,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)

PLATFORMS = ["sensor"]

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Home Assistant Log Assistant component."""
    if DOMAIN not in config:
        return True

    hass.data[DOMAIN] = {}
    
    # Register services
    await _register_services(hass)
    
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Home Assistant Log Assistant from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    
    # Validate log path exists
    log_path = entry.data.get(CONF_LOG_PATH, DEFAULT_LOG_PATH)
    if not os.path.exists(log_path):
        _LOGGER.warning(
            "Log file not found at %s. The integration will still be set up, "
            "but no logs will be analyzed until the file exists.", 
            log_path
        )
    
    # Create log monitor instance
    try:
        log_monitor = LogMonitor(
            hass,
            entry.data[CONF_API_KEY],
            entry.data.get(CONF_MODEL_NAME, DEFAULT_MODEL_NAME),
            log_path,
            entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        )
        
        await log_monitor.initialize()
        hass.data[DOMAIN][entry.entry_id] = log_monitor
        
        # Register services if not already registered
        if not hass.services.has_service(DOMAIN, SERVICE_ANALYZE_LOGS):
            await _register_services(hass)
        
        # Set up platforms
        for platform in PLATFORMS:
            hass.async_create_task(
                hass.config_entries.async_forward_entry_setup(entry, platform)
            )
        
        _LOGGER.info(
            "Home Assistant Log Assistant set up successfully with model %s, "
            "scanning every %s seconds",
            entry.data.get(CONF_MODEL_NAME, DEFAULT_MODEL_NAME),
            entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        )
        
        return True
        
    except Exception as err:
        _LOGGER.error("Error setting up Log Assistant: %s", err, exc_info=True)
        raise HomeAssistantError(f"Failed to set up Log Assistant: {err}") from err

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, platform)
                for platform in PLATFORMS
            ]
        )
    )
    
    if unload_ok:
        log_monitor = hass.data[DOMAIN].pop(entry.entry_id)
        await log_monitor.shutdown()
        
        # Remove services if this is the last entry
        if not hass.data[DOMAIN]:
            for service in [SERVICE_ANALYZE_LOGS, SERVICE_CLEAR_ISSUES, SERVICE_GET_ISSUES]:
                if hass.services.has_service(DOMAIN, service):
                    hass.services.async_remove(DOMAIN, service)
    
    return unload_ok

async def _register_services(hass: HomeAssistant):
    """Register integration services."""
    
    @callback
    def get_log_monitors():
        """Get all log monitor instances."""
        return [
            log_monitor 
            for entry_id, log_monitor in hass.data[DOMAIN].items()
        ]
    
    async def analyze_logs_service(call: ServiceCall):
        """Service to manually trigger log analysis."""
        _LOGGER.info("Manual log analysis triggered via service call")
        for log_monitor in get_log_monitors():
            await log_monitor.analyze_logs()
    
    async def clear_issues_service(call: ServiceCall):
        """Service to clear all detected issues."""
        _LOGGER.info("Clearing all issues via service call")
        for log_monitor in get_log_monitors():
            log_monitor.clear_issues()
    
    async def get_issues_service(call: ServiceCall):
        """Service to get detected issues."""
        issue_type = call.data.get(ATTR_ISSUE_TYPE)
        limit = call.data.get(ATTR_LIMIT)
        
        all_issues = []
        for log_monitor in get_log_monitors():
            issues = log_monitor.get_issues(limit=limit, issue_type=issue_type)
            all_issues.extend(issues)
            
        # Sort by detection time
        all_issues.sort(key=lambda x: x.get("detected_at", ""))
        
        # Apply limit after combining all issues
        if limit and limit > 0:
            all_issues = all_issues[-limit:]
            
        # Return as service response
        return {"issues": all_issues}
    
    # Register services
    hass.services.async_register(
        DOMAIN, 
        SERVICE_ANALYZE_LOGS, 
        analyze_logs_service, 
        schema=ANALYZE_LOGS_SCHEMA
    )
    
    hass.services.async_register(
        DOMAIN, 
        SERVICE_CLEAR_ISSUES, 
        clear_issues_service, 
        schema=CLEAR_ISSUES_SCHEMA
    )
    
    hass.services.async_register(
        DOMAIN, 
        SERVICE_GET_ISSUES, 
        get_issues_service, 
        schema=GET_ISSUES_SCHEMA
    )
