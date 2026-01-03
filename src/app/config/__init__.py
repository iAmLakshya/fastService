"""Application configuration.

Usage:
    from app.config import settings

    # Access grouped settings
    settings.database.url
    settings.server.port
    settings.name
    settings.is_production

Testing:
    from app.config import configure

    # Override for tests
    configure(AppSettings(name="Test App", env="testing"))
"""

from app.config.base import AppSettings, DatabaseSettings, ServerSettings

_settings: AppSettings | None = None


def get_settings() -> AppSettings:
    """Get current settings. Creates default if not configured."""
    global _settings
    if _settings is None:
        _settings = AppSettings()
    return _settings


def configure(new_settings: AppSettings) -> None:
    """Override settings. Useful for testing."""
    global _settings
    _settings = new_settings


def reset() -> None:
    """Reset to default settings. Useful for testing."""
    global _settings
    _settings = None


# Module-level singleton for convenient access
# Use: from app.config import settings
class _SettingsProxy:
    """Lazy proxy to settings singleton."""

    def __getattr__(self, name: str):
        return getattr(get_settings(), name)


settings = _SettingsProxy()

__all__ = [
    "settings",
    "get_settings",
    "configure",
    "reset",
    "AppSettings",
    "DatabaseSettings",
    "ServerSettings",
]
