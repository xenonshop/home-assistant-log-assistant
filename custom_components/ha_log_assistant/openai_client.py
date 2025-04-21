"""OpenAI client for Home Assistant Log Assistant."""
import logging
import json
import re
import asyncio
from typing import Dict, Any, Optional

import openai
from openai import AsyncOpenAI

_LOGGER = logging.getLogger(__name__)

class OpenAIClient:
    """Client for interacting with OpenAI API."""

    def __init__(self, api_key: str, model_name: str):
        """Initialize the OpenAI client."""
        self.api_key = api_key
        self.model_name = model_name
        self.client = AsyncOpenAI(api_key=api_key)
        
        # Cache for similar issues to avoid redundant API calls
        self.response_cache = {}
        self.cache_size_limit = 50
        
        _LOGGER.info("OpenAI client initialized with model: %s", model_name)

    async def analyze_log(self, log_text: str, issue_type: str, metadata: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Analyze log text and return suggestions."""
        try:
            # Check cache for similar issues first
            cache_key = self._generate_cache_key(log_text, issue_type)
            if cache_key in self.response_cache:
                _LOGGER.debug("Using cached analysis for similar issue")
                return self.response_cache[cache_key]
            
            # Prepare the prompt for the AI
            prompt = self._create_prompt(log_text, issue_type, metadata)
            
            # Call the OpenAI API
            response = await self._call_openai_api(prompt)
            
            if not response:
                return None
                
            # Parse the response
            parsed_response = self._parse_response(response)
            
            # Cache the response if valid
            if parsed_response and parsed_response.get("suggested_fix"):
                self._update_cache(cache_key, parsed_response)
                
            return parsed_response
            
        except Exception as err:
            _LOGGER.error("Error analyzing logs with OpenAI: %s", err, exc_info=True)
            return None

    def _create_prompt(self, log_text: str, issue_type: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Create a prompt for the OpenAI model."""
        # Truncate log text if it's too long to avoid token limits
        max_log_length = 4000  # Adjust based on model's context window
        if len(log_text) > max_log_length:
            log_text = log_text[:max_log_length] + "... [truncated]"
        
        # Format metadata for inclusion in the prompt
        metadata_str = ""
        if metadata:
            metadata_str = "CONTEXT INFORMATION:\n"
            if metadata.get("entities"):
                metadata_str += f"Entities mentioned: {', '.join(metadata['entities'][:10])}\n"
            if metadata.get("components"):
                metadata_str += f"Components/integrations involved: {', '.join(metadata['components'][:5])}\n"
            if metadata.get("services"):
                metadata_str += f"Services mentioned: {', '.join(metadata['services'][:5])}\n"
            metadata_str += "\n"
        
        # Create a more detailed prompt with Home Assistant specific guidance
        return f"""
You are a Home Assistant expert assistant. Analyze the following log snippet that contains a potential {issue_type.replace('_', ' ')} issue.

{metadata_str}LOG SNIPPET:
```
{log_text}
```

Based on the log snippet, identify the specific issue and provide a practical solution.

Common Home Assistant issues and their typical solutions:
1. Entity unavailable: Check entity configuration, verify the device is powered and connected, check network connectivity, or restart the integration.
2. Automation errors: Check for syntax errors, verify entity IDs exist, ensure conditions are valid, or check for timing issues.
3. Script errors: Verify service calls are valid, check entity IDs, or ensure required parameters are provided.
4. Configuration errors: Look for syntax errors in YAML, check indentation, verify required fields are present, or ensure values are in the correct format.
5. Integration errors: Check if the integration is properly configured, verify credentials, check network connectivity, or update the integration.

Provide a JSON response with the following fields:
1. "suggested_fix": A clear, concise, step-by-step suggestion on how to fix the issue
2. "details": Additional context or explanation about the issue, including potential causes
3. "confidence": A number from 0-100 indicating your confidence in this suggestion

Only respond with valid JSON. Do not include any other text.
"""

    async def _call_openai_api(self, prompt: str) -> Optional[str]:
        """Call the OpenAI API with the given prompt."""
        try:
            # Add retry logic for API resilience
            max_retries = 3
            retry_delay = 2  # seconds
            
            for attempt in range(max_retries):
                try:
                    response = await self.client.chat.completions.create(
                        model=self.model_name,
                        messages=[
                            {"role": "system", "content": "You are a Home Assistant expert assistant that analyzes logs and provides suggestions for fixes. You have deep knowledge of Home Assistant components, integrations, and common issues."},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.2,  # Lower temperature for more deterministic responses
                        max_tokens=800,   # Increased token limit for more detailed responses
                        response_format={"type": "json_object"}  # Ensure JSON response
                    )
                    
                    if not response.choices or not response.choices[0].message.content:
                        _LOGGER.error("Empty response from OpenAI API")
                        return None
                        
                    return response.choices[0].message.content
                    
                except openai.RateLimitError as e:
                    if attempt < max_retries - 1:
                        wait_time = retry_delay * (2 ** attempt)  # Exponential backoff
                        _LOGGER.warning(f"Rate limit hit, retrying in {wait_time}s (attempt {attempt+1}/{max_retries})")
                        await asyncio.sleep(wait_time)
                    else:
                        raise
                        
                except (openai.APIError, openai.APIConnectionError) as e:
                    if attempt < max_retries - 1:
                        wait_time = retry_delay * (2 ** attempt)
                        _LOGGER.warning(f"API error, retrying in {wait_time}s (attempt {attempt+1}/{max_retries}): {e}")
                        await asyncio.sleep(wait_time)
                    else:
                        raise
            
        except Exception as err:
            _LOGGER.error("Error calling OpenAI API: %s", err, exc_info=True)
            return None

    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        """Parse the response from OpenAI into a structured format."""
        try:
            # Extract JSON from the response (in case there's any extra text)
            json_match = re.search(r'({.*})', response_text, re.DOTALL)
            if json_match:
                response_text = json_match.group(1)
                
            response_data = json.loads(response_text)
            
            # Ensure required fields are present
            if "suggested_fix" not in response_data:
                response_data["suggested_fix"] = "No specific suggestion available"
                
            if "confidence" not in response_data:
                response_data["confidence"] = 50
                
            if "details" not in response_data:
                response_data["details"] = ""
                
            # Validate confidence value
            try:
                confidence = int(response_data["confidence"])
                if confidence < 0 or confidence > 100:
                    response_data["confidence"] = max(0, min(100, confidence))
            except (ValueError, TypeError):
                response_data["confidence"] = 50
                
            return response_data
            
        except json.JSONDecodeError:
            _LOGGER.error("Failed to parse OpenAI response as JSON: %s", response_text)
            return {
                "suggested_fix": "Could not generate a suggestion (API response format error)",
                "confidence": 0,
                "details": ""
            }
    
    def _generate_cache_key(self, log_text: str, issue_type: str) -> str:
        """Generate a cache key for a log analysis request."""
        # Use a simplified representation of the log text to identify similar issues
        # Extract key parts like error messages and entity IDs
        error_pattern = re.compile(r'(Error|Exception|Failed|WARNING|ERROR).*?(?=\n|$)', re.IGNORECASE)
        entity_pattern = re.compile(r'([a-z_]+\.[a-z0-9_]+)', re.IGNORECASE)
        
        errors = error_pattern.findall(log_text)
        entities = entity_pattern.findall(log_text)
        
        # Create a simplified key from the issue type and extracted patterns
        key_parts = [issue_type]
        if errors:
            key_parts.extend(errors[:2])  # Use first two error messages
        if entities:
            key_parts.extend(entities[:3])  # Use first three entity IDs
            
        return "|".join(key_parts)
    
    def _update_cache(self, key: str, value: Dict[str, Any]):
        """Update the response cache with a new entry, maintaining size limit."""
        # If cache is at capacity, remove oldest entry
        if len(self.response_cache) >= self.cache_size_limit:
            oldest_key = next(iter(self.response_cache))
            del self.response_cache[oldest_key]
            
        # Add new entry
        self.response_cache[key] = value
