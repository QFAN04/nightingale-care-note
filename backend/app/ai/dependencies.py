"""FastAPI dependency for the configured scribe provider."""

from typing import Annotated

from fastapi import Depends, HTTPException, status

from app.ai.providers.base import ScribeProvider
from app.ai.providers.deepseek import DeepSeekScribeProvider
from app.config import Settings, get_settings


def get_scribe_provider(
    settings: Annotated[Settings, Depends(get_settings)],
) -> ScribeProvider:
    if settings.deepseek_api_key is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI scribe provider is not configured",
        )
    return DeepSeekScribeProvider(
        api_key=settings.deepseek_api_key.get_secret_value(),
        model=settings.deepseek_model,
        base_url=settings.deepseek_base_url,
        max_tokens=settings.deepseek_max_tokens,
        timeout_seconds=settings.deepseek_timeout_seconds,
    )
