"""Settings routes for persisted user configuration."""

from __future__ import annotations

import logging
from dataclasses import asdict
from typing import Any

from fastapi import APIRouter, HTTPException

from thalos_prime.user_settings import (
    UserSettingsError,
    load_settings,
    reset_settings,
    settings_file_path,
    update_settings,
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("")
async def get_settings() -> dict[str, Any]:
    """Return current persisted user settings."""
    try:
        settings = load_settings()
    except UserSettingsError as exc:
        logger.exception("Settings load failed")
        raise HTTPException(status_code=500, detail="Settings load failed") from exc
    payload = asdict(settings)
    payload["settings_file"] = str(settings_file_path())
    return payload


@router.patch("")
async def patch_settings(payload: dict[str, object]) -> dict[str, Any]:
    """Merge partial settings updates and return the resulting settings."""
    try:
        settings = update_settings(payload)
    except UserSettingsError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    response = asdict(settings)
    response["settings_file"] = str(settings_file_path())
    return response


@router.post("/reset")
async def reset_user_settings() -> dict[str, Any]:
    """Reset user settings to defaults and return the new settings."""
    settings = reset_settings()
    response = asdict(settings)
    response["settings_file"] = str(settings_file_path())
    return response
