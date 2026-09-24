"""Shared provider configuration for structured model calls."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from openai import OpenAI


PROVIDERS = {
    "deepseek": {
        "key_name": "DEEPSEEK_API_KEY",
        "model": "deepseek-flash",
        "base_url": "https://api.deepseek.com",
    },
    "openai": {
        "key_name": "OPENAI_API_KEY",
        "model": "gpt-5.6-luna",
        "base_url": None,
    },
}


class ModelUnavailable(RuntimeError):
    """Provider selection or API key is missing."""


class ModelFailure(RuntimeError):
    """Provider did not return a usable output."""


def provider_settings() -> tuple[str, dict[str, str | None]]:
    provider = os.environ.get("CV_ASSISTANT_PROVIDER", "deepseek").lower()
    if provider not in PROVIDERS:
        raise ModelUnavailable("CV_ASSISTANT_PROVIDER must be deepseek or openai")
    return provider, PROVIDERS[provider]


def responses_client(settings: dict[str, str | None]) -> Any:
    key_name = str(settings["key_name"])
    api_key = os.environ.get(key_name)
    if not api_key:
        raise ModelUnavailable(f"{key_name} is not configured")
    return OpenAI(
        api_key=api_key,
        base_url=settings["base_url"],
        timeout=90.0,
        max_retries=1,
    ).responses


def response_format(schema_path: Path, provider: str) -> dict[str, Any]:
    wrapper = json.loads(schema_path.read_text(encoding="utf-8"))
    if provider == "deepseek":
        return {
            "type": "json_schema",
            "name": wrapper["name"],
            "schema": wrapper["schema"],
        }
    return wrapper
