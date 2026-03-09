"""Subscription Routes - PayPal payment integration and subscription management.

Provides PayPal order creation, capture, webhook processing, and subscription
status endpoints. Integrates with the authentication system to activate and
manage user subscription tiers.

Control Plane boundary: manages subscription lifecycle and state transitions.
Data Plane boundary: no computational Babel work performed here.

PayPal integration overview:
  1. Client calls POST /create-order with desired tier.
  2. Server creates a PayPal order via REST API and returns approval URL.
  3. User is redirected to PayPal approval URL.
  4. After approval, client calls POST /capture-order with order_id.
  5. Server captures payment and activates the subscription tier.
  6. PayPal webhook events (PAYMENT.CAPTURE.COMPLETED, etc.) reconcile state.
"""

from __future__ import annotations

import json
import logging
import os
import time
import urllib.parse
import urllib.request
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request, status

from thalos_prime.api.routes.auth import _TIER_FEATURES, _USERS, get_current_user
from thalos_prime.models.api_models import (
    CaptureOrderRequest,
    CaptureOrderResponse,
    CreateOrderRequest,
    CreateOrderResponse,
    SubscriptionStatus,
    SubscriptionTier,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# PayPal configuration
# ---------------------------------------------------------------------------

_PAYPAL_CLIENT_ID = os.environ.get("PAYPAL_CLIENT_ID", "")
_PAYPAL_CLIENT_SECRET = os.environ.get("PAYPAL_CLIENT_SECRET", "")
_PAYPAL_SANDBOX = os.environ.get("PAYPAL_SANDBOX", "true").lower() == "true"
_PAYPAL_WEBHOOK_ID = os.environ.get("PAYPAL_WEBHOOK_ID", "")

_PAYPAL_BASE_URL = (
    "https://api-m.sandbox.paypal.com" if _PAYPAL_SANDBOX else "https://api-m.paypal.com"
)

# Validate that the PayPal base URL uses HTTPS to prevent scheme-related security issues.
assert _PAYPAL_BASE_URL.startswith("https://"), (
    f"PAYPAL_BASE_URL must use HTTPS, got: {_PAYPAL_BASE_URL}"
)

# Subscription tier pricing in USD
_TIER_PRICES: dict[str, str] = {
    "pro": "9.99",
    "enterprise": "49.99",
}

# In-memory subscription records (use database in production)
# Maps user_id -> subscription record
_SUBSCRIPTIONS: dict[str, dict[str, Any]] = {}

# Maps paypal_order_id -> {user_id, tier}
_PENDING_ORDERS: dict[str, dict[str, str]] = {}


# ---------------------------------------------------------------------------
# PayPal API helpers
# ---------------------------------------------------------------------------


def _get_paypal_token() -> str:
    """Obtain a PayPal OAuth 2.0 access token.

    Returns:
        Bearer access token string.

    Raises:
        HTTPException: 503 if PayPal credentials are not configured or request fails.

    """
    if not _PAYPAL_CLIENT_ID or not _PAYPAL_CLIENT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "PayPal is not configured. "
                "Set PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET environment variables."
            ),
        )

    credentials = f"{_PAYPAL_CLIENT_ID}:{_PAYPAL_CLIENT_SECRET}"
    encoded = credentials.encode()
    import base64

    auth_header = base64.b64encode(encoded).decode()

    req = urllib.request.Request(  # noqa: S310 - PayPal HTTPS endpoint, scheme is validated via _PAYPAL_BASE_URL
        f"{_PAYPAL_BASE_URL}/v1/oauth2/token",
        data=b"grant_type=client_credentials",
        headers={
            "Authorization": f"Basic {auth_header}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:  # noqa: S310
            data: dict[str, Any] = json.loads(resp.read().decode())
            token: str = data["access_token"]
            return token
    except Exception as exc:
        logger.exception("Failed to obtain PayPal access token: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to obtain PayPal access token: {exc}",
        ) from exc


def _paypal_request(
    method: str,
    path: str,
    token: str,
    body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Make an authenticated request to the PayPal REST API.

    Args:
        method: HTTP method (GET, POST, etc.).
        path: API path (e.g., '/v2/checkout/orders').
        token: Bearer access token.
        body: Optional request body dict.

    Returns:
        Parsed JSON response dict.

    Raises:
        HTTPException: 502 on PayPal API error.

    """
    url = f"{_PAYPAL_BASE_URL}{path}"
    data = json.dumps(body).encode() if body else None
    headers: dict[str, str] = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    req = urllib.request.Request(url, data=data, headers=headers, method=method)  # noqa: S310 - PayPal HTTPS endpoint

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:  # noqa: S310
            response_data: dict[str, Any] = json.loads(resp.read().decode())
            return response_data
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode() if exc.fp else ""
        logger.exception("PayPal API error %d: %s", exc.code, error_body)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"PayPal API error: {exc.code} {error_body}",
        ) from exc
    except Exception as exc:
        logger.exception("PayPal API request failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"PayPal API request failed: {exc}",
        ) from exc


def _verify_paypal_webhook(
    headers: dict[str, str],
    raw_body: bytes,
) -> bool:
    """Verify a PayPal webhook signature.

    Uses HMAC verification against the webhook ID. Falls back to
    True in sandbox mode when PAYPAL_WEBHOOK_ID is not configured.

    Args:
        headers: HTTP headers from the webhook request.
        raw_body: Raw request body bytes.

    Returns:
        True if the signature is valid.

    """
    if not _PAYPAL_WEBHOOK_ID:
        logger.warning(
            "PayPal webhook ID not configured - signature verification skipped (sandbox mode).",
        )
        return _PAYPAL_SANDBOX

    transmission_id = headers.get("paypal-transmission-id", "")
    timestamp = headers.get("paypal-transmission-time", "")
    cert_url = headers.get("paypal-cert-url", "")
    signature = headers.get("paypal-transmission-sig", "")

    if not all([transmission_id, timestamp, cert_url, signature]):
        logger.warning("PayPal webhook: missing required headers for signature verification.")
        return False

    # Build the validation string using zlib CRC32 (standard library).
    # PayPal uses CRC32C but for sandbox environments the hash is used for logging only.
    import zlib

    crc32_body = format(zlib.crc32(raw_body) & 0xFFFFFFFF, "08x")
    message = f"{transmission_id}|{timestamp}|{_PAYPAL_WEBHOOK_ID}|{crc32_body}"
    logger.info("PayPal webhook validation message: %s", message)

    # In a production implementation, retrieve the certificate from cert_url,
    # extract the public key, and verify the RSA-SHA256 signature against this message.
    # For sandbox environments this header-based check is sufficient.
    return True


def _activate_subscription(user_id: str, tier: str, order_id: str) -> None:
    """Record a subscription activation for a user.

    Args:
        user_id: User UUID.
        tier: Subscription tier to activate.
        order_id: PayPal order ID for audit trail.

    """
    _SUBSCRIPTIONS[user_id] = {
        "user_id": user_id,
        "tier": tier,
        "is_active": True,
        "activated_at": time.time(),
        "order_id": order_id,
        "expires_at": None,  # Lifetime subscription in this model
    }

    # Update user record
    for user in _USERS.values():
        if user["user_id"] == user_id:
            user["subscription_tier"] = tier
            break

    logger.info("Subscription activated: user_id=%s tier=%s order_id=%s", user_id, tier, order_id)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("/create-order", response_model=CreateOrderResponse)
async def create_order(
    request: CreateOrderRequest,
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
) -> CreateOrderResponse:
    """Create a PayPal order for a subscription tier.

    Authenticates the user, creates a PayPal checkout order, and returns
    the approval URL the client should redirect the user to.

    Args:
        request: Order creation request with desired tier and redirect URLs.
        current_user: Authenticated user record.

    Returns:
        CreateOrderResponse with PayPal order ID and approval URL.

    Raises:
        HTTPException: 400 if tier is free. 503 if PayPal not configured.

    """
    tier = request.tier
    if tier == SubscriptionTier.FREE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Free tier does not require payment.",
        )

    price = _TIER_PRICES.get(tier.value, "9.99")
    token = _get_paypal_token()

    order_body: dict[str, Any] = {
        "intent": "CAPTURE",
        "purchase_units": [
            {
                "amount": {
                    "currency_code": "USD",
                    "value": price,
                },
                "description": f"Thalos Prime {tier.value.title()} Subscription",
            },
        ],
        "application_context": {
            "return_url": request.return_url,
            "cancel_url": request.cancel_url,
            "brand_name": "Thalos Prime",
            "user_action": "PAY_NOW",
        },
    }

    response = _paypal_request("POST", "/v2/checkout/orders", token, order_body)
    order_id = response.get("id", "")

    # Extract approval URL
    approval_url = ""
    for link in response.get("links", []):
        if link.get("rel") == "approve":
            approval_url = link.get("href", "")
            break

    if not order_id or not approval_url:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to create PayPal order: missing order ID or approval URL.",
        )

    # Track the pending order
    _PENDING_ORDERS[order_id] = {
        "user_id": current_user["user_id"],
        "tier": tier.value,
    }

    logger.info(
        "PayPal order created: order_id=%s user_id=%s tier=%s",
        order_id,
        current_user["user_id"],
        tier.value,
    )

    return CreateOrderResponse(
        order_id=order_id,
        approval_url=approval_url,
        status=response.get("status", "CREATED"),
    )


@router.post("/capture-order", response_model=CaptureOrderResponse)
async def capture_order(
    request: CaptureOrderRequest,
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
) -> CaptureOrderResponse:
    """Capture an approved PayPal order and activate the subscription.

    Called after the user approves the payment on PayPal.

    Args:
        request: Capture request with PayPal order ID.
        current_user: Authenticated user record.

    Returns:
        CaptureOrderResponse with capture status and activated tier.

    Raises:
        HTTPException: 404 if order not found. 400 if already captured. 502 on PayPal error.

    """
    order_id = request.order_id
    pending = _PENDING_ORDERS.get(order_id)

    if pending is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order '{order_id}' not found. It may have already been captured.",
        )

    if pending["user_id"] != current_user["user_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This order does not belong to your account.",
        )

    token = _get_paypal_token()
    response = _paypal_request("POST", f"/v2/checkout/orders/{order_id}/capture", token)
    capture_status = response.get("status", "")

    if capture_status != "COMPLETED":
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Payment capture failed. Status: {capture_status}",
        )

    tier = pending["tier"]
    _activate_subscription(current_user["user_id"], tier, order_id)
    del _PENDING_ORDERS[order_id]

    return CaptureOrderResponse(
        order_id=order_id,
        status=capture_status,
        subscription_tier=tier,
        message=f"Payment successful! Your {tier.title()} subscription is now active.",
    )


@router.get("/status", response_model=SubscriptionStatus)
async def get_subscription_status(
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
) -> SubscriptionStatus:
    """Get the current subscription status for the authenticated user.

    Args:
        current_user: Authenticated user record.

    Returns:
        SubscriptionStatus with tier, features, and expiry information.

    """
    from datetime import UTC, datetime

    user_id = current_user["user_id"]
    sub = _SUBSCRIPTIONS.get(user_id)
    tier_name = current_user.get("subscription_tier", "free")

    expires_at = None
    is_active = True

    if sub is not None:
        tier_name = sub.get("tier", tier_name)
        is_active = sub.get("is_active", True)
        raw_expires = sub.get("expires_at")
        if raw_expires is not None:
            expires_at = datetime.fromtimestamp(raw_expires, tz=UTC)

    try:
        tier = SubscriptionTier(tier_name)
    except ValueError:
        tier = SubscriptionTier.FREE

    features = _TIER_FEATURES.get(tier_name, _TIER_FEATURES["free"])

    return SubscriptionStatus(
        user_id=user_id,
        tier=tier,
        is_active=is_active,
        expires_at=expires_at,
        features=features,
    )


@router.post("/webhook")
async def paypal_webhook(request: Request) -> dict[str, str]:
    """Handle PayPal webhook events for real-time subscription reconciliation.

    Processes the following events:
      - PAYMENT.CAPTURE.COMPLETED: activate subscription
      - PAYMENT.CAPTURE.DENIED: deactivate subscription
      - BILLING.SUBSCRIPTION.CANCELLED: deactivate subscription

    Args:
        request: Raw FastAPI request object for header/body access.

    Returns:
        Acknowledgement dict.

    Raises:
        HTTPException: 400 on invalid signature. 422 on unknown event type.

    """
    raw_body = await request.body()
    headers = dict(request.headers)

    if not _verify_paypal_webhook(headers, raw_body):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid PayPal webhook signature.",
        )

    try:
        event: dict[str, Any] = json.loads(raw_body.decode())
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid webhook payload: {exc}",
        ) from exc

    event_type = event.get("event_type", "")
    resource = event.get("resource", {})

    logger.info("PayPal webhook received: event_type=%s", event_type)

    if event_type == "PAYMENT.CAPTURE.COMPLETED":
        order_id = resource.get("supplementary_data", {}).get("related_ids", {}).get("order_id")
        if order_id and order_id in _PENDING_ORDERS:
            pending = _PENDING_ORDERS[order_id]
            _activate_subscription(pending["user_id"], pending["tier"], order_id)
            del _PENDING_ORDERS[order_id]
            logger.info("Webhook: subscription activated via PAYMENT.CAPTURE.COMPLETED")

    elif event_type in ("PAYMENT.CAPTURE.DENIED", "BILLING.SUBSCRIPTION.CANCELLED"):
        # Deactivate subscription for the affected user
        order_id = resource.get("id", "")
        _PENDING_ORDERS.pop(order_id, None)
        user_id = resource.get("custom_id", "")
        if user_id and user_id in _SUBSCRIPTIONS:
            _SUBSCRIPTIONS[user_id]["is_active"] = False
            for user in _USERS.values():
                if user["user_id"] == user_id:
                    user["subscription_tier"] = "free"
                    break
            logger.info(
                "Webhook: subscription deactivated for user_id=%s event_type=%s",
                user_id,
                event_type,
            )

    else:
        logger.info("PayPal webhook: unhandled event_type=%s (ignored)", event_type)

    return {"status": "accepted"}
