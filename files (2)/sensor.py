"""Sensor platform for Home Assistant Log Assistant."""
import logging
from typing import Any, Dict, Optional

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.event import async_track_state_change_event

from .const import (
    DOMAIN,
    ATTR_ISSUE_TYPE,
    ATTR_ISSUE_DETAILS,
    ATTR_SUGGESTED_FIX,
    ATTR_CONFIDENCE,
    ATTR_DETECTED_AT,
    ATTR_LOG_SNIPPET,
    ATTR_METADATA,
    EVENT_ISSUE_DETECTED,
    EVENT_ASSISTANT_UPDATED,
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Home Assistant Log Assistant sensor."""
    log_monitor = hass.data[DOMAIN][config_entry.entry_id]
    
    async_add_entities([
        LogAssistantSensor(hass, log_monitor),
        LogAssistantLastIssueSensor(hass, log_monitor),
    ])

class LogAssistantSensor(SensorEntity):
    """Sensor showing the number of detected issues."""

    def __init__(self, hass: HomeAssistant, log_monitor):
        """Initialize the sensor."""
        self.hass = hass
        self.log_monitor = log_monitor
        self._attr_name = "Log Assistant Issues"
        self._attr_unique_id = f"{DOMAIN}_issues_count"
        self._attr_icon = "mdi:file-document-alert"
        self._attr_native_unit_of_measurement = "issues"
        self._attr_should_poll = False
        
    async def async_added_to_hass(self) -> None:
        """Register callbacks."""
        self.hass.bus.async_listen(EVENT_ASSISTANT_UPDATED, self._handle_update)
        self.hass.bus.async_listen(EVENT_ISSUE_DETECTED, self._handle_update)
        
    def _handle_update(self, event):
        """Handle updates from the log monitor."""
        self.async_schedule_update_ha_state(True)
        
    @property
    def native_value(self) -> StateType:
        """Return the number of issues."""
        return len(self.log_monitor.issues)
        
    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return entity specific state attributes."""
        return {
            "issues_by_type": self._count_issues_by_type(),
            "last_scan": self.log_monitor.last_scan_time if hasattr(self.log_monitor, "last_scan_time") else None,
        }
        
    def _count_issues_by_type(self) -> Dict[str, int]:
        """Count issues by type."""
        counts = {}
        for issue in self.log_monitor.issues:
            issue_type = issue["issue_type"]
            counts[issue_type] = counts.get(issue_type, 0) + 1
        return counts

class LogAssistantLastIssueSensor(SensorEntity):
    """Sensor showing the last detected issue."""

    def __init__(self, hass: HomeAssistant, log_monitor):
        """Initialize the sensor."""
        self.hass = hass
        self.log_monitor = log_monitor
        self._attr_name = "Log Assistant Last Issue"
        self._attr_unique_id = f"{DOMAIN}_last_issue"
        self._attr_icon = "mdi:alert-circle"
        self._attr_should_poll = False
        
    async def async_added_to_hass(self) -> None:
        """Register callbacks."""
        self.hass.bus.async_listen(EVENT_ISSUE_DETECTED, self._handle_new_issue)
        
    def _handle_new_issue(self, event):
        """Handle a new issue being detected."""
        self.async_schedule_update_ha_state(True)
        
    @property
    def native_value(self) -> StateType:
        """Return the type of the last issue."""
        if not self.log_monitor.issues:
            return "No Issues"
        return self.log_monitor.issues[-1]["issue_type"].replace("_", " ").title()
        
    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return entity specific state attributes."""
        if not self.log_monitor.issues:
            return {}
            
        last_issue = self.log_monitor.issues[-1]
        attributes = {
            ATTR_SUGGESTED_FIX: last_issue["suggested_fix"],
            ATTR_CONFIDENCE: last_issue["confidence"],
            ATTR_DETECTED_AT: last_issue["detected_at"],
            ATTR_ISSUE_DETAILS: last_issue.get("details", ""),
            ATTR_LOG_SNIPPET: last_issue["log_snippet"][:200] + "..." if len(last_issue["log_snippet"]) > 200 else last_issue["log_snippet"],
        }
        
        # Add metadata if available
        if "metadata" in last_issue:
            attributes[ATTR_METADATA] = last_issue["metadata"]
            
        return attributes
