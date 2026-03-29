"""Shared inbox/message logic for TestMailbox."""

import os
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from bs4 import BeautifulSoup

import db

DOMAIN = os.environ.get("DOMAIN", "testmailbox.dev")
INBOX_TTL_MINUTES = int(os.environ.get("INBOX_TTL_MINUTES", "60"))


def generate_email() -> str:
    """Generate a random email address like test-a1b2c3@testmailbox.dev."""
    short_id = uuid.uuid4().hex[:6]
    return f"test-{short_id}@{DOMAIN}"


def create_inbox() -> dict:
    """Create a new disposable inbox."""
    inbox_id = uuid.uuid4().hex
    email = generate_email()
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=INBOX_TTL_MINUTES)
    return db.create_inbox(
        inbox_id=inbox_id,
        email=email,
        created_at=now.isoformat(),
        expires_at=expires_at.isoformat(),
    )


def get_inbox(inbox_id: str) -> Optional[dict]:
    return db.get_inbox(inbox_id)


def delete_inbox(inbox_id: str) -> bool:
    return db.delete_inbox(inbox_id)


def list_messages(inbox_id: str) -> list[dict]:
    return db.list_messages(inbox_id)


def get_message(inbox_id: str, msg_id: str) -> Optional[dict]:
    return db.get_message(inbox_id, msg_id)


def get_latest_message(inbox_id: str) -> Optional[dict]:
    return db.get_latest_message(inbox_id)


def extract_links(html: str) -> list[str]:
    """Extract all href links from HTML body."""
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    links = []
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        if href and href.startswith(("http://", "https://")):
            links.append(href)
    return links


def extract_links_from_text(text: str) -> list[str]:
    """Extract URLs from plain text body as fallback."""
    if not text:
        return []
    url_pattern = re.compile(r'https?://[^\s<>"\')\]]+')
    return url_pattern.findall(text)


def get_email_links(inbox_id: str) -> list[str]:
    """Get all links from the latest email in an inbox."""
    msg = get_latest_message(inbox_id)
    if not msg:
        return []
    links = extract_links(msg.get("body_html", ""))
    if not links:
        links = extract_links_from_text(msg.get("body_text", ""))
    return links


def receive_message(
    from_addr: str,
    to_addr: str,
    subject: str,
    body_text: str,
    body_html: str,
    raw: str,
) -> Optional[dict]:
    """Process an incoming email message. Returns stored message or None if no matching inbox."""
    local_part = to_addr.split("@")[0] if "@" in to_addr else to_addr
    domain = to_addr.split("@")[1] if "@" in to_addr else ""

    # Find inbox by email address
    inbox = db.get_inbox_by_email(to_addr)
    if not inbox:
        # Try case-insensitive match
        inbox = db.get_inbox_by_email(to_addr.lower())
    if not inbox:
        return None

    # Check if inbox has expired
    expires_at = datetime.fromisoformat(inbox["expires_at"])
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) > expires_at:
        return None

    msg_id = uuid.uuid4().hex
    now = datetime.now(timezone.utc).isoformat()

    return db.store_message(
        msg_id=msg_id,
        inbox_id=inbox["id"],
        from_addr=from_addr,
        to_addr=to_addr,
        subject=subject,
        body_text=body_text,
        body_html=body_html,
        raw=raw,
        received_at=now,
    )
