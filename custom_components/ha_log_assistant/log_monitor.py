"""Log monitoring and analysis component for Home Assistant Log Assistant."""
import logging
import asyncio
import re
import os
from datetime import datetime
from typing import Dict, List, Optional, Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_track_time_interval
import homeassistant.util.dt as dt_util

from .openai_client import OpenAIClient
from .const import (
    ISSUE_ENTITY_UNAVAILABLE,
    ISSUE_AUTOMATION_ERROR,
    ISSUE_SCRIPT_ERROR,
    ISSUE_CONFIG_ERROR,
    ISSUE_INTEGRATION_ERROR,
    ISSUE_GENERAL_ERROR,
    EVENT_ISSUE_DETECTED,
    EVENT_ASSISTANT_UPDATED,
)

_LOGGER = logging.getLogger(__name__)

class LogMonitor:
    """Class to monitor and analyze Home Assistant logs."""

    def __init__(
        self,
        hass: HomeAssistant,
        api_key: str,
        model_name: str,
        log_path: str,
        scan_interval: int,
    ):
        """Initialize the log monitor."""
        self.hass = hass
        self.log_path = log_path
        self.scan_interval = scan_interval
        self.openai_client = OpenAIClient(api_key, model_name)
        self.last_position = 0
        self.issues = []
        self.cancel_interval = None
        self.last_scan_time = None
        
        # Enhanced regex patterns for better issue detection
        self._issue_patterns = {
            ISSUE_ENTITY_UNAVAILABLE: r"(Entity|Device) .+? (is unavailable|not available|could not be found|not found|not responding)",
            ISSUE_AUTOMATION_ERROR: r"(Error|Exception) (executing|running|in) automation .+?",
            ISSUE_SCRIPT_ERROR: r"(Error|Exception) (executing|running|in) script .+?",
            ISSUE_CONFIG_ERROR: r"(Invalid|Error in|Failed) config(uration)? .+?",
            ISSUE_INTEGRATION_ERROR: r"(Error|Failed|Exception) (setting up|loading|initializing) (platform|integration|component) .+?",
            ISSUE_GENERAL_ERROR: r"(Error|Exception|Failed|Traceback|WARNING|ERROR)",
        }
        
        # Additional patterns for specific Home Assistant issues
        self._entity_id_pattern = re.compile(r'([a-z_]+\.[a-z0-9_]+)', re.IGNORECASE)
        self._component_pattern = re.compile(r'(component|integration|platform) ([a-z_]+)', re.IGNORECASE)
        self._service_pattern = re.compile(r'service ([a-z_]+\.[a-z_]+)', re.IGNORECASE)

    async def initialize(self):
        """Set up the log monitor."""
        # Set initial file position
        try:
            if os.path.exists(self.log_path):
                self.last_position = os.path.getsize(self.log_path)
                _LOGGER.info("Log monitor initialized at position %s for %s", 
                            self.last_position, self.log_path)
            else:
                _LOGGER.error("Log file not found: %s", self.log_path)
        except Exception as err:
            _LOGGER.error("Error initializing log monitor: %s", err)

        # Schedule regular log analysis
        self.cancel_interval = async_track_time_interval(
            self.hass, 
            self.analyze_logs, 
            dt_util.parse_duration(f"{self.scan_interval}s")
        )
        
        # Run initial analysis
        await self.analyze_logs(None)
        
        _LOGGER.info("Home Assistant Log Assistant initialized successfully")

    async def shutdown(self):
        """Stop the log monitor."""
        if self.cancel_interval:
            self.cancel_interval()
            _LOGGER.info("Log monitor shutdown complete")

    async def analyze_logs(self, _now=None):
        """Analyze logs for issues and generate suggestions."""
        try:
            self.last_scan_time = dt_util.now().isoformat()
            _LOGGER.debug("Starting log analysis at %s", self.last_scan_time)
            
            if not os.path.exists(self.log_path):
                _LOGGER.error("Log file not found: %s", self.log_path)
                return

            # Read new log entries
            current_size = os.path.getsize(self.log_path)
            
            # Handle log rotation (if current size is smaller than last position)
            if current_size < self.last_position:
                _LOGGER.info("Log rotation detected, resetting position")
                self.last_position = 0
            
            if current_size == self.last_position:
                _LOGGER.debug("No new log entries to analyze")
                return
                
            with open(self.log_path, 'r', encoding='utf-8', errors='replace') as f:
                f.seek(self.last_position)
                new_logs = f.read()
                
            self.last_position = current_size
            
            _LOGGER.debug("Read %d bytes of new log data", len(new_logs))
            
            # Preliminary filtering to identify potential issues
            potential_issues = await self._identify_potential_issues(new_logs)
            
            if not potential_issues:
                _LOGGER.debug("No potential issues found in logs")
                return
                
            _LOGGER.info("Found %d potential issues across %d categories", 
                        sum(len(snippets) for snippets in potential_issues.values()),
                        len(potential_issues))
                
            # Analyze issues with OpenAI
            for issue_type, log_snippets in potential_issues.items():
                _LOGGER.debug("Processing %d issues of type %s", len(log_snippets), issue_type)
                
                # Process at most 5 issues per type to avoid excessive API calls
                for snippet in log_snippets[:5]:
                    # Extract metadata to provide context for the analysis
                    metadata = self._extract_metadata(snippet, issue_type)
                    
                    # Analyze with OpenAI
                    analysis = await self.openai_client.analyze_log(snippet, issue_type, metadata)
                    
                    if analysis and analysis.get("suggested_fix"):
                        self.issues.append({
                            "issue_type": issue_type,
                            "log_snippet": snippet,
                            "suggested_fix": analysis.get("suggested_fix"),
                            "confidence": analysis.get("confidence", 0),
                            "detected_at": dt_util.now().isoformat(),
                            "details": analysis.get("details", ""),
                            "metadata": metadata
                        })
                        
                        _LOGGER.info("New issue detected: %s (confidence: %s%%)", 
                                    issue_type, analysis.get("confidence", 0))
                        
                        # Notify about the new issue
                        await self._notify_new_issue(self.issues[-1])
            
            # Update sensor state
            self.hass.bus.async_fire(EVENT_ASSISTANT_UPDATED, {"issues_count": len(self.issues)})
            
        except Exception as err:
            _LOGGER.error("Error analyzing logs: %s", err, exc_info=True)

    async def _identify_potential_issues(self, log_text: str) -> Dict[str, List[str]]:
        """Identify potential issues in log text using regex patterns."""
        potential_issues = {}
        
        # Split logs into individual entries (assuming standard HA log format)
        log_entries = re.findall(
            r'\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2}.*?(?=\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2}|$)', 
            log_text, 
            re.DOTALL
        )
        
        if not log_entries:
            # Try alternative pattern for different log formats
            log_entries = log_text.split('\n\n')
        
        _LOGGER.debug("Found %d log entries to analyze", len(log_entries))
        
        # Process each issue type in parallel for better performance
        tasks = []
        for issue_type, pattern in self._issue_patterns.items():
            task = asyncio.create_task(
                self._find_matching_entries(issue_type, pattern, log_entries)
            )
            tasks.append(task)
            
        results = await asyncio.gather(*tasks)
        
        # Combine results
        for issue_type, matching_entries in results:
            if matching_entries:
                potential_issues[issue_type] = matching_entries
                
        return potential_issues
        
    async def _find_matching_entries(self, issue_type, pattern, log_entries):
        """Find log entries matching a specific pattern."""
        matching_entries = []
        compiled_pattern = re.compile(pattern, re.IGNORECASE)
        
        for entry in log_entries:
            if compiled_pattern.search(entry):
                # Get context by including a few lines before and after if possible
                try:
                    entry_index = log_entries.index(entry)
                    start_idx = max(0, entry_index - 2)
                    end_idx = min(len(log_entries), entry_index + 3)
                    context = "\n".join(log_entries[start_idx:end_idx])
                    
                    # Deduplicate entries with similar content
                    if not any(self._is_similar_entry(context, existing) for existing in matching_entries):
                        matching_entries.append(context)
                except ValueError:
                    # If entry.index fails (duplicate entries), just use the entry itself
                    matching_entries.append(entry)
        
        return (issue_type, matching_entries)
    
    def _is_similar_entry(self, entry1, entry2):
        """Check if two log entries are similar to avoid duplicates."""
        # Simple similarity check - can be enhanced with more sophisticated algorithms
        if len(entry1) < 20 or len(entry2) < 20:
            return entry1 == entry2
            
        # Check if they share significant content
        return entry1[20:100] == entry2[20:100]
        
    def _extract_metadata(self, log_snippet, issue_type):
        """Extract useful metadata from log snippet to provide context for analysis."""
        metadata = {
            "issue_type": issue_type,
            "entities": [],
            "components": [],
            "services": []
        }
        
        # Extract entity IDs
        entities = self._entity_id_pattern.findall(log_snippet)
        if entities:
            metadata["entities"] = list(set(entities))
            
        # Extract component/integration names
        components = self._component_pattern.findall(log_snippet)
        if components:
            metadata["components"] = list(set([comp[1] for comp in components]))
            
        # Extract service calls
        services = self._service_pattern.findall(log_snippet)
        if services:
            metadata["services"] = list(set(services))
            
        return metadata

    async def _notify_new_issue(self, issue: Dict[str, Any]):
        """Notify users about a new issue."""
        self.hass.bus.async_fire(
            EVENT_ISSUE_DETECTED,
            {
                "issue_type": issue["issue_type"],
                "suggested_fix": issue["suggested_fix"],
                "confidence": issue["confidence"],
            }
        )
        
        # Create a persistent notification
        await self.hass.services.async_call(
            "persistent_notification",
            "create",
            {
                "title": f"Log Assistant: {issue['issue_type'].replace('_', ' ').title()} Issue",
                "message": (
                    f"**Suggested Fix:** {issue['suggested_fix']}\n\n"
                    f"**Log Snippet:**\n```\n{issue['log_snippet'][:300]}...\n```\n\n"
                    f"**Confidence:** {issue['confidence']}%\n\n"
                    f"**Details:** {issue.get('details', 'No additional details')}"
                ),
                "notification_id": f"log_assistant_{len(self.issues)}"
            }
        )

    def get_issues(self, limit: Optional[int] = None, issue_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get detected issues, optionally filtered by type and limited to a count."""
        filtered_issues = self.issues
        
        if issue_type:
            filtered_issues = [i for i in filtered_issues if i["issue_type"] == issue_type]
            
        if limit and limit > 0:
            filtered_issues = filtered_issues[-limit:]
            
        return filtered_issues

    def clear_issues(self):
        """Clear all stored issues."""
        self.issues = []
        _LOGGER.info("Cleared all stored issues")
        
        # Update sensor state
        self.hass.bus.async_fire(EVENT_ASSISTANT_UPDATED, {"issues_count": 0})

