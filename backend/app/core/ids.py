import secrets

from app.core.config import settings


def generate_bin_id() -> str:
    """URL-safe random slug; knowledge of it grants access (ADR-001)."""
    # token_hex(n) → 2n hex chars; slice to the configured length.
    return secrets.token_hex(settings.bin_id_length)[: settings.bin_id_length]
