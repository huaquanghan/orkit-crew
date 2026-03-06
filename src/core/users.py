"""User management for Orkit Crew API.

This module provides user models, user management, and role-based access control.
"""

from __future__ import annotations

import hashlib
import secrets
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class UserRole(str, Enum):
    """User roles for role-based access control."""

    ADMIN = "admin"
    USER = "user"
    READONLY = "readonly"


@dataclass
class User:
    """User model for Orkit Crew API.

    Attributes:
        id: Unique user identifier
        username: Unique username
        email: User email address
        role: User role (admin, user, readonly)
        password_hash: Hashed password
        is_active: Whether the user account is active
        created_at: Account creation timestamp
        updated_at: Last update timestamp
        metadata: Additional user metadata
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    username: str = ""
    email: str = ""
    role: UserRole = UserRole.USER
    password_hash: str = ""
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self, include_sensitive: bool = False) -> dict[str, Any]:
        """Convert user to dictionary.

        Args:
            include_sensitive: Whether to include sensitive fields

        Returns:
            Dictionary representation of user
        """
        result = {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "role": self.role.value,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata,
        }
        if include_sensitive:
            result["password_hash"] = self.password_hash
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> User:
        """Create user from dictionary.

        Args:
            data: Dictionary containing user data

        Returns:
            User instance
        """
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            username=data.get("username", ""),
            email=data.get("email", ""),
            role=UserRole(data.get("role", "user")),
            password_hash=data.get("password_hash", ""),
            is_active=data.get("is_active", True),
            created_at=datetime.fromisoformat(data["created_at"])
            if "created_at" in data
            else datetime.utcnow(),
            updated_at=datetime.fromisoformat(data["updated_at"])
            if "updated_at" in data
            else datetime.utcnow(),
            metadata=data.get("metadata", {}),
        )

    def has_permission(self, required_role: UserRole) -> bool:
        """Check if user has required permission level.

        Args:
            required_role: Minimum required role

        Returns:
            True if user has permission
        """
        role_hierarchy = {
            UserRole.READONLY: 0,
            UserRole.USER: 1,
            UserRole.ADMIN: 2,
        }
        return role_hierarchy.get(self.role, 0) >= role_hierarchy.get(required_role, 0)

    def is_admin(self) -> bool:
        """Check if user is admin."""
        return self.role == UserRole.ADMIN


class UserManager:
    """Manager for user operations.

    Handles user CRUD operations with Redis storage.
    """

    def __init__(self, redis_client: Any | None = None):
        """Initialize user manager.

        Args:
            redis_client: Optional Redis client for persistence
        """
        self._users: dict[str, User] = {}  # id -> User
        self._username_index: dict[str, str] = {}  # username -> user_id
        self._email_index: dict[str, str] = {}  # email -> user_id
        self._redis = redis_client

    def _hash_password(self, password: str) -> str:
        """Hash a password using PBKDF2.

        Args:
            password: Plain text password

        Returns:
            Hashed password with salt
        """
        salt = secrets.token_hex(16)
        pwdhash = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000)
        return salt + pwdhash.hex()

    def _verify_password(self, password: str, password_hash: str) -> bool:
        """Verify a password against its hash.

        Args:
            password: Plain text password
            password_hash: Stored password hash

        Returns:
            True if password matches
        """
        salt = password_hash[:32]
        stored_hash = password_hash[32:]
        pwdhash = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000)
        return pwdhash.hex() == stored_hash

    async def create_user(
        self,
        username: str,
        email: str,
        password: str,
        role: UserRole = UserRole.USER,
        metadata: dict[str, Any] | None = None,
    ) -> User:
        """Create a new user.

        Args:
            username: Unique username
            email: User email
            password: Plain text password
            role: User role
            metadata: Optional metadata

        Returns:
            Created user

        Raises:
            ValueError: If username or email already exists
        """
        # Check for existing username
        if username in self._username_index:
            raise ValueError(f"Username '{username}' already exists")

        # Check for existing email
        if email in self._email_index:
            raise ValueError(f"Email '{email}' already exists")

        # Create user
        user = User(
            username=username,
            email=email,
            role=role,
            password_hash=self._hash_password(password),
            metadata=metadata or {},
        )

        # Store user
        self._users[user.id] = user
        self._username_index[username] = user.id
        self._email_index[email] = user.id

        # Persist to Redis if available
        if self._redis:
            await self._persist_user(user)

        return user

    async def get_user(self, user_id: str) -> User | None:
        """Get user by ID.

        Args:
            user_id: User identifier

        Returns:
            User if found, None otherwise
        """
        # Try memory first
        if user_id in self._users:
            return self._users[user_id]

        # Try Redis if available
        if self._redis:
            user_data = await self._redis.get(f"user:{user_id}")
            if user_data:
                user = User.from_dict(user_data)
                self._users[user_id] = user
                return user

        return None

    async def get_user_by_username(self, username: str) -> User | None:
        """Get user by username.

        Args:
            username: Username to lookup

        Returns:
            User if found, None otherwise
        """
        user_id = self._username_index.get(username)
        if user_id:
            return await self.get_user(user_id)

        # Try Redis if available
        if self._redis:
            user_id = await self._redis.get(f"user:username:{username}")
            if user_id:
                return await self.get_user(user_id.decode())

        return None

    async def get_user_by_email(self, email: str) -> User | None:
        """Get user by email.

        Args:
            email: Email to lookup

        Returns:
            User if found, None otherwise
        """
        user_id = self._email_index.get(email)
        if user_id:
            return await self.get_user(user_id)

        # Try Redis if available
        if self._redis:
            user_id = await self._redis.get(f"user:email:{email}")
            if user_id:
                return await self.get_user(user_id.decode())

        return None

    async def authenticate_user(self, username: str, password: str) -> User | None:
        """Authenticate user with username and password.

        Args:
            username: Username
            password: Plain text password

        Returns:
            User if authenticated, None otherwise
        """
        user = await self.get_user_by_username(username)
        if not user:
            return None

        if not user.is_active:
            return None

        if self._verify_password(password, user.password_hash):
            return user

        return None

    async def update_user(
        self,
        user_id: str,
        email: str | None = None,
        role: UserRole | None = None,
        is_active: bool | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> User | None:
        """Update user information.

        Args:
            user_id: User identifier
            email: New email (optional)
            role: New role (optional)
            is_active: New active status (optional)
            metadata: Metadata updates (optional)

        Returns:
            Updated user if found, None otherwise
        """
        user = await self.get_user(user_id)
        if not user:
            return None

        # Update email if provided
        if email is not None and email != user.email:
            if email in self._email_index:
                raise ValueError(f"Email '{email}' already exists")
            del self._email_index[user.email]
            self._email_index[email] = user_id
            user.email = email

        # Update other fields
        if role is not None:
            user.role = role
        if is_active is not None:
            user.is_active = is_active
        if metadata is not None:
            user.metadata.update(metadata)

        user.updated_at = datetime.utcnow()

        # Persist to Redis if available
        if self._redis:
            await self._persist_user(user)

        return user

    async def update_password(self, user_id: str, new_password: str) -> bool:
        """Update user password.

        Args:
            user_id: User identifier
            new_password: New plain text password

        Returns:
            True if updated successfully
        """
        user = await self.get_user(user_id)
        if not user:
            return False

        user.password_hash = self._hash_password(new_password)
        user.updated_at = datetime.utcnow()

        # Persist to Redis if available
        if self._redis:
            await self._persist_user(user)

        return True

    async def delete_user(self, user_id: str) -> bool:
        """Delete a user.

        Args:
            user_id: User identifier

        Returns:
            True if deleted successfully
        """
        user = await self.get_user(user_id)
        if not user:
            return False

        # Remove from indexes
        del self._users[user_id]
        del self._username_index[user.username]
        del self._email_index[user.email]

        # Remove from Redis if available
        if self._redis:
            await self._redis.delete(f"user:{user_id}")
            await self._redis.delete(f"user:username:{user.username}")
            await self._redis.delete(f"user:email:{user.email}")

        return True

    async def list_users(self, active_only: bool = False) -> list[User]:
        """List all users.

        Args:
            active_only: Only return active users

        Returns:
            List of users
        """
        users = list(self._users.values())
        if active_only:
            users = [u for u in users if u.is_active]
        return users

    async def _persist_user(self, user: User) -> None:
        """Persist user to Redis.

        Args:
            user: User to persist
        """
        if not self._redis:
            return

        import json

        user_data = user.to_dict(include_sensitive=True)
        await self._redis.set(f"user:{user.id}", json.dumps(user_data))
        await self._redis.set(f"user:username:{user.username}", user.id)
        await self._redis.set(f"user:email:{user.email}", user.id)

    async def load_from_redis(self) -> None:
        """Load all users from Redis."""
        if not self._redis:
            return

        import json

        # Get all user keys
        keys = await self._redis.keys("user:*")
        for key in keys:
            key_str = key.decode() if isinstance(key, bytes) else key
            if key_str.startswith("user:") and not key_str.startswith(
                ("user:username:", "user:email:")):
                user_data = await self._redis.get(key)
                if user_data:
                    data = json.loads(user_data.decode() if isinstance(user_data, bytes) else user_data)
                    user = User.from_dict(data)
                    self._users[user.id] = user
                    self._username_index[user.username] = user.id
                    self._email_index[user.email] = user.id


# Global user manager instance
user_manager = UserManager()
