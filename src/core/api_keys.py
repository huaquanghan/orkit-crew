"""API Key management for Orkit Crew API.

This module provides API key generation, rotation, and revocation.
"""

from __future__ import annotations

import hashlib
import secrets
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any


class APIKeyStatus(str, Enum):
    """API key status."""

    ACTIVE = "active"
    REVOKED = "revoked"
    EXPIRED = "expired"


@dataclass
class APIKey:
    """API Key model.

    Attributes:
        id: Unique key identifier
        key_hash: Hashed API key (the actual key is only shown once on creation)
        user_id: Owner user ID
        name: Human-readable key name
        status: Key status
        created_at: Creation timestamp
        expires_at: Optional expiration timestamp
        last_used_at: Last usage timestamp
        rate_limit: Requests per minute limit (None = unlimited)
        permissions: List of allowed permissions
        metadata: Additional metadata
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    key_hash: str = ""
    user_id: str = ""
    name: str = ""
    status: APIKeyStatus = APIKeyStatus.ACTIVE
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: datetime | None = None
    last_used_at: datetime | None = None
    rate_limit: int | None = None  # requests per minute
    permissions: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self, include_sensitive: bool = False) -> dict[str, Any]:
        """Convert API key to dictionary.

        Args:
            include_sensitive: Whether to include sensitive fields

        Returns:
            Dictionary representation
        """
        result = {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
            "rate_limit": self.rate_limit,
            "permissions": self.permissions,
            "metadata": self.metadata,
        }
        if include_sensitive:
            result["key_hash"] = self.key_hash
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> APIKey:
        """Create API key from dictionary."""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            key_hash=data.get("key_hash", ""),
            user_id=data.get("user_id", ""),
            name=data.get("name", ""),
            status=APIKeyStatus(data.get("status", "active")),
            created_at=datetime.fromisoformat(data["created_at"])
            if "created_at" in data
            else datetime.utcnow(),
            expires_at=datetime.fromisoformat(data["expires_at"]) if data.get("expires_at") else None,
            last_used_at=datetime.fromisoformat(data["last_used_at"])
            if data.get("last_used_at")
            else None,
            rate_limit=data.get("rate_limit"),
            permissions=data.get("permissions", []),
            metadata=data.get("metadata", {}),
        )

    def is_valid(self) -> bool:
        """Check if key is valid (active and not expired)."""
        if self.status != APIKeyStatus.ACTIVE:
            return False
        if self.expires_at and datetime.utcnow() > self.expires_at:
            return False
        return True

    def record_usage(self) -> None:
        """Record key usage."""
        self.last_used_at = datetime.utcnow()


class APIKeyManager:
    """Manager for API key operations."""

    def __init__(self, redis_client: Any | None = None):
        """Initialize API key manager.

        Args:
            redis_client: Optional Redis client for persistence
        """
        self._keys: dict[str, APIKey] = {}  # key_id -> APIKey
        self._key_hash_index: dict[str, str] = {}  # key_hash -> key_id
        self._user_keys: dict[str, set[str]] = {}  # user_id -> set of key_ids
        self._redis = redis_client

    def _generate_key(self) -> tuple[str, str]:
        """Generate a new API key and its hash.

        Returns:
            Tuple of (raw_key, key_hash)
        """
        # Generate a secure random key
        raw_key = f"orkit_{secrets.token_urlsafe(32)}"
        # Hash the key for storage
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        return raw_key, key_hash

    def _hash_key(self, raw_key: str) -> str:
        """Hash a raw API key."""
        return hashlib.sha256(raw_key.encode()).hexdigest()

    async def create_key(
        self,
        user_id: str,
        name: str,
        expires_in_days: int | None = None,
        rate_limit: int | None = None,
        permissions: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> tuple[APIKey, str]:
        """Create a new API key.

        Args:
            user_id: Owner user ID
            name: Human-readable key name
            expires_in_days: Optional expiration in days
            rate_limit: Optional rate limit (requests per minute)
            permissions: Optional list of permissions
            metadata: Optional metadata

        Returns:
            Tuple of (APIKey, raw_key) - raw_key is only shown once!
        """
        raw_key, key_hash = self._generate_key()

        expires_at = None
        if expires_in_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_in_days)

        api_key = APIKey(
            key_hash=key_hash,
            user_id=user_id,
            name=name,
            expires_at=expires_at,
            rate_limit=rate_limit,
            permissions=permissions or [],
            metadata=metadata or {},
        )

        # Store key
        self._keys[api_key.id] = api_key
        self._key_hash_index[key_hash] = api_key.id

        # Add to user's keys
        if user_id not in self._user_keys:
            self._user_keys[user_id] = set()
        self._user_keys[user_id].add(api_key.id)

        # Persist to Redis if available
        if self._redis:
            await self._persist_key(api_key)

        return api_key, raw_key

    async def get_key(self, key_id: str) -> APIKey | None:
        """Get API key by ID."""
        # Try memory first
        if key_id in self._keys:
            return self._keys[key_id]

        # Try Redis if available
        if self._redis:
            key_data = await self._redis.get(f"apikey:{key_id}")
            if key_data:
                import json

                data = json.loads(key_data.decode() if isinstance(key_data, bytes) else key_data)
                key = APIKey.from_dict(data)
                self._keys[key_id] = key
                self._key_hash_index[key.key_hash] = key_id
                return key

        return None

    async def get_key_by_hash(self, key_hash: str) -> APIKey | None:
        """Get API key by its hash."""
        key_id = self._key_hash_index.get(key_hash)
        if key_id:
            return await self.get_key(key_id)

        # Try Redis if available
        if self._redis:
            key_id = await self._redis.get(f"apikey:hash:{key_hash}")
            if key_id:
                return await self.get_key(key_id.decode() if isinstance(key_id, bytes) else key_id)

        return None

    async def validate_key(self, raw_key: str) -> APIKey | None:
        """Validate a raw API key.

        Args:
            raw_key: The raw API key to validate

        Returns:
            APIKey if valid, None otherwise
        """
        key_hash = self._hash_key(raw_key)
        api_key = await self.get_key_by_hash(key_hash)

        if not api_key:
            return None

        if not api_key.is_valid():
            return None

        # Record usage
        api_key.record_usage()
        if self._redis:
            await self._persist_key(api_key)

        return api_key

    async def revoke_key(self, key_id: str) -> bool:
        """Revoke an API key.

        Args:
            key_id: Key identifier

        Returns:
            True if revoked successfully
        """
        api_key = await self.get_key(key_id)
        if not api_key:
            return False

        api_key.status = APIKeyStatus.REVOKED

        if self._redis:
            await self._persist_key(api_key)

        return True

    async def rotate_key(self, key_id: str) -> tuple[APIKey, str] | None:
        """Rotate an API key (revoke old and create new).

        Args:
            key_id: Key identifier to rotate

        Returns:
            Tuple of (new_APIKey, raw_key) if successful, None otherwise
        """
        old_key = await self.get_key(key_id)
        if not old_key:
            return None

        # Revoke old key
        await self.revoke_key(key_id)

        # Create new key with same settings
        return await self.create_key(
            user_id=old_key.user_id,
            name=f"{old_key.name} (rotated)",
            expires_in_days=None,  # Will be calculated from old key if needed
            rate_limit=old_key.rate_limit,
            permissions=old_key.permissions,
            metadata=old_key.metadata,
        )

    async def list_user_keys(self, user_id: str) -> list[APIKey]:
        """List all API keys for a user.

        Args:
            user_id: User identifier

        Returns:
            List of API keys
        """
        key_ids = self._user_keys.get(user_id, set())
        keys = []
        for key_id in key_ids:
            key = await self.get_key(key_id)
            if key:
                keys.append(key)
        return keys

    async def delete_key(self, key_id: str) -> bool:
        """Delete an API key permanently.

        Args:
            key_id: Key identifier

        Returns:
            True if deleted successfully
        """
        api_key = await self.get_key(key_id)
        if not api_key:
            return False

        # Remove from indexes
        del self._keys[key_id]
        del self._key_hash_index[api_key.key_hash]
        if api_key.user_id in self._user_keys:
            self._user_keys[api_key.user_id].discard(key_id)

        # Remove from Redis if available
        if self._redis:
            await self._redis.delete(f"apikey:{key_id}")
            await self._redis.delete(f"apikey:hash:{api_key.key_hash}")
            await self._redis.srem(f"user:{api_key.user_id}:apikeys", key_id)

        return True

    async def _persist_key(self, api_key: APIKey) -> None:
        """Persist API key to Redis.

        Args:
            api_key: API key to persist
        """
        if not self._redis:
            return

        import json

        key_data = api_key.to_dict(include_sensitive=True)
        await self._redis.set(f"apikey:{api_key.id}", json.dumps(key_data))
        await self._redis.set(f"apikey:hash:{api_key.key_hash}", api_key.id)
        await self._redis.sadd(f"user:{api_key.user_id}:apikeys", api_key.id)

    async def load_from_redis(self) -> None:
        """Load all API keys from Redis."""
        if not self._redis:
            return

        import json

        # Get all API key keys
        keys = await self._redis.keys("apikey:*")
        for key in keys:
            key_str = key.decode() if isinstance(key, bytes) else key
            # Skip index keys
            if key_str.startswith("apikey:hash:"):
                continue
            if ":" in key_str[len("apikey:"):]:  # Skip user-specific keys
                continue

            key_data = await self._redis.get(key)
            if key_data:
                data = json.loads(key_data.decode() if isinstance(key_data, bytes) else key_data)
                api_key = APIKey.from_dict(data)
                self._keys[api_key.id] = api_key
                self._key_hash_index[api_key.key_hash] = api_key.id
                if api_key.user_id not in self._user_keys:
                    self._user_keys[api_key.user_id] = set()
                self._user_keys[api_key.user_id].add(api_key.id)


# Global API key manager instance
api_key_manager = APIKeyManager()
