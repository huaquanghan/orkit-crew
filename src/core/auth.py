"""Authentication module for Orkit Crew API.

This module provides authentication with API Key and JWT token support,
along with rate limiting per user/key.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from fastapi import HTTPException, Request, Security, status
from fastapi.security import APIKeyHeader, HTTPBearer
from pydantic import BaseModel

from .api_keys import APIKeyManager, api_key_manager
from .users import User, UserManager, UserRole, user_manager

# Security schemes
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
jwt_bearer = HTTPBearer(auto_error=False)


class AuthMethod(str, Enum):
    """Authentication methods."""

    API_KEY = "api_key"
    JWT = "jwt"
    NONE = "none"


@dataclass
class RateLimitEntry:
    """Rate limit tracking entry."""

    count: int = 0
    window_start: float = field(default_factory=time.time)
    last_request: float = field(default_factory=time.time)


class RateLimiter:
    """Rate limiter with sliding window.

    Tracks requests per key/user with configurable limits.
    """

    def __init__(self, redis_client: Any | None = None):
        """Initialize rate limiter.

        Args:
            redis_client: Optional Redis client for distributed rate limiting
        """
        self._limits: dict[str, RateLimitEntry] = {}  # key -> entry
        self._redis = redis_client
        self._default_window = 60  # 1 minute window

    def _get_key(self, identifier: str, window: int | None = None) -> str:
        """Get rate limit key for identifier.

        Args:
            identifier: User ID or API key hash
            window: Time window in seconds

        Returns:
            Rate limit key
        """
        window = window or self._default_window
        current_window = int(time.time() / window)
        return f"{identifier}:{current_window}"

    async def check_rate_limit(
        self,
        identifier: str,
        limit: int,
        window: int | None = None,
    ) -> tuple[bool, dict[str, Any]]:
        """Check if request is within rate limit.

        Args:
            identifier: User ID or API key hash
            limit: Maximum requests allowed
            window: Time window in seconds

        Returns:
            Tuple of (allowed, headers) where headers contains rate limit info
        """
        window = window or self._default_window
        key = self._get_key(identifier, window)
        now = time.time()

        # Try Redis first for distributed rate limiting
        if self._redis:
            try:
                pipe = self._redis.pipeline()
                pipe.incr(key)
                pipe.expire(key, window)
                results = await pipe.execute()
                count = results[0]

                remaining = max(0, limit - count)
                reset_time = int((int(now / window) + 1) * window)

                headers = {
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": str(remaining),
                    "X-RateLimit-Reset": str(reset_time),
                }

                return count <= limit, headers
            except Exception:
                # Fall back to memory-based limiting
                pass

        # Memory-based rate limiting
        entry = self._limits.get(key)
        if not entry or (now - entry.window_start) > window:
            # New window
            entry = RateLimitEntry(count=0, window_start=now)
            self._limits[key] = entry

        entry.count += 1
        entry.last_request = now

        remaining = max(0, limit - entry.count)
        reset_time = int((int(now / window) + 1) * window)

        headers = {
            "X-RateLimit-Limit": str(limit),
            "X-RateLimit-Remaining": str(remaining),
            "X-RateLimit-Reset": str(reset_time),
        }

        return entry.count <= limit, headers

    async def get_rate_limit_status(
        self,
        identifier: str,
        limit: int,
        window: int | None = None,
    ) -> dict[str, Any]:
        """Get current rate limit status without incrementing.

        Args:
            identifier: User ID or API key hash
            limit: Maximum requests allowed
            window: Time window in seconds

        Returns:
            Rate limit status dictionary
        """
        window = window or self._default_window
        key = self._get_key(identifier, window)
        now = time.time()

        if self._redis:
            try:
                count = await self._redis.get(key)
                count = int(count) if count else 0
            except Exception:
                count = 0
        else:
            entry = self._limits.get(key)
            count = entry.count if entry and (now - entry.window_start) <= window else 0

        remaining = max(0, limit - count)
        reset_time = int((int(now / window) + 1) * window)

        return {
            "limit": limit,
            "remaining": remaining,
            "reset": reset_time,
            "window": window,
        }


class AuthContext(BaseModel):
    """Authentication context for a request."""

    user_id: str | None = None
    api_key_id: str | None = None
    auth_method: AuthMethod = AuthMethod.NONE
    permissions: list[str] = []
    rate_limit: int | None = None

    def is_authenticated(self) -> bool:
        """Check if request is authenticated."""
        return self.auth_method != AuthMethod.NONE

    def has_permission(self, permission: str) -> bool:
        """Check if has specific permission."""
        return permission in self.permissions or "*" in self.permissions


class AuthManager:
    """Main authentication manager.

    Handles API key and JWT authentication with rate limiting.
    """

    def __init__(
        self,
        user_manager: UserManager = user_manager,
        api_key_manager: APIKeyManager = api_key_manager,
        redis_client: Any | None = None,
    ):
        """Initialize auth manager.

        Args:
            user_manager: User manager instance
            api_key_manager: API key manager instance
            redis_client: Optional Redis client
        """
        self._user_manager = user_manager
        self._api_key_manager = api_key_manager
        self._rate_limiter = RateLimiter(redis_client)
        self._redis = redis_client

        # JWT settings (optional)
        self._jwt_secret: str | None = None
        self._jwt_algorithm = "HS256"
        self._jwt_expiry = timedelta(hours=24)

    def configure_jwt(self, secret: str, algorithm: str = "HS256", expiry_hours: int = 24) -> None:
        """Configure JWT settings.

        Args:
            secret: JWT secret key
            algorithm: JWT algorithm
            expiry_hours: Token expiry in hours
        """
        self._jwt_secret = secret
        self._jwt_algorithm = algorithm
        self._jwt_expiry = timedelta(hours=expiry_hours)

    async def authenticate_api_key(self, api_key: str) -> AuthContext:
        """Authenticate using API key.

        Args:
            api_key: Raw API key

        Returns:
            Authentication context

        Raises:
            HTTPException: If authentication fails
        """
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key required",
                headers={"WWW-Authenticate": "ApiKey"},
            )

        # Validate API key
        key_obj = await self._api_key_manager.validate_key(api_key)
        if not key_obj:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired API key",
                headers={"WWW-Authenticate": "ApiKey"},
            )

        # Get user
        user = await self._user_manager.get_user(key_obj.user_id)
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account inactive",
                headers={"WWW-Authenticate": "ApiKey"},
            )

        # Check rate limit
        if key_obj.rate_limit:
            allowed, headers = await self._rate_limiter.check_rate_limit(
                key_obj.key_hash,
                key_obj.rate_limit,
            )
            if not allowed:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded",
                    headers=headers,
                )

        return AuthContext(
            user_id=user.id,
            api_key_id=key_obj.id,
            auth_method=AuthMethod.API_KEY,
            permissions=key_obj.permissions or ["*"],
            rate_limit=key_obj.rate_limit,
        )

    async def authenticate_jwt(self, token: str) -> AuthContext:
        """Authenticate using JWT token.

        Args:
            token: JWT token

        Returns:
            Authentication context

        Raises:
            HTTPException: If authentication fails
        """
        if not self._jwt_secret:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="JWT authentication not configured",
            )

        try:
            import jwt
        except ImportError:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="JWT library not installed. Run: pip install PyJWT",
            )

        try:
            payload = jwt.decode(token, self._jwt_secret, algorithms=[self._jwt_algorithm])
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Get user
        user = await self._user_manager.get_user(user_id)
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account inactive",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return AuthContext(
            user_id=user.id,
            auth_method=AuthMethod.JWT,
            permissions=payload.get("permissions", ["*"]),
        )

    async def create_jwt_token(
        self,
        user_id: str,
        permissions: list[str] | None = None,
    ) -> str:
        """Create a JWT token for a user.

        Args:
            user_id: User identifier
            permissions: Optional permissions to include

        Returns:
            JWT token string

        Raises:
            HTTPException: If JWT not configured
        """
        if not self._jwt_secret:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="JWT authentication not configured",
            )

        try:
            import jwt
        except ImportError:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="JWT library not installed. Run: pip install PyJWT",
            )

        now = datetime.utcnow()
        payload = {
            "sub": user_id,
            "iat": now,
            "exp": now + self._jwt_expiry,
            "permissions": permissions or ["*"],
        }

        return jwt.encode(payload, self._jwt_secret, algorithm=self._jwt_algorithm)

    async def authenticate_request(
        self,
        request: Request,
        api_key: str | None = None,
        jwt_token: str | None = None,
    ) -> AuthContext:
        """Authenticate a request using available credentials.

        Args:
            request: FastAPI request
            api_key: Optional API key from header
            jwt_token: Optional JWT token from header

        Returns:
            Authentication context

        Raises:
            HTTPException: If authentication fails
        """
        # Try API key first
        if api_key:
            return await self.authenticate_api_key(api_key)

        # Try JWT token
        if jwt_token:
            return await self.authenticate_jwt(jwt_token)

        # No credentials provided
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "ApiKey, Bearer"},
        )


# Global auth manager instance
auth_manager = AuthManager()


# FastAPI dependency functions
async def require_auth(
    request: Request,
    api_key: str | None = Security(api_key_header),
) -> AuthContext:
    """FastAPI dependency to require authentication.

    Args:
        request: FastAPI request
        api_key: API key from header

    Returns:
        Authentication context

    Raises:
        HTTPException: If authentication fails
    """
    # Check for JWT in Authorization header
    jwt_token = None
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        jwt_token = auth_header[7:]

    return await auth_manager.authenticate_request(request, api_key, jwt_token)


async def optional_auth(
    request: Request,
    api_key: str | None = Security(api_key_header),
) -> AuthContext:
    """FastAPI dependency for optional authentication.

    Args:
        request: FastAPI request
        api_key: API key from header

    Returns:
        Authentication context (may be unauthenticated)
    """
    try:
        return await require_auth(request, api_key)
    except HTTPException:
        return AuthContext(auth_method=AuthMethod.NONE)


async def require_admin(auth: AuthContext = Security(require_auth)) -> AuthContext:
    """FastAPI dependency to require admin role.

    Args:
        auth: Authentication context

    Returns:
        Authentication context

    Raises:
        HTTPException: If user is not admin
    """
    user = await user_manager.get_user(auth.user_id) if auth.user_id else None
    if not user or not user.is_admin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return auth


class AuthMiddleware:
    """Middleware for authentication and rate limiting."""

    def __init__(
        self,
        auth_manager: AuthManager = auth_manager,
        public_paths: list[str] | None = None,
    ):
        """Initialize auth middleware.

        Args:
            auth_manager: Auth manager instance
            public_paths: List of paths that don't require authentication
        """
        self._auth_manager = auth_manager
        self._public_paths = set(public_paths or [])
        self._public_paths.update([
            "/",
            "/health",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/api/v1/health",
        ])

    async def __call__(self, request: Request, call_next):
        """Process request through middleware.

        Args:
            request: FastAPI request
            call_next: Next middleware/handler

        Returns:
            Response
        """
        from fastapi.responses import JSONResponse

        # Check if path is public
        path = request.url.path
        if any(path.startswith(p) for p in self._public_paths):
            return await call_next(request)

        # Try to authenticate
        try:
            api_key = request.headers.get("X-API-Key")
            jwt_token = None
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                jwt_token = auth_header[7:]

            auth_context = await self._auth_manager.authenticate_request(
                request, api_key, jwt_token
            )
            request.state.auth = auth_context
        except HTTPException as e:
            return JSONResponse(
                status_code=e.status_code,
                content={"detail": e.detail},
                headers=e.headers,
            )

        return await call_next(request)
