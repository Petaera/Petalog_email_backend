"""Settings read from environment variables.

Every variable the previous version used keeps its name and meaning, so an
existing Render deployment keeps working without changes. New variables are
optional and have safe defaults.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Optional


def _env(name: str, default: Optional[str] = None) -> Optional[str]:
    value = os.getenv(name)
    if value is None:
        return default
    value = value.strip()
    return value if value != "" else default


def _env_bool(name: str, default: bool) -> bool:
    value = _env(name)
    if value is None:
        return default
    return value.lower() in ("1", "true", "yes", "on")


def _env_int(name: str, default: int) -> int:
    value = _env(name)
    try:
        return int(value) if value is not None else default
    except ValueError:
        return default


def email_address_of(sender: str) -> str:
    """'PetaLog <no-reply@petalog.in>' -> 'no-reply@petalog.in'."""
    match = re.search(r"<([^>]+)>", sender or "")
    return (match.group(1) if match else (sender or "")).strip()


@dataclass(frozen=True)
class Settings:
    # --- Supabase (unchanged names) ---
    supabase_url: Optional[str] = None
    supabase_service_role_key: Optional[str] = None
    supabase_anon_key: Optional[str] = None
    logs_table: str = "log-man"

    # --- AWS SES (unchanged names) ---
    aws_region: str = "us-east-1"
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    ses_from: Optional[str] = None
    ses_configuration_set: Optional[str] = None

    # --- Security ---
    # Dedicated secret for the new edge function / dispatch endpoint.
    reports_api_secret: Optional[str] = None
    # The previous edge function may authenticate with the anon key. Kept on
    # by default so nothing breaks during the switch-over; anon callers are
    # limited to sending the normal report to listed owners (no overrides).
    allow_anon_key_auth: bool = True
    unsubscribe_secret: Optional[str] = None

    # --- Links / branding ---
    app_url: str = "https://petalog.in"
    public_url: Optional[str] = None  # this service's public URL (Render)
    brand_logo_url: str = "https://petalog.in/android-chrome-512x512.png"
    brand_name: str = "PetaLog"

    # --- Behaviour ---
    morning_cutoff_hour: int = 12  # sends before this local hour report the previous day
    catchup_minutes: int = 180  # how late a missed send may still go out
    dispatch_max_owners: int = 25  # owners processed per dispatch call
    include_owners_without_schedule: bool = False
    attachment_format: str = "xlsx"  # xlsx | csv | none
    admin_email: Optional[str] = None
    admin_summary_mode: str = "failures"  # failures | always | off
    delivery_tracking: bool = True
    stale_sending_minutes: int = 20
    max_attempts: int = 3

    # --- Dev ---
    enable_dev_route: bool = False

    extra: dict = field(default_factory=dict)

    @property
    def from_address(self) -> str:
        return email_address_of(self.ses_from or "")

    @property
    def admin_recipient(self) -> Optional[str]:
        return self.admin_email or (self.from_address or None)

    @classmethod
    def from_env(cls) -> "Settings":
        attachment_format = (_env("REPORT_ATTACHMENT_FORMAT", "xlsx") or "xlsx").lower()
        if attachment_format not in ("xlsx", "csv", "none"):
            attachment_format = "xlsx"
        admin_mode = (_env("ADMIN_SUMMARY_MODE", "failures") or "failures").lower()
        if admin_mode not in ("failures", "always", "off"):
            admin_mode = "failures"
        public_url = _env("REPORTS_PUBLIC_URL")
        return cls(
            supabase_url=_env("SUPABASE_URL"),
            supabase_service_role_key=_env("SUPABASE_SERVICE_ROLE_KEY"),
            supabase_anon_key=_env("SUPABASE_ANON_KEY"),
            logs_table=_env("SUPABASE_LOGS_TABLE", "log-man") or "log-man",
            aws_region=_env("AWS_REGION", "us-east-1") or "us-east-1",
            aws_access_key_id=_env("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=_env("AWS_SECRET_ACCESS_KEY"),
            ses_from=_env("SES_VERIFIED_FROM"),
            ses_configuration_set=_env("SES_CONFIGURATION_SET"),
            reports_api_secret=_env("REPORTS_API_SECRET"),
            allow_anon_key_auth=_env_bool("ALLOW_ANON_KEY_AUTH", True),
            unsubscribe_secret=_env("UNSUBSCRIBE_SECRET") or _env("REPORTS_API_SECRET"),
            app_url=(_env("APP_URL", "https://petalog.in") or "https://petalog.in").rstrip("/"),
            public_url=public_url.rstrip("/") if public_url else None,
            brand_logo_url=_env("BRAND_LOGO_URL", "https://petalog.in/android-chrome-512x512.png")
            or "https://petalog.in/android-chrome-512x512.png",
            morning_cutoff_hour=min(max(_env_int("REPORT_MORNING_CUTOFF_HOUR", 12), 0), 24),
            catchup_minutes=max(_env_int("DISPATCH_CATCHUP_MINUTES", 180), 5),
            dispatch_max_owners=max(_env_int("DISPATCH_MAX_OWNERS", 25), 1),
            include_owners_without_schedule=_env_bool("INCLUDE_OWNERS_WITHOUT_SCHEDULE", False),
            attachment_format=attachment_format,
            admin_email=_env("ADMIN_REPORT_EMAIL"),
            admin_summary_mode=admin_mode,
            delivery_tracking=_env_bool("DELIVERY_TRACKING", True),
            stale_sending_minutes=max(_env_int("DELIVERY_STALE_MINUTES", 20), 5),
            max_attempts=max(_env_int("DELIVERY_MAX_ATTEMPTS", 3), 1),
            enable_dev_route=_env_bool("ENABLE_DEV_ROUTE", False),
        )
