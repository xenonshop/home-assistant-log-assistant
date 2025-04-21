# Home Assistant Log Assistant - Architecture

This document describes the architecture and design of the Home Assistant Log Assistant integration.

## Overview

The Home Assistant Log Assistant is designed to monitor Home Assistant logs for common issues and provide AI-powered suggestions for fixes. It uses OpenAI's models to analyze log entries and generate helpful suggestions.

## Component Structure

The integration is structured as follows:

```
custom_components/ha_log_assistant/
├── __init__.py           # Main integration setup
├── manifest.json         # Integration manifest
├── config_flow.py        # Configuration UI
├── const.py              # Constants
├── log_monitor.py        # Log monitoring and analysis
├── openai_client.py      # OpenAI API client
├── sensor.py             # Sensor entities
├── services.yaml         # Service definitions
├── strings.json          # UI strings
└── translations/         # Translations
    └── en.json           # English translations
```

## Core Components

### 1. Log Monitor (`log_monitor.py`)

The Log Monitor is responsible for:
- Reading the Home Assistant log file
- Identifying potential issues using regex patterns
- Sending relevant log snippets to the OpenAI client for analysis
- Storing and managing detected issues
- Notifying users about new issues

### 2. OpenAI Client (`openai_client.py`)

The OpenAI Client handles:
- Creating appropriate prompts for the AI model
- Sending requests to the OpenAI API
- Parsing and structuring the AI responses

### 3. Sensors (`sensor.py`)

The integration provides two sensors:
- **Log Assistant Issues**: Shows the total number of detected issues
- **Log Assistant Last Issue**: Shows details about the most recently detected issue

### 4. Configuration (`config_flow.py`)

The configuration flow allows users to:
- Enter their OpenAI API key
- Customize the model name
- Specify the log file path
- Adjust the scan interval

## Data Flow

1. The Log Monitor periodically reads new entries from the Home Assistant log file
2. It uses regex patterns to identify potential issues in the logs
3. For each potential issue, it extracts metadata (entities, components, services) to provide context
4. It sends the relevant log snippet and metadata to the OpenAI client for analysis
5. The OpenAI client creates a detailed prompt and sends it to the OpenAI API
6. The API response is parsed, validated, and structured
7. If a valid suggestion is received, it's stored as an issue with metadata
8. Users are notified about new issues via persistent notifications
9. Sensor states are updated to reflect the new issues
10. The integration provides services to manually trigger analysis, retrieve issues, or clear issues

## Issue Categories

The integration detects several categories of issues:
- `entity_unavailable`: Entity unavailability issues
- `automation_error`: Errors in automations
- `script_error`: Errors in scripts
- `config_error`: Configuration problems
- `integration_error`: Integration setup issues
- `general_error`: General errors and exceptions

## Services

The integration provides the following services:
- **analyze_logs**: Manually trigger a log analysis
- **clear_issues**: Clear all detected issues
- **get_issues**: Retrieve detected issues, with optional filtering by type and count limitation

## Extension Points

The architecture is designed to be extensible:
- New issue categories can be added by updating the regex patterns in `log_monitor.py`
- Additional sensors can be created to display different aspects of the detected issues
- The OpenAI prompt can be customized to improve the quality of suggestions
- Additional services can be added to provide more functionality
- The metadata extraction can be enhanced to provide better context for analysis

## Performance Considerations

- The integration uses file seeking to only read new log entries since the last scan
- It performs preliminary filtering using regex to minimize the amount of data sent to the OpenAI API
- Parallel processing of log entries for better performance with large log files
- Response caching to avoid redundant API calls for similar issues
- Deduplication of similar log entries to reduce API usage
- Limiting the number of issues processed per type to avoid excessive API calls
- The scan interval is configurable to balance between timely issue detection and resource usage
- Retry logic with exponential backoff for API resilience
