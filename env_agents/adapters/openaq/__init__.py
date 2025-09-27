# Package facade for OpenAQ v3
from .adapter import OpenAQAdapter

# Legacy aliases for backward compatibility
OpenaqV3Adapter = OpenAQAdapter

__all__ = ["OpenAQAdapter", "OpenaqV3Adapter"]