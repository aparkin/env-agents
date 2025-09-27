"""
Standardized Error Classification for Environmental Data Adapters

All adapters must follow these error handling patterns for consistency:

1. SERVICE ERROR (Authentication, API down, network issues):
   - Raise FetchError("Specific error message")
   - This indicates the service itself is having problems

2. NO DATA (Service operational but no data for location/time):  
   - Return empty list: []
   - This is a valid result - service works but has no data for the request

3. SUCCESS WITH DATA:
   - Return list of dicts: [{'observation_id': ..., 'value': ..., ...}]
   - All dicts must conform to 24-column CORE_COLUMNS schema

IMPORTANT: Never mask service errors as "no data" or vice versa.
Users and downstream systems need to distinguish between these cases.
"""

from typing import List, Dict, Any
from .errors import FetchError

class StandardErrorHandler:
    """Helper class for consistent error handling across adapters"""
    
    @staticmethod
    def service_error(message: str, service: str = None) -> None:
        """Raise standardized service error"""
        prefix = f"{service}: " if service else ""
        raise FetchError(f"{prefix}{message}")
    
    @staticmethod
    def no_data_result(message: str = "No data found for the specified location and time range") -> List[Dict[str, Any]]:
        """Return standardized no-data result"""
        return []  # Empty list indicates no data (but service is operational)
    
    @staticmethod
    def validate_success_data(rows: List[Dict[str, Any]], service: str = None) -> List[Dict[str, Any]]:
        """Validate that success data conforms to expected schema"""
        if not isinstance(rows, list):
            StandardErrorHandler.service_error(
                f"Adapter returned invalid data type {type(rows)}, expected list", 
                service
            )
        
        # Additional schema validation could be added here
        return rows

# Error classification examples:

# ❌ BAD - masks service error as no data:
# try:
#     response = api_call()
# except requests.ConnectionError:
#     return []  # This hides that the service is down!

# ✅ GOOD - distinguishes service error from no data:
# try:
#     response = api_call()
#     if response.status_code == 404:
#         return StandardErrorHandler.no_data_result("No monitoring stations in region")
#     response.raise_for_status()
#     data = response.json()
#     if not data or len(data) == 0:
#         return StandardErrorHandler.no_data_result()
#     return process_data(data)
# except requests.ConnectionError as e:
#     StandardErrorHandler.service_error(f"Network connection failed: {e}", "SERVICE_NAME")
# except requests.HTTPError as e:
#     StandardErrorHandler.service_error(f"API error: {e}", "SERVICE_NAME")