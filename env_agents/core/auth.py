"""
Unified Authentication Management System for env-agents

Creates a uniform authentication interface that abstracts different backend
authentication schemes (API keys, service accounts, OAuth, none) while
maintaining the specific requirements of each service.

This allows developers to have a consistent authentication experience
regardless of the underlying service complexity.
"""

import os
import json
import logging
from typing import Dict, Any, Optional, Tuple
from pathlib import Path
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class AuthenticationError(Exception):
    """Authentication-related errors with rich context for debugging"""
    def __init__(self, message: str, service_id: str, auth_type: str,
                 suggested_fix: str = None, config_status: Dict[str, Any] = None):
        super().__init__(message)
        self.service_id = service_id
        self.auth_type = auth_type
        self.suggested_fix = suggested_fix or "Check service configuration and credentials"
        self.config_status = config_status or {}


class AuthenticationManager:
    """
    Unified authentication interface that hides backend complexity.

    Provides a single authenticate_service() method that handles:
    - API key authentication (NASA_POWER, EPA_AQS, OpenAQ)
    - Service account authentication (Earth Engine)
    - No authentication (GBIF, SoilGrids, USGS_NWIS, etc.)
    - OAuth flows (future services)

    Each service gets appropriate authentication context for its specific
    requirements, but the developer interface remains consistent.
    """

    def __init__(self, config_manager):
        """
        Initialize authentication manager with configuration.

        Args:
            config_manager: ConfigManager instance for credential access
        """
        self.config_manager = config_manager
        self._auth_cache = {}  # Cache authenticated sessions

        # Define authentication schemes for each service
        self.auth_schemes = {
            'NASA_POWER': 'api_key',
            'EPA_AQS': 'api_key',
            'OpenAQ': 'api_key',
            'EARTH_ENGINE': 'service_account',
            'GBIF': 'none',
            'SoilGrids': 'none',
            'WQP': 'none',
            'OSM_Overpass': 'none',
            'USGS_NWIS': 'none',
            'SSURGO': 'none'
        }

    def authenticate_service(self, service_id: str) -> Dict[str, Any]:
        """
        Authenticate a service and return auth context.

        This is the unified interface that abstracts all authentication complexity.
        Returns a standardized auth context that adapters can use consistently.

        Args:
            service_id: Service identifier (e.g., 'NASA_POWER', 'EPA_AQS')

        Returns:
            Dict with authentication context:
            {
                'authenticated': bool,
                'auth_type': str,
                'headers': dict,        # HTTP headers to include
                'params': dict,         # URL parameters to include
                'session_config': dict, # requests.Session configuration
                'service_config': dict, # Service-specific configuration
                'metadata': dict        # Additional auth metadata
            }

        Raises:
            AuthenticationError: If authentication fails with detailed context
        """
        if service_id in self._auth_cache:
            cached_auth = self._auth_cache[service_id]
            if self._is_auth_valid(cached_auth):
                return cached_auth

        auth_scheme = self.auth_schemes.get(service_id, 'none')

        try:
            if auth_scheme == 'api_key':
                auth_context = self._handle_api_key_auth(service_id)
            elif auth_scheme == 'service_account':
                auth_context = self._handle_service_account_auth(service_id)
            elif auth_scheme == 'none':
                auth_context = self._handle_no_auth(service_id)
            elif auth_scheme == 'oauth':
                auth_context = self._handle_oauth_auth(service_id)
            else:
                raise AuthenticationError(
                    f"Unsupported auth scheme: {auth_scheme}",
                    service_id=service_id,
                    auth_type=auth_scheme
                )

            # Cache successful authentication
            auth_context['authenticated_at'] = datetime.utcnow()
            self._auth_cache[service_id] = auth_context

            return auth_context

        except Exception as e:
            # Convert any auth failure to rich AuthenticationError
            config_status = self._get_config_status(service_id)
            suggested_fix = self._get_auth_fix_suggestion(service_id, auth_scheme)

            raise AuthenticationError(
                message=f"Authentication failed for {service_id}: {str(e)}",
                service_id=service_id,
                auth_type=auth_scheme,
                suggested_fix=suggested_fix,
                config_status=config_status
            )

    def _handle_api_key_auth(self, service_id: str) -> Dict[str, Any]:
        """Handle API key authentication for services like NASA_POWER, EPA_AQS, OpenAQ"""
        credentials = self.config_manager.get_service_credentials(service_id)
        service_config = self.config_manager.get_service_config(service_id)

        # Different services use different API key formats
        if service_id == 'NASA_POWER':
            # NASA POWER uses email + key
            email = credentials.get('email')
            api_key = credentials.get('key')
            if not email or not api_key:
                raise ValueError(f"NASA POWER requires 'email' and 'key' in credentials")

            return {
                'authenticated': True,
                'auth_type': 'api_key',
                'headers': {
                    'User-Agent': f'env-agents/{service_id}',
                },
                'params': {
                    'user': email,
                    'key': api_key,
                    'format': 'JSON'  # NASA POWER specific
                },
                'session_config': {
                    'timeout': service_config.get('timeout', 30)
                },
                'service_config': service_config,
                'metadata': {
                    'email': email,
                    'key_length': len(api_key) if api_key else 0
                }
            }

        elif service_id == 'EPA_AQS':
            # EPA AQS uses email + key
            email = credentials.get('email')
            api_key = credentials.get('key')
            if not email or not api_key:
                raise ValueError(f"EPA AQS requires 'email' and 'key' in credentials")

            return {
                'authenticated': True,
                'auth_type': 'api_key',
                'headers': {
                    'User-Agent': f'env-agents/{service_id}',
                },
                'params': {
                    'email': email,
                    'key': api_key
                },
                'session_config': {
                    'timeout': service_config.get('timeout', 30)
                },
                'service_config': service_config,
                'metadata': {
                    'email': email,
                    'key_length': len(api_key) if api_key else 0
                }
            }

        elif service_id == 'OpenAQ':
            # OpenAQ uses API key in header
            api_key = credentials.get('api_key')
            if not api_key:
                raise ValueError(f"OpenAQ requires 'api_key' in credentials")

            return {
                'authenticated': True,
                'auth_type': 'api_key',
                'headers': {
                    'User-Agent': f'env-agents/{service_id}',
                    'X-API-Key': api_key
                },
                'params': {},
                'session_config': {
                    'timeout': service_config.get('timeout', 30)
                },
                'service_config': service_config,
                'metadata': {
                    'key_length': len(api_key) if api_key else 0
                }
            }

        else:
            raise ValueError(f"Unknown API key service: {service_id}")

    def _handle_service_account_auth(self, service_id: str) -> Dict[str, Any]:
        """Handle service account authentication for Earth Engine"""
        if service_id != 'EARTH_ENGINE':
            raise ValueError(f"Service account auth only supported for EARTH_ENGINE, got {service_id}")

        credentials = self.config_manager.get_service_credentials(service_id)
        service_config = self.config_manager.get_service_config(service_id)

        # Earth Engine can use service account or user authentication
        service_account_path = credentials.get('service_account_path')
        project_id = credentials.get('project_id')

        if service_account_path and Path(service_account_path).exists():
            # Service account authentication
            return {
                'authenticated': True,
                'auth_type': 'service_account',
                'headers': {
                    'User-Agent': f'env-agents/{service_id}',
                },
                'params': {},
                'session_config': {},
                'service_config': service_config,
                'metadata': {
                    'service_account_path': service_account_path,
                    'project_id': project_id,
                    'auth_method': 'service_account'
                },
                'ee_auth_config': {
                    'service_account_path': service_account_path,
                    'project_id': project_id
                }
            }
        else:
            # User authentication (requires manual ee.Authenticate())
            return {
                'authenticated': True,
                'auth_type': 'user_auth',
                'headers': {
                    'User-Agent': f'env-agents/{service_id}',
                },
                'params': {},
                'session_config': {},
                'service_config': service_config,
                'metadata': {
                    'auth_method': 'user_auth',
                    'requires_manual_auth': True
                },
                'ee_auth_config': {
                    'use_user_auth': True
                }
            }

    def _handle_no_auth(self, service_id: str) -> Dict[str, Any]:
        """Handle services that don't require authentication"""
        service_config = self.config_manager.get_service_config(service_id)

        return {
            'authenticated': True,
            'auth_type': 'none',
            'headers': {
                'User-Agent': f'env-agents/{service_id}',
            },
            'params': {},
            'session_config': {
                'timeout': service_config.get('timeout', 30)
            },
            'service_config': service_config,
            'metadata': {
                'requires_auth': False
            }
        }

    def _handle_oauth_auth(self, service_id: str) -> Dict[str, Any]:
        """Handle OAuth authentication (placeholder for future services)"""
        raise NotImplementedError("OAuth authentication not yet implemented")

    def _is_auth_valid(self, auth_context: Dict[str, Any]) -> bool:
        """Check if cached authentication is still valid"""
        if 'authenticated_at' not in auth_context:
            return False

        # Simple time-based validity (could be enhanced per service)
        auth_time = auth_context['authenticated_at']
        max_age = timedelta(hours=1)  # Auth valid for 1 hour

        return datetime.utcnow() - auth_time < max_age

    def _get_config_status(self, service_id: str) -> Dict[str, Any]:
        """Get configuration status for error reporting"""
        try:
            credentials = self.config_manager.get_service_credentials(service_id)
            service_config = self.config_manager.get_service_config(service_id)

            return {
                'has_credentials': bool(credentials),
                'has_service_config': bool(service_config),
                'credential_keys': list(credentials.keys()) if credentials else [],
                'config_keys': list(service_config.keys()) if service_config else []
            }
        except:
            return {'status': 'config_error'}

    def _get_auth_fix_suggestion(self, service_id: str, auth_type: str) -> str:
        """Generate helpful fix suggestions for authentication failures"""
        if auth_type == 'api_key':
            if service_id == 'NASA_POWER':
                return "Register at https://power.larc.nasa.gov/data-access-viewer/ and add 'email' and 'key' to credentials.yaml"
            elif service_id == 'EPA_AQS':
                return "Register at https://aqs.epa.gov/aqsweb/documents/data_api.html and add 'email' and 'key' to credentials.yaml"
            elif service_id == 'OpenAQ':
                return "Get API key from https://docs.openaq.org/ and add 'api_key' to credentials.yaml"
        elif auth_type == 'service_account':
            return "Set up Google Earth Engine service account and add 'service_account_path' to credentials.yaml"

        return f"Check {service_id} authentication configuration in credentials.yaml"

    def clear_auth_cache(self, service_id: str = None):
        """Clear authentication cache for a service or all services"""
        if service_id:
            self._auth_cache.pop(service_id, None)
        else:
            self._auth_cache.clear()

    def get_auth_status(self) -> Dict[str, str]:
        """Get authentication status for all services"""
        status = {}
        for service_id in self.auth_schemes:
            try:
                auth_context = self.authenticate_service(service_id)
                status[service_id] = 'authenticated' if auth_context['authenticated'] else 'failed'
            except AuthenticationError:
                status[service_id] = 'failed'
            except Exception:
                status[service_id] = 'error'

        return status