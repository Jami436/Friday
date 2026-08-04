"""Gmail adapter for the EmailProvider port, using IMAP + an App Password."""
import email
import imaplib
import re
from datetime import datetime, timedelta
from email.header import decode_header
from email.utils import parsedate_to_datetime
from typing import Optional

from app.core.logger import logger
from app.domain.entities.email import EmailMessage
from app.domain.ports.email import EmailProvider

IMAP_HOST = "imap.gmail.com"


def _decode_header_value(value: str) -> str:
    if not value:
        return ""
    parts = decode_header(value)
    decoded = []
    for text, enc in parts:
        if isinstance(text, bytes):
            try:
                decoded.append(text.decode(enc or "utf-8", errors="replace"))
            except LookupError:
                decoded.append(text.decode("utf-8", errors="replace"))
        else:
            decoded.append(text)
    return " ".join(decoded).strip()


def _extract_snippet(payload, limit: int = 240) -> str:
    if isinstance(payload, bytes):
        payload = payload.decode("utf-8", errors="replace")
    text = re.sub(r"<[^>]+>", " ", payload)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit]


def _walk_body(msg) -> str:
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                snippet = _extract_snippet(part.get_payload(decode=True))
                if snippet:
                    return snippet
        for part in msg.walk():
            if part.get_content_type() == "text/html":
                snippet = _extract_snippet(part.get_payload(decode=True))
                if snippet:
                    return snippet
        return ""
    return _extract_snippet(msg.get_payload(decode=True))


class GmailImapAdapter(EmailProvider):
    """Reads recent inbox emails. Requires Gmail IMAP enabled and an App Password."""

    def __init__(
        self,
        user: Optional[str] = None,
        app_password: Optional[str] = None,
    ) -> None:
        self._user = user
        self._app_password = app_password

    @property
    def configured(self) -> bool:
        return bool(self._user and self._app_password)

    def fetch_recent(
        self,
        days: int = 3,
        limit: int = 15,
        unread_only: bool = True,
    ) -> list[EmailMessage]:
        if not self.configured:
            logger.warning("Gmail not configured; skipping email fetch.")
            return []

        messages: list[EmailMessage] = []
        try:
            mail = imaplib.IMAP4_SSL(IMAP_HOST)
            mail.login(self._user, self._app_password)
            mail.select("INBOX")

            since = (datetime.now() - timedelta(days=days)).strftime("%d-%b-%Y")
            criterion = "UNSEEN" if unread_only else "ALL"
            status, data = mail.uid("search", None, f"({criterion} SINCE {since})")
            if status != "OK":
                return messages

            for uid in data[0].split()[-limit:]:
                status, msg_data = mail.uid("fetch", uid, "(BODY.PEEK[])")
                if status != "OK" or msg_data[0] is None:
                    continue
                raw = msg_data[0][1]
                msg = email.message_from_bytes(raw)
                date_obj = parsedate_to_datetime(msg.get("Date"))
                messages.append(
                    EmailMessage(
                        uid=uid.decode(),
                        subject=_decode_header_value(msg.get("Subject", "")) or "(no subject)",
                        sender=_decode_header_value(msg.get("From", "")).split("<")[0].strip(),
                        date=date_obj.strftime("%b %d, %I:%M %p") if date_obj else "",
                        snippet=_walk_body(msg),
                    )
                )
            mail.logout()
        except Exception as error:  # noqa: BLE001 - surface any IMAP failure
            logger.exception(f"Email fetch failed: {error}")
        return messages
