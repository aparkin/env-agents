"""
Service-specific caching system for env-agents
Provides intelligent caching for metadata, parameter lists, and geographic data
"""

import json
import time
import hashlib
import logging
from pathlib import Path
from typing import Any, Dict, Optional, Union, Callable
from datetime import datetime, timedelta


class ServiceCache:
    """Service-specific cache with TTL and intelligent invalidation"""
    
    def __init__(self, service_name: str, cache_dir: str = "data/cache", default_ttl: int = 604800):
        """
        Initialize service cache
        
        Args:
            service_name: Name of the service (e.g., 'EPA_AQS', 'US_EIA')
            cache_dir: Directory for cache files
            default_ttl: Default TTL in seconds (default: 7 days)
        """
        self.service_name = service_name
        
        # Resolve cache directory relative to project root, not current working directory
        if not Path(cache_dir).is_absolute():
            # Find project root by looking for setup.py or pyproject.toml
            current = Path(__file__).parent
            while current != current.parent:
                if (current / "setup.py").exists() or (current / "pyproject.toml").exists():
                    cache_dir = str(current / cache_dir)
                    break
                current = current.parent
        
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.default_ttl = default_ttl
        self.logger = logging.getLogger(f"cache.{service_name.lower()}")
        
        # Cache file paths
        self.metadata_cache = self.cache_dir / f"{service_name.lower()}_metadata.json"
        self.parameters_cache = self.cache_dir / f"{service_name.lower()}_parameters.json"
        self.geographic_cache = self.cache_dir / f"{service_name.lower()}_geographic.json"
    
    def get(self, key: str, cache_type: str = "metadata") -> Optional[Any]:
        """
        Get value from cache
        
        Args:
            key: Cache key
            cache_type: Type of cache ("metadata", "parameters", "geographic")
            
        Returns:
            Cached value or None if not found/expired
        """
        cache_file = self._get_cache_file(cache_type)
        
        if not cache_file.exists():
            return None
        
        try:
            with open(cache_file, 'r') as f:
                cache_data = json.load(f)
            
            if key not in cache_data:
                return None
            
            entry = cache_data[key]
            
            # Check TTL
            if self._is_expired(entry):
                self.logger.debug(f"Cache entry '{key}' expired")
                return None
            
            self.logger.debug(f"Cache hit for '{key}' in {cache_type}")
            return entry['value']
            
        except Exception as e:
            self.logger.warning(f"Failed to read cache for '{key}': {e}")
            return None
    
    def set(self, key: str, value: Any, cache_type: str = "metadata", ttl: Optional[int] = None) -> None:
        """
        Set value in cache
        
        Args:
            key: Cache key
            value: Value to cache
            cache_type: Type of cache ("metadata", "parameters", "geographic")
            ttl: TTL in seconds (uses default if None)
        """
        cache_file = self._get_cache_file(cache_type)
        ttl = ttl or self.default_ttl
        
        try:
            # Load existing cache
            cache_data = {}
            if cache_file.exists():
                with open(cache_file, 'r') as f:
                    cache_data = json.load(f)
            
            # Add new entry
            cache_data[key] = {
                'value': value,
                'timestamp': time.time(),
                'ttl': ttl
            }
            
            # Write back to file
            with open(cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2, default=str)
            
            self.logger.debug(f"Cached '{key}' in {cache_type} with TTL {ttl}s")
            
        except Exception as e:
            self.logger.error(f"Failed to cache '{key}': {e}")
    
    def get_or_fetch(self, key: str, fetch_func: Callable, cache_type: str = "metadata", ttl: Optional[int] = None) -> Any:
        """
        Get from cache or fetch and cache
        
        Args:
            key: Cache key
            fetch_func: Function to call if not cached
            cache_type: Type of cache
            ttl: TTL in seconds
            
        Returns:
            Cached or freshly fetched value
        """
        # Try cache first
        cached_value = self.get(key, cache_type)
        if cached_value is not None:
            return cached_value
        
        # Fetch fresh data
        try:
            self.logger.debug(f"Cache miss for '{key}', fetching...")
            fresh_value = fetch_func()
            
            # Cache the result
            if fresh_value is not None:
                self.set(key, fresh_value, cache_type, ttl)
            
            return fresh_value
            
        except Exception as e:
            self.logger.error(f"Failed to fetch data for '{key}': {e}")
            raise
    
    def invalidate(self, key: Optional[str] = None, cache_type: Optional[str] = None) -> None:
        """
        Invalidate cache entries
        
        Args:
            key: Specific key to invalidate (None = all keys in cache_type)
            cache_type: Cache type to invalidate (None = all cache types)
        """
        if cache_type is None:
            # Invalidate all cache types
            for ct in ["metadata", "parameters", "geographic"]:
                self.invalidate(key, ct)
            return
        
        cache_file = self._get_cache_file(cache_type)
        
        if not cache_file.exists():
            return
        
        try:
            if key is None:
                # Invalidate entire cache file
                cache_file.unlink()
                self.logger.info(f"Invalidated all {cache_type} cache")
            else:
                # Invalidate specific key
                with open(cache_file, 'r') as f:
                    cache_data = json.load(f)
                
                if key in cache_data:
                    del cache_data[key]
                    
                    with open(cache_file, 'w') as f:
                        json.dump(cache_data, f, indent=2, default=str)
                    
                    self.logger.info(f"Invalidated '{key}' from {cache_type} cache")
                
        except Exception as e:
            self.logger.error(f"Failed to invalidate cache: {e}")
    
    def cleanup_expired(self) -> int:
        """
        Remove expired entries from all cache files
        
        Returns:
            Number of entries removed
        """
        removed_count = 0
        
        for cache_type in ["metadata", "parameters", "geographic"]:
            cache_file = self._get_cache_file(cache_type)
            
            if not cache_file.exists():
                continue
            
            try:
                with open(cache_file, 'r') as f:
                    cache_data = json.load(f)
                
                # Find expired entries
                expired_keys = []
                for key, entry in cache_data.items():
                    if self._is_expired(entry):
                        expired_keys.append(key)
                
                # Remove expired entries
                for key in expired_keys:
                    del cache_data[key]
                    removed_count += 1
                
                if expired_keys:
                    with open(cache_file, 'w') as f:
                        json.dump(cache_data, f, indent=2, default=str)
                    
                    self.logger.info(f"Removed {len(expired_keys)} expired entries from {cache_type}")
                
            except Exception as e:
                self.logger.error(f"Failed to cleanup {cache_type} cache: {e}")
        
        return removed_count
    
    def cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        stats = {
            'service': self.service_name,
            'cache_types': {}
        }
        
        for cache_type in ["metadata", "parameters", "geographic"]:
            cache_file = self._get_cache_file(cache_type)
            
            if not cache_file.exists():
                stats['cache_types'][cache_type] = {
                    'exists': False,
                    'total_entries': 0,
                    'expired_entries': 0
                }
                continue
            
            try:
                with open(cache_file, 'r') as f:
                    cache_data = json.load(f)
                
                total_entries = len(cache_data)
                expired_entries = sum(1 for entry in cache_data.values() if self._is_expired(entry))
                
                stats['cache_types'][cache_type] = {
                    'exists': True,
                    'file_size': cache_file.stat().st_size,
                    'total_entries': total_entries,
                    'expired_entries': expired_entries,
                    'valid_entries': total_entries - expired_entries
                }
                
            except Exception as e:
                stats['cache_types'][cache_type] = {
                    'exists': True,
                    'error': str(e)
                }
        
        return stats
    
    def _get_cache_file(self, cache_type: str) -> Path:
        """Get cache file path for given type"""
        if cache_type == "metadata":
            return self.metadata_cache
        elif cache_type == "parameters":
            return self.parameters_cache
        elif cache_type == "geographic":
            return self.geographic_cache
        else:
            raise ValueError(f"Unknown cache type: {cache_type}")
    
    def _is_expired(self, entry: Dict[str, Any]) -> bool:
        """Check if cache entry is expired"""
        timestamp = entry.get('timestamp', 0)
        ttl = entry.get('ttl', self.default_ttl)
        return time.time() > timestamp + ttl
    
    @staticmethod
    def create_geographic_key(geometry: Dict[str, Any], radius_km: Optional[float] = None) -> str:
        """Create consistent cache key for geographic queries"""
        geo_string = f"{geometry['type']}:{geometry['coordinates']}"
        if radius_km:
            geo_string += f":{radius_km}km"
        
        return hashlib.md5(geo_string.encode()).hexdigest()[:16]
    
    @staticmethod 
    def create_parameter_key(service_params: Dict[str, Any]) -> str:
        """Create consistent cache key for parameter combinations"""
        # Sort parameters for consistent hashing
        sorted_params = json.dumps(service_params, sort_keys=True)
        return hashlib.md5(sorted_params.encode()).hexdigest()[:16]


class CacheManager:
    """Global cache manager for all services"""
    
    def __init__(self, cache_dir: str = "data/cache"):
        # Resolve cache directory relative to project root, not current working directory
        if not Path(cache_dir).is_absolute():
            # Find project root by looking for setup.py or pyproject.toml
            current = Path(__file__).parent
            while current != current.parent:
                if (current / "setup.py").exists() or (current / "pyproject.toml").exists():
                    cache_dir = str(current / cache_dir)
                    break
                current = current.parent
        
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.service_caches: Dict[str, ServiceCache] = {}
        self.logger = logging.getLogger("cache_manager")
    
    def get_service_cache(self, service_name: str) -> ServiceCache:
        """Get or create service cache"""
        if service_name not in self.service_caches:
            self.service_caches[service_name] = ServiceCache(
                service_name, 
                str(self.cache_dir)
            )
        
        return self.service_caches[service_name]
    
    def cleanup_all_expired(self) -> Dict[str, int]:
        """Cleanup expired entries from all service caches"""
        results = {}
        
        for service_name, cache in self.service_caches.items():
            removed_count = cache.cleanup_expired()
            results[service_name] = removed_count
        
        return results
    
    def global_stats(self) -> Dict[str, Any]:
        """Get statistics for all service caches"""
        stats = {
            'total_services': len(self.service_caches),
            'cache_directory': str(self.cache_dir),
            'services': {}
        }
        
        for service_name, cache in self.service_caches.items():
            stats['services'][service_name] = cache.cache_stats()
        
        return stats
    
    def invalidate_service(self, service_name: str) -> None:
        """Invalidate all caches for a service"""
        if service_name in self.service_caches:
            cache = self.service_caches[service_name]
            cache.invalidate()  # Invalidate all cache types
            self.logger.info(f"Invalidated all caches for {service_name}")


# Global cache manager instance
global_cache = CacheManager()