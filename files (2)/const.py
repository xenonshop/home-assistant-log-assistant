"""Constants for the Home Assistant Log Assistant integration."""

DOMAIN = "ha_log_assistant"

# Configuration
CONF_MODEL_NAME = "model_name"
CONF_LOG_PATH = "log_path"

# Defaults
DEFAULT_SCAN_INTERVAL = 3600  # 1 hour in seconds
DEFAULT_MODEL_NAME = "gpt-3.5-turbo"
DEFAULT_LOG_PATH = "/config/home-assistant.log"

# Services
SERVICE_ANALYZE_LOGS = "analyze_logs"
SERVICE_CLEAR_ISSUES = "clear_issues"
SERVICE_GET_ISSUES = "get_issues"

# Service parameters
ATTR_LIMIT = "limit"

# Issue categories
ISSUE_ENTITY_UNAVAILABLE = "entity_unavailable"
ISSUE_AUTOMATION_ERROR = "automation_error"
ISSUE_SCRIPT_ERROR = "script_error"
ISSUE_CONFIG_ERROR = "config_error"
ISSUE_INTEGRATION_ERROR = "integration_error"
ISSUE_GENERAL_ERROR = "general_error"

# Attributes
ATTR_ISSUE_TYPE = "issue_type"
ATTR_ISSUE_DETAILS = "issue_details"
ATTR_SUGGESTED_FIX = "suggested_fix"
ATTR_CONFIDENCE = "confidence"
ATTR_DETECTED_AT = "detected_at"
ATTR_LOG_SNIPPET = "log_snippet"
ATTR_METADATA = "metadata"

# Events
EVENT_ISSUE_DETECTED = "ha_log_assistant_issue_detected"
EVENT_ASSISTANT_UPDATED = "ha_log_assistant_updated"
