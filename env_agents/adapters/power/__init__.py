# Package facade for NASA POWER
from .adapter import NASAPowerAdapter

# Legacy alias for backward compatibility
NASAPOWEREnhancedAdapter = NASAPowerAdapter
NasaPowerDailyAdapter = NASAPowerAdapter

__all__ = ["NASAPowerAdapter", "NASAPOWEREnhancedAdapter", "NasaPowerDailyAdapter"]