"""
Standard adapter mixins for unified functionality.

Provides reusable components that adapters can inherit to get
standardized authentication, configuration, and error handling.
"""

import logging
from typing import Dict, Any, Optional
from .config import ConfigManager
from .auth import AuthenticationManager, AuthenticationError


class StandardAuthMixin:
    """
    Standard authentication mixin for all adapters.

    Provides unified authentication setup that works with the
    AuthenticationManager abstraction layer. All adapters can
    inherit this to get consistent auth behavior.

    Usage:
        class MyAdapter(BaseAdapter, StandardAuthMixin):
            DATASET = "MY_SERVICE"
            # ... rest of implementation
    """

    def _setup_authentication(self):
        """
        Setup authentication using unified auth manager.

        This method provides standardized authentication setup that:
        1. Uses AuthenticationManager for service-specific auth
        2. Configures requests session with auth context
        3. Applies service configuration (timeouts, etc.)
        4. Provides rich error messages on auth failures

        Called automatically during adapter initialization.
        """
        if not hasattr(self, 'DATASET'):
            raise AttributeError(f"{self.__class__.__name__} must define DATASET constant")

        if not hasattr(self, '_session'):
            raise AttributeError(f"{self.__class__.__name__} must have _session attribute from BaseAdapter")

        try:
            # Initialize config and auth managers if not already done
            if not hasattr(self, 'config_manager'):
                self.config_manager = ConfigManager()
            if not hasattr(self, 'auth_manager'):
                self.auth_manager = AuthenticationManager(self.config_manager)

            # Authenticate service
            self.auth_context = self.auth_manager.authenticate_service(self.DATASET)

            # Configure requests session with auth context
            auth_headers = self.auth_context.get('headers', {})
            auth_params = self.auth_context.get('params', {})
            session_config = self.auth_context.get('session_config', {})

            # Apply authentication to session
            self._session.headers.update(auth_headers)
            if hasattr(self._session, 'params'):
                self._session.params.update(auth_params)
            else:
                # Some session types don't support params - store for manual use
                self._auth_params = auth_params

            # Apply session configuration (timeout, etc.)
            if 'timeout' in session_config:
                self._session.timeout = session_config['timeout']

            # Store service configuration for adapter use
            self.service_config = self.auth_context.get('service_config', {})

            # Success logging
            auth_type = self.auth_context.get('auth_type', 'unknown')
            self.logger.info(f"Authentication successful for {self.DATASET} ({auth_type})")

        except AuthenticationError as e:
            self.logger.error(f"Authentication failed for {self.DATASET}: {e}")
            self.logger.error(f"Suggested fix: {e.suggested_fix}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected authentication error for {self.DATASET}: {e}")
            raise AuthenticationError(
                message=f"Authentication setup failed: {str(e)}",
                service_id=self.DATASET,
                auth_type="unknown"
            )

    def _initialize_standard_components(self):
        """
        Initialize standard adapter components.

        Sets up logging, config manager, auth manager, and auth context.
        Should be called in adapter __init__ after super().__init__().
        """
        # Setup logging
        self.logger = logging.getLogger(f"adapter.{self.DATASET.lower()}")

        # Initialize configuration and authentication
        self.config_manager = ConfigManager()
        self.auth_manager = AuthenticationManager(self.config_manager)
        self.auth_context = None
        self.service_config = {}

        # Setup authentication
        self._setup_authentication()

    def get_authenticated_session_params(self) -> Dict[str, Any]:
        """
        Get authentication parameters for manual session requests.

        Useful for adapters that need to construct requests manually
        rather than using the pre-configured session.

        Returns:
            Dict with authentication parameters to include in requests
        """
        if hasattr(self, '_auth_params'):
            return self._auth_params
        return self.auth_context.get('params', {}) if self.auth_context else {}

    def is_authenticated(self) -> bool:
        """Check if adapter is successfully authenticated"""
        return (
            self.auth_context is not None and
            self.auth_context.get('authenticated', False)
        )

    def get_auth_status(self) -> Dict[str, Any]:
        """Get detailed authentication status for debugging"""
        if not self.auth_context:
            return {'status': 'not_initialized'}

        return {
            'status': 'authenticated' if self.is_authenticated() else 'failed',
            'auth_type': self.auth_context.get('auth_type', 'unknown'),
            'service': self.DATASET,
            'metadata': self.auth_context.get('metadata', {})
        }


class StandardErrorMixin:
    """
    Standard error handling mixin for adapters.

    Provides consistent error messages and logging patterns.
    """

    def _handle_api_error(self, response, context: str = "API call"):
        """
        Handle API response errors with rich context.

        Args:
            response: requests.Response object
            context: Description of what was being attempted
        """
        try:
            response.raise_for_status()
        except Exception as e:
            error_msg = f"{context} failed for {self.DATASET}"

            # Add response details
            if hasattr(response, 'status_code'):
                error_msg += f" (HTTP {response.status_code})"

            # Add response body if available
            try:
                if response.headers.get('content-type', '').startswith('application/json'):
                    error_details = response.json()
                    error_msg += f": {error_details.get('message', str(error_details))}"
                else:
                    error_msg += f": {response.text[:200]}"
            except:
                error_msg += f": {str(e)}"

            self.logger.error(error_msg)
            raise Exception(error_msg)


class StandardConfigMixin:
    """
    Standard configuration access mixin.

    Provides consistent configuration access patterns.
    """

    def get_service_setting(self, key: str, default: Any = None) -> Any:
        """Get a service-specific configuration setting"""
        if hasattr(self, 'service_config'):
            return self.service_config.get(key, default)
        return default

    def get_rate_limit_config(self) -> Dict[str, Any]:
        """Get rate limiting configuration for this service"""
        return self.get_service_setting('rate_limit', {})

    def get_timeout_config(self) -> int:
        """Get timeout configuration for this service"""
        return self.get_service_setting('timeout', 30)


class StandardAdapterMixin(StandardAuthMixin, StandardErrorMixin, StandardConfigMixin):
    """
    Combined mixin that provides all standard adapter functionality.

    Single mixin that adapters can inherit to get:
    - Unified authentication
    - Consistent error handling
    - Configuration access
    - Standard logging patterns

    Usage:
        class MyAdapter(BaseAdapter, StandardAdapterMixin):
            DATASET = "MY_SERVICE"

            def __init__(self):
                super().__init__()
                self._initialize_standard_components()  # One line setup
                # ... adapter-specific initialization
    """

    def initialize_adapter(self):
        """
        Complete adapter initialization with all standard components.

        Convenience method that sets up everything needed for a
        standardized adapter. Call this in __init__ after super().__init__().
        """
        self._initialize_standard_components()
        self.logger.info(f"{self.__class__.__name__} initialized successfully")