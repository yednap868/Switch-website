"""
Redis client utility for caching Claude API responses.
"""

import hashlib
import json
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import redis


class RedisCache:
    """Redis cache client for Claude API responses."""

    def __init__(self):
        """Initialize Redis connection."""
        try:
            self.redis_client = redis.Redis(
                host=os.getenv("REDIS_HOST", "localhost"),
                port=int(os.getenv("REDIS_PORT", 6379)),
                db=int(os.getenv("REDIS_DB", 0)),
                password=os.getenv("REDIS_PASSWORD", None),
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
            )

            # Test connection
            self.redis_client.ping()
            print("✅ [REDIS] Connected successfully")

        except Exception as e:
            print(f"❌ [REDIS] Connection failed: {e}")
            self.redis_client = None

    def is_available(self) -> bool:
        """Check if Redis is available."""
        if not self.redis_client:
            return False

        try:
            self.redis_client.ping()
            return True
        except:
            return False

    def _generate_cache_key(self, prefix: str, data: Dict[str, Any]) -> str:
        """Generate a consistent cache key from data."""
        # Create a hash of the data for consistent keys
        data_str = json.dumps(data, sort_keys=True)
        data_hash = hashlib.md5(data_str.encode()).hexdigest()[:12]
        return f"claude:{prefix}:{data_hash}"

    def _serialize_data(self, data: Any) -> str:
        """Serialize data for Redis storage."""
        if isinstance(data, (dict, list)):
            return json.dumps(data, default=str)
        return str(data)

    def _deserialize_data(self, data: str, data_type: type = dict) -> Any:
        """Deserialize data from Redis storage."""
        try:
            if data_type == dict:
                return json.loads(data)
            elif data_type == list:
                return json.loads(data)
            else:
                return data
        except (json.JSONDecodeError, TypeError):
            return data

    def get(self, key: str, data_type: type = dict) -> Optional[Any]:
        """Get data from cache."""
        if not self.is_available():
            return None

        try:
            cached_data = self.redis_client.get(key)
            if cached_data:
                print(f"🎯 [CACHE] Hit for key: {key}")
                return self._deserialize_data(cached_data, data_type)
            else:
                print(f"❌ [CACHE] Miss for key: {key}")
                return None
        except Exception as e:
            print(f"⚠️ [CACHE] Error getting key {key}: {e}")
            return None

    def set(self, key: str, data: Any, ttl_seconds: int = 21600) -> bool:
        """Set data in cache with TTL."""
        if not self.is_available():
            return False

        try:
            serialized_data = self._serialize_data(data)
            result = self.redis_client.setex(key, ttl_seconds, serialized_data)
            if result:
                print(f"💾 [CACHE] Stored key: {key} (TTL: {ttl_seconds}s)")
                return True
            return False
        except Exception as e:
            print(f"⚠️ [CACHE] Error setting key {key}: {e}")
            return False

    def delete(self, key: str) -> bool:
        """Delete data from cache."""
        if not self.is_available():
            return False

        try:
            result = self.redis_client.delete(key)
            if result:
                print(f"🗑️ [CACHE] Deleted key: {key}")
                return True
            return False
        except Exception as e:
            print(f"⚠️ [CACHE] Error deleting key {key}: {e}")
            return False

    def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching a pattern."""
        if not self.is_available():
            return 0

        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                deleted = self.redis_client.delete(*keys)
                print(f"🗑️ [CACHE] Cleared {deleted} keys matching pattern: {pattern}")
                return deleted
            return 0
        except Exception as e:
            print(f"⚠️ [CACHE] Error clearing pattern {pattern}: {e}")
            return 0

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        if not self.is_available():
            return {"status": "unavailable"}

        try:
            info = self.redis_client.info()
            return {
                "status": "available",
                "connected_clients": info.get("connected_clients", 0),
                "used_memory_human": info.get("used_memory_human", "0B"),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "total_commands_processed": info.get("total_commands_processed", 0),
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}


# Global Redis cache instance
redis_cache = RedisCache()


def get_cache_key_for_intent_classification(urgent_needs: str) -> str:
    """Generate cache key for intent classification."""
    data = {"urgent_needs": urgent_needs}
    return redis_cache._generate_cache_key("intent", data)


def get_cache_key_for_profile_matches(
    user_intent: str,
    user_urgent_needs: str,
    available_profiles: List[Dict],
    user_profile_summary: Optional[str] = None,
) -> str:
    """Generate cache key for profile matches."""
    # Create a simplified profile summary for consistent hashing
    profile_summary = []
    for profile in available_profiles[:20]:  # Limit to first 20 for consistent hashing
        profile_summary.append(
            {
                "name": profile.get("name", ""),
                "intent": profile.get("intent", ""),
                "urgent_needs": profile.get("urgent_needs", "")[
                    :100
                ],  # Truncate for consistency
            }
        )

    data = {
        "user_intent": user_intent,
        "user_urgent_needs": user_urgent_needs,
        "user_profile_summary": user_profile_summary or "",
        "profile_count": len(available_profiles),
        "profile_summary": profile_summary,
    }
    return redis_cache._generate_cache_key("matches", data)


def get_cache_key_for_business_context(user_intent: str, user_urgent_needs: str) -> str:
    """Generate cache key for business context analysis."""
    data = {"user_intent": user_intent, "user_urgent_needs": user_urgent_needs}
    return redis_cache._generate_cache_key("context", data)
