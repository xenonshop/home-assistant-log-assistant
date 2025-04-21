# Home Assistant Log Assistant

A Home Assistant integration that monitors your logs for issues and provides AI-powered suggestions for fixes.

## Features

- Automatically monitors Home Assistant logs for common issues
- Uses OpenAI's models to analyze log entries and generate helpful suggestions
- Detects various types of issues:
  - Unavailable entities
  - Automation errors
  - Script errors
  - Configuration problems
  - Integration setup issues
  - General errors and exceptions
- Creates sensors to track issues and display suggestions
- Sends notifications when new issues are detected
- Provides a service to manually trigger log analysis

## Installation

### HACS Installation (Recommended)

1. Make sure [HACS](https://hacs.xyz/) is installed in your Home Assistant instance
2. Add this repository as a custom repository in HACS:
   - Go to HACS > Integrations
   - Click the three dots in the top right corner
   - Select "Custom repositories"
   - Add the URL: `https://github.com/yourusername/ha_log_assistant`
   - Category: Integration
3. Click "Install" on the Home Assistant Log Assistant integration
4. Restart Home Assistant

### Manual Installation

1. Download the latest release from the [GitHub repository](https://github.com/yourusername/ha_log_assistant)
2. Extract the `custom_components/ha_log_assistant` directory to your Home Assistant's `custom_components` directory
3. Restart Home Assistant

## Configuration

1. Go to Settings > Devices & Services
2. Click "Add Integration"
3. Search for "Home Assistant Log Assistant"
4. Follow the configuration steps:
   - Enter your OpenAI API key
   - Optionally customize the model name (default: gpt-3.5-turbo)
   - Optionally customize the log file path (default: /config/home-assistant.log)
   - Optionally adjust the scan interval in seconds (default: 3600 - 1 hour)

## Usage

Once installed and configured, the integration will:

1. Periodically scan your Home Assistant logs for issues
2. Create sensors with information about detected issues
3. Send notifications when new issues are detected

### Available Sensors

- **Log Assistant Issues**: Shows the total number of detected issues
- **Log Assistant Last Issue**: Shows details about the most recently detected issue

### Services

- **ha_log_assistant.analyze_logs**: Manually trigger a log analysis
- **ha_log_assistant.clear_issues**: Clear all detected issues
- **ha_log_assistant.get_issues**: Retrieve detected issues, with optional filtering by type and count limitation

## Privacy Considerations

This integration sends portions of your Home Assistant logs to OpenAI's API for analysis. While efforts are made to limit the data sent to only relevant log entries, you should be aware that log entries might contain sensitive information such as device names, room names, or other personal data.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
