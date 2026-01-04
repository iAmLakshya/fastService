from functools import lru_cache
from typing import TYPE_CHECKING

from app.config.base import AppSettings, ServerSettings
from app.config.database import DatabasesSettings

_settings_override: AppSettings | None = None


@lru_cache
def _create_default_settings() -> AppSettings:
    return AppSettings()


def get_settings() -> AppSettings:
    if _settings_override is not None:
        return _settings_override
    return _create_default_settings()


def configure(new_settings: AppSettings) -> None:
    global _settings_override
    _settings_override = new_settings


def reset() -> None:
    global _settings_override
    _settings_override = None
    _create_default_settings.cache_clear()


if TYPE_CHECKING:
    settings: AppSettings
else:

    class _SettingsProxy:
        __slots__ = ()

        def __getattr__(self, name: str) -> object:
            return getattr(get_settings(), name)

        def __repr__(self) -> str:
            return repr(get_settings())

    settings = _SettingsProxy()

__all__ = [
    "settings",
    "get_settings",
    "configure",
    "reset",
    "AppSettings",
    "DatabasesSettings",
    "ServerSettings",
]
