"""Lightweight SMTP server for TestMailbox using aiosmtpd."""

import asyncio
import email
import logging
import os
from email.policy import default as default_policy

from aiosmtpd.controller import Controller
from aiosmtpd.smtp import SMTP, Envelope, Session

import db
import core

logger = logging.getLogger("testmailbox.smtp")

SMTP_HOST = os.environ.get("SMTP_HOST", "0.0.0.0")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "2525"))
DOMAIN = os.environ.get("DOMAIN", "testmailbox.dev")


class TestMailboxHandler:
    """SMTP handler that accepts mail for any address at the configured domain."""

    async def handle_RCPT(self, server: SMTP, session: Session, envelope: Envelope, address: str, rcpt_options: list):
        # Accept mail for our domain only
        if "@" in address:
            addr_domain = address.split("@")[1].lower()
            if addr_domain == DOMAIN.lower():
                envelope.rcpt_tos.append(address)
                return "250 OK"
        return f"550 Not accepting mail for {address}"

    async def handle_DATA(self, server: SMTP, session: Session, envelope: Envelope):
        raw_data = envelope.content
        if isinstance(raw_data, bytes):
            raw_str = raw_data.decode("utf-8", errors="replace")
        else:
            raw_str = raw_data

        # Parse the email
        msg = email.message_from_string(raw_str, policy=default_policy)

        subject = str(msg.get("Subject", ""))
        from_addr = str(msg.get("From", envelope.mail_from or ""))

        # Extract body parts
        body_text = ""
        body_html = ""

        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                try:
                    payload = part.get_content()
                except Exception:
                    continue
                if isinstance(payload, str):
                    if content_type == "text/plain" and not body_text:
                        body_text = payload
                    elif content_type == "text/html" and not body_html:
                        body_html = payload
        else:
            content_type = msg.get_content_type()
            try:
                payload = msg.get_content()
            except Exception:
                payload = raw_str
            if isinstance(payload, str):
                if content_type == "text/html":
                    body_html = payload
                else:
                    body_text = payload

        # Deliver to each recipient
        delivered = 0
        for rcpt in envelope.rcpt_tos:
            result = core.receive_message(
                from_addr=from_addr,
                to_addr=rcpt,
                subject=subject,
                body_text=body_text,
                body_html=body_html,
                raw=raw_str,
            )
            if result:
                delivered += 1
                logger.info(f"Delivered message to {rcpt} (inbox={result['inbox_id']}, subject={subject!r})")
            else:
                logger.warning(f"No active inbox found for {rcpt}")

        if delivered > 0:
            return "250 Message accepted for delivery"
        else:
            return "550 No valid inbox found for recipients"


async def start_smtp_server():
    """Start the SMTP server. Returns the controller for shutdown."""
    handler = TestMailboxHandler()
    controller = Controller(
        handler,
        hostname=SMTP_HOST,
        port=SMTP_PORT,
        ready_timeout=5.0,
    )
    controller.start()
    logger.info(f"SMTP server listening on {SMTP_HOST}:{SMTP_PORT} for @{DOMAIN}")
    return controller


def stop_smtp_server(controller: Controller):
    """Stop the SMTP server."""
    controller.stop()
    logger.info("SMTP server stopped")
