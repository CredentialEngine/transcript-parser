"""Configuration via environment variables."""

import os

# Anthropic API key for transcript extraction (required).
ANTHROPIC_API_KEY_VAR = "ANTHROPIC_API_KEY"

# Credential Engine Registry Search API key (required).
CE_API_KEY_VAR = "CE_REGISTRY_API_KEY"

# Model used for extraction.
DEFAULT_MODEL = os.environ.get("TRANSCRIPT_MATCHER_MODEL", "claude-opus-4-8")

SEARCH_ENDPOINTS = {
    "production": "https://apps.credentialengine.org/assistant/search/ctdl",
    "sandbox": "https://sandbox.credentialengine.org/assistant/search/ctdl",
}


def get_anthropic_key() -> str | None:
    return os.environ.get(ANTHROPIC_API_KEY_VAR)


def get_ce_key() -> str | None:
    return os.environ.get(CE_API_KEY_VAR)
