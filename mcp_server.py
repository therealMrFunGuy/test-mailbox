"""MCP server for TestMailbox - exposes inbox tools for AI agents."""

import asyncio
import re
import logging

from mcp.server.fastmcp import FastMCP

import core
import db

logger = logging.getLogger("testmailbox.mcp")

mcp = FastMCP(
    "TestMailbox",
    description="Disposable email inbox service for testing. Create inboxes, receive emails, extract verification links.",
)


@mcp.tool()
def create_inbox() -> dict:
    """Create a new disposable email inbox.

    Returns an inbox with a random email address like test-a1b2c3@testmailbox.dev.
    Inboxes auto-expire after 1 hour.

    Returns:
        dict with id, email, created_at, expires_at
    """
    db.init_db()
    inbox = core.create_inbox()
    return inbox


@mcp.tool()
def check_inbox(inbox_id: str) -> dict:
    """List all messages in a disposable inbox.

    Args:
        inbox_id: The inbox ID returned from create_inbox

    Returns:
        dict with inbox_id, count, and list of messages (newest first)
    """
    db.init_db()
    inbox = core.get_inbox(inbox_id)
    if not inbox:
        return {"error": "Inbox not found"}
    messages = core.list_messages(inbox_id)
    return {"inbox_id": inbox_id, "count": len(messages), "messages": messages}


@mcp.tool()
def wait_for_email(inbox_id: str, subject_pattern: str = "", from_pattern: str = "", timeout: int = 30) -> dict:
    """Wait for an email matching subject/from pattern to arrive in the inbox.

    Polls the inbox every second until a matching email arrives or timeout.

    Args:
        inbox_id: The inbox ID to watch
        subject_pattern: Optional regex to match against email subject
        from_pattern: Optional regex to match against sender address
        timeout: Maximum seconds to wait (1-120, default 30)

    Returns:
        The matching message dict, or error if timeout
    """
    db.init_db()
    inbox = core.get_inbox(inbox_id)
    if not inbox:
        return {"error": "Inbox not found"}

    timeout = max(1, min(120, timeout))
    subject_re = re.compile(subject_pattern, re.IGNORECASE) if subject_pattern else None
    from_re = re.compile(from_pattern, re.IGNORECASE) if from_pattern else None

    import time
    start = time.time()
    while time.time() - start < timeout:
        messages = core.list_messages(inbox_id)
        for msg in messages:
            subject_match = subject_re.search(msg.get("subject", "")) if subject_re else True
            from_match = from_re.search(msg.get("from_addr", "")) if from_re else True
            if subject_match and from_match:
                msg["links"] = core.extract_links(msg.get("body_html", ""))
                if not msg["links"]:
                    msg["links"] = core.extract_links_from_text(msg.get("body_text", ""))
                return msg
        time.sleep(1)

    return {"error": f"No matching email arrived within {timeout} seconds"}


@mcp.tool()
def get_email_links(inbox_id: str) -> dict:
    """Extract all links from the latest email in an inbox.

    Perfect for finding verification links, password reset URLs, etc.

    Args:
        inbox_id: The inbox ID

    Returns:
        dict with inbox_id and list of links
    """
    db.init_db()
    inbox = core.get_inbox(inbox_id)
    if not inbox:
        return {"error": "Inbox not found"}
    links = core.get_email_links(inbox_id)
    return {"inbox_id": inbox_id, "links": links, "count": len(links)}


@mcp.tool()
def delete_inbox(inbox_id: str) -> dict:
    """Delete a disposable inbox and all its messages.

    Args:
        inbox_id: The inbox ID to delete

    Returns:
        dict with status
    """
    db.init_db()
    deleted = core.delete_inbox(inbox_id)
    if not deleted:
        return {"error": "Inbox not found"}
    return {"status": "deleted", "inbox_id": inbox_id}


def main():
    """Run the MCP server via stdio transport."""
    db.init_db()
    logger.info("Starting TestMailbox MCP server")
    mcp.run(transport="stdio")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
