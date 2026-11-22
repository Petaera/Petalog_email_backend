"""Caller authentication.

Bearer tokens accepted:

* REPORTS_API_SECRET        the new edge function / operators (full access)
* SUPABASE_SERVICE_ROLE_KEY  backwards compatible (full access)
* SUPABASE_ANON_KEY         backwards compatible, only while
                             ALLOW_ANON_KEY_AUTH=true. The anon key is public
                             (it ships in the web app), so anon callers may
                             only trigger the normal report for owners they
                             name: no email override, no location override,
                             no "all owners" run, no template/timezone
                             override. Those used to let anyone mail any
                             location's data to any address.
"""

from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass
from typing import Optional

from .config import Settings


@dataclass(frozen=True)
class Caller:
    kind: str  # 'secret' | 'service' | 'anon'

    @property
    def trusted(self) -> bool:
        return self.kind in ("secret", "service")


def _same(a: Optional[str], b: Optional[str]) -> bool:
    return bool(a) and bool(b) and hmac.compare_digest(a.encode(), b.encode())


def authenticate(authorization: Optional[str], settings: Settings) -> Optional[Caller]:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization[len("Bearer "):].strip()
    if _same(token, settings.reports_api_secret):
        return Caller("secret")
    if _same(token, settings.supabase_service_role_key):
        return Caller("service")
    if settings.allow_anon_key_auth and _same(token, settings.supabase_anon_key):
        return Caller("anon")
    return None


def unsubscribe_token(settings: Settings, owner_id: str) -> Optional[str]:
    if not settings.unsubscribe_secret:
        return None
    return hmac.new(settings.unsubscribe_secret.encode(), f"unsubscribe:{owner_id}".encode(),
                    hashlib.sha256).hexdigest()[:40]


def unsubscribe_url(settings: Settings, owner_id: str) -> Optional[str]:
    token = unsubscribe_token(settings, owner_id)
    if not token or not settings.public_url:
        return None
    return f"{settings.public_url}/v1/unsubscribe?u={owner_id}&t={token}"


def check_unsubscribe(settings: Settings, owner_id: str, token: str) -> bool:
    expected = unsubscribe_token(settings, owner_id)
    return _same(expected, token)
