from __future__ import annotations

import os
from dataclasses import dataclass


TRUE_VALUES = {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    app_env: str
    auth_enabled: bool
    site_password: str
    session_secret: str

    @property
    def production(self) -> bool:
        return self.app_env == "production"


def load_settings(environ: dict[str, str] | None = None) -> Settings:
    values = os.environ if environ is None else environ
    railway_environment = any(
        values.get(name)
        for name in (
            "RAILWAY_ENVIRONMENT",
            "RAILWAY_ENVIRONMENT_NAME",
            "RAILWAY_PROJECT_ID",
            "RAILWAY_SERVICE_ID",
            "RAILWAY_PUBLIC_DOMAIN",
            "RAILWAY_STATIC_URL",
        )
    )
    app_env = "production" if railway_environment else (values.get("APP_ENV") or "development").strip().lower()
    settings = Settings(
        app_env=app_env,
        auth_enabled=(values.get("AUTH_ENABLED") or "false").strip().lower() in TRUE_VALUES,
        site_password=values.get("SITE_PASSWORD") or "",
        session_secret=values.get("SESSION_SECRET") or "",
    )
    validate_settings(settings)
    return settings


def validate_settings(settings: Settings) -> None:
    if settings.production and not settings.auth_enabled:
        raise RuntimeError("AUTH_ENABLED must be true when APP_ENV=production")
    if settings.production and not settings.site_password:
        raise RuntimeError("SITE_PASSWORD is required when APP_ENV=production")
    if settings.production and not settings.session_secret:
        raise RuntimeError("SESSION_SECRET is required when APP_ENV=production")
    if settings.auth_enabled and not settings.site_password:
        raise RuntimeError("SITE_PASSWORD is required when authentication is enabled")
    if settings.auth_enabled and not settings.session_secret:
        raise RuntimeError("SESSION_SECRET is required when authentication is enabled")
