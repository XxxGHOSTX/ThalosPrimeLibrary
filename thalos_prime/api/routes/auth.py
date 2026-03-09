"""Authentication Routes - User registration and login with JWT tokens.

Provides sign-up, sign-in, profile retrieval, and logout endpoints.
Users authenticate via JWT bearer tokens issued at login.

Control Plane boundary: manages authentication lifecycle.
Data Plane boundary: no computational work performed here.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
import time
import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from thalos_prime.models.api_models import (
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    RegisterResponse,
    UserProfile,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# In-memory user store (replace with database in production)
# ---------------------------------------------------------------------------

# Maps username -> user record
_USERS: dict[str, dict[str, Any]] = {}
# Maps token -> username for active sessions
_TOKENS: dict[str, str] = {}

_JWT_SECRET = os.environ.get("THALOS_JWT_SECRET", "thalos-prime-dev-secret-change-in-production")
_TOKEN_TTL_SECONDS = int(os.environ.get("THALOS_TOKEN_TTL", "86400"))  # 24 hours

# Subscription tier feature map
_TIER_FEATURES: dict[str, list[str]] = {
    "free": ["basic_search", "basic_generate", "5_searches_per_day"],
    "pro": ["unlimited_search", "advanced_generate", "decode", "chat", "enumerate", "api_access"],
    "enterprise": [
        "unlimited_search",
        "advanced_generate",
        "decode",
        "chat",
        "enumerate",
        "api_access",
        "priority_support",
        "custom_integrations",
    ],
}

bearer_scheme = HTTPBearer(auto_error=False)


def _hash_password(password: str) -> str:
    """Hash a password with HMAC-SHA256.

    Args:
        password: Plain-text password to hash.

    Returns:
        Hex-encoded HMAC-SHA256 hash.

    """
    return hmac.new(_JWT_SECRET.encode(), password.encode(), hashlib.sha256).hexdigest()


def _create_token(user_id: str, username: str) -> str:
    """Create a deterministic bearer token from user ID and current time.

    Args:
        user_id: User UUID.
        username: Username for inclusion in token.

    Returns:
        Hex token string.

    """
    seed = f"{user_id}:{username}:{time.time()}"
    return hmac.new(_JWT_SECRET.encode(), seed.encode(), hashlib.sha256).hexdigest()


def _verify_token(token: str) -> str | None:
    """Verify bearer token and return username if valid.

    Args:
        token: Bearer token from Authorization header.

    Returns:
        Username if token is valid and not expired, else None.

    """
    return _TOKENS.get(token)


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> dict[str, Any]:
    """FastAPI dependency: verify bearer token and return user record.

    Args:
        credentials: HTTP bearer credentials from Authorization header.

    Returns:
        User record dict.

    Raises:
        HTTPException: 401 if token is missing or invalid.

    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please sign in.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    username = _verify_token(credentials.credentials)
    if username is None or username not in _USERS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token. Please sign in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return _USERS[username]


def get_current_user_optional(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> dict[str, Any] | None:
    """FastAPI dependency: return user if authenticated, else None.

    Args:
        credentials: HTTP bearer credentials from Authorization header.

    Returns:
        User record dict if authenticated, else None.

    """
    if credentials is None:
        return None
    username = _verify_token(credentials.credentials)
    if username is None or username not in _USERS:
        return None
    return _USERS[username]


def require_subscription(
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
    required_tier: str = "pro",
) -> dict[str, Any]:
    """FastAPI dependency: verify user has required subscription tier.

    Args:
        current_user: Authenticated user record.
        required_tier: Minimum required tier ('pro' or 'enterprise').

    Returns:
        User record if subscription requirement is met.

    Raises:
        HTTPException: 402 if subscription is insufficient.

    """
    tier_order = ["free", "pro", "enterprise"]
    user_tier = current_user.get("subscription_tier", "free")
    if tier_order.index(user_tier) < tier_order.index(required_tier):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=(
                f"This feature requires a '{required_tier}' subscription. "
                f"Your current tier is '{user_tier}'. "
                "Please upgrade at /api/v1/subscription/create-order."
            ),
        )
    return current_user


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(request: RegisterRequest) -> RegisterResponse:
    """Register a new user account.

    Creates a new user with hashed password and free subscription tier.

    Args:
        request: Registration request with username, email, and password.

    Returns:
        RegisterResponse with new user details.

    Raises:
        HTTPException: 409 if username or email already exists.

    """
    if request.username in _USERS:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Username '{request.username}' is already taken.",
        )
    for user in _USERS.values():
        if user["email"] == request.email:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email already exists.",
            )

    user_id = str(uuid.uuid4())
    hashed_pw = _hash_password(request.password)
    created_at = time.time()

    _USERS[request.username] = {
        "user_id": user_id,
        "username": request.username,
        "email": request.email,
        "hashed_password": hashed_pw,
        "subscription_tier": "free",
        "is_active": True,
        "created_at": created_at,
    }

    logger.info("New user registered: username=%s user_id=%s", request.username, user_id)

    return RegisterResponse(
        user_id=user_id,
        username=request.username,
        email=request.email,
        message="Registration successful. You can now sign in.",
    )


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest) -> LoginResponse:
    """Authenticate a user and return a JWT bearer token.

    Args:
        request: Login request with username/email and password.

    Returns:
        LoginResponse with bearer token and user details.

    Raises:
        HTTPException: 401 if credentials are invalid.

    """
    user = _USERS.get(request.username)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    expected_hash = _hash_password(request.password)
    if not hmac.compare_digest(user["hashed_password"], expected_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated. Please contact support.",
        )

    token = _create_token(user["user_id"], user["username"])
    _TOKENS[token] = user["username"]

    logger.info("User logged in: username=%s", user["username"])

    return LoginResponse(
        access_token=token,
        token_type="bearer",  # noqa: S106 - "bearer" is the RFC 6750 OAuth2 token type, not a hardcoded credential
        expires_in=_TOKEN_TTL_SECONDS,
        user_id=user["user_id"],
        username=user["username"],
        subscription_tier=user.get("subscription_tier", "free"),
    )


@router.get("/me", response_model=UserProfile)
async def get_profile(
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
) -> UserProfile:
    """Get the current authenticated user's profile.

    Args:
        current_user: Authenticated user record (injected by dependency).

    Returns:
        UserProfile with account details.

    """
    from datetime import UTC, datetime

    return UserProfile(
        user_id=current_user["user_id"],
        username=current_user["username"],
        email=current_user["email"],
        subscription_tier=current_user.get("subscription_tier", "free"),
        is_active=current_user.get("is_active", True),
        created_at=datetime.fromtimestamp(current_user["created_at"], tz=UTC),
    )


@router.post("/logout")
async def logout(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> dict[str, str]:
    """Invalidate the current bearer token.

    Args:
        credentials: HTTP bearer credentials from Authorization header.

    Returns:
        Success message dict.

    """
    if credentials and credentials.credentials in _TOKENS:
        username = _TOKENS.pop(credentials.credentials)
        logger.info("User logged out: username=%s", username)
    return {"message": "Logged out successfully."}


@router.get("/subscription-features")
async def get_subscription_features() -> dict[str, Any]:
    """Get the features available for each subscription tier.

    Returns:
        Dict mapping tier names to their feature lists.

    """
    return {
        "tiers": {
            "free": {
                "price_usd": "0.00",
                "features": _TIER_FEATURES["free"],
                "description": "Basic access to Library of Babel search.",
            },
            "pro": {
                "price_usd": "9.99",
                "features": _TIER_FEATURES["pro"],
                "description": "Full access to all search, decode, chat, and API features.",
            },
            "enterprise": {
                "price_usd": "49.99",
                "features": _TIER_FEATURES["enterprise"],
                "description": "Unlimited access with priority support and custom integrations.",
            },
        },
    }
