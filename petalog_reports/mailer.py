"""MIME building and delivery through AWS SES (send_raw_email)."""

from __future__ import annotations

import logging
import time
from email.message import EmailMessage
from email.policy import SMTP
from typing import Dict, List, Optional, Sequence

from .config import Settings
from .exports import Attachment

logger = logging.getLogger(__name__)

# RFC 5322 allows 998-character lines. With the default 78 a long header
# without spaces (the List-Unsubscribe URL) gets RFC 2047-encoded, which mail
# clients then fail to read as a URL.
POLICY = SMTP.clone(max_line_length=998)

RETRYABLE = {"Throttling", "ThrottlingException", "ServiceUnavailable", "InternalFailure", "RequestTimeout"}


class SendError(Exception):
    def __init__(self, message: str, retryable: bool = False):
        super().__init__(message)
        self.retryable = retryable


def build_message(*, sender: str, to: Sequence[str], subject: str, html: str, text: str,
                  attachments: Sequence[Attachment] = (), headers: Optional[Dict[str, str]] = None,
                  reply_to: Optional[str] = None) -> bytes:
    """multipart/mixed( multipart/alternative(text, html), attachments... )"""
    msg = EmailMessage(policy=POLICY)
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = ", ".join(to)
    if reply_to:
        msg["Reply-To"] = reply_to
    for key, value in (headers or {}).items():
        msg[key] = value
    msg.set_content(text, subtype="plain", charset="utf-8")
    msg.add_alternative(html, subtype="html", charset="utf-8")
    for a in attachments:
        msg.add_attachment(a.content, maintype=a.maintype, subtype=a.subtype, filename=a.filename)
    return msg.as_bytes()


class SesMailer:
    def __init__(self, settings: Settings, client=None, sleep=time.sleep):
        self.settings = settings
        self._client = client
        self._sleep = sleep

    @property
    def client(self):
        if self._client is None:
            import boto3

            kwargs = {"region_name": self.settings.aws_region}
            if self.settings.aws_access_key_id and self.settings.aws_secret_access_key:
                kwargs.update(aws_access_key_id=self.settings.aws_access_key_id,
                              aws_secret_access_key=self.settings.aws_secret_access_key)
            self._client = boto3.client("ses", **kwargs)
        return self._client

    def send_raw(self, raw: bytes, recipients: List[str], attempts: int = 3) -> str:
        if not self.settings.ses_from:
            raise SendError("SES_VERIFIED_FROM is not set")
        params = {"Source": self.settings.ses_from, "Destinations": recipients, "RawMessage": {"Data": raw}}
        if self.settings.ses_configuration_set:
            params["ConfigurationSetName"] = self.settings.ses_configuration_set
        delay = 1.0
        for attempt in range(1, attempts + 1):
            try:
                response = self.client.send_raw_email(**params)
                return response["MessageId"]
            except Exception as exc:  # noqa: BLE001 - botocore ClientError and transport errors
                code = getattr(exc, "response", {}).get("Error", {}).get("Code", "") if hasattr(exc, "response") else ""
                message = getattr(exc, "response", {}).get("Error", {}).get("Message", str(exc)) if hasattr(exc, "response") else str(exc)
                retryable = code in RETRYABLE or not code
                if retryable and attempt < attempts:
                    logger.warning("SES send failed (%s), retrying in %.0fs: %s", code or "error", delay, message)
                    self._sleep(delay)
                    delay *= 2
                    continue
                raise SendError(f"SES {code or 'error'}: {message}", retryable=retryable) from exc
        raise SendError("SES send failed")  # pragma: no cover

    def send(self, *, to: Sequence[str], subject: str, html: str, text: str,
             attachments: Sequence[Attachment] = (), headers: Optional[Dict[str, str]] = None) -> str:
        raw = build_message(sender=self.settings.ses_from or "", to=to, subject=subject, html=html, text=text,
                            attachments=attachments, headers=headers)
        if len(raw) > 9_500_000:  # SES raw message limit is 10 MB
            raise SendError(f"Message too large ({len(raw)} bytes)")
        return self.send_raw(raw, list(to))
