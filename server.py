"""FastAPI REST API for TestMailbox."""

import asyncio
import logging
import os
import re
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

import core
import db

logger = logging.getLogger("testmailbox.api")

CLEANUP_INTERVAL = int(os.environ.get("CLEANUP_INTERVAL_SECONDS", "300"))


async def cleanup_loop():
    """Background task to purge expired inboxes every N seconds."""
    while True:
        try:
            count = db.purge_expired()
            if count > 0:
                logger.info(f"Purged {count} expired inbox(es)")
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
        await asyncio.sleep(CLEANUP_INTERVAL)


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    task = asyncio.create_task(cleanup_loop())
    logger.info("TestMailbox API started, cleanup task running")
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title="TestMailbox",
    description="Disposable email inbox service for testing",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.get("/health")
async def health():
    return {"status": "ok", "service": "testmailbox"}


@app.post("/inboxes")
async def create_inbox():
    """Create a new disposable inbox."""
    inbox = core.create_inbox()
    return inbox


@app.get("/inboxes/{inbox_id}")
async def get_inbox(inbox_id: str):
    """Get inbox details."""
    inbox = core.get_inbox(inbox_id)
    if not inbox:
        raise HTTPException(status_code=404, detail="Inbox not found")
    return inbox


@app.get("/inboxes/{inbox_id}/messages")
async def list_messages(inbox_id: str):
    """List all messages in an inbox."""
    inbox = core.get_inbox(inbox_id)
    if not inbox:
        raise HTTPException(status_code=404, detail="Inbox not found")
    messages = core.list_messages(inbox_id)
    return {"inbox_id": inbox_id, "count": len(messages), "messages": messages}


@app.get("/inboxes/{inbox_id}/messages/latest")
async def get_latest_message(inbox_id: str):
    """Get the most recent message in an inbox."""
    inbox = core.get_inbox(inbox_id)
    if not inbox:
        raise HTTPException(status_code=404, detail="Inbox not found")
    msg = core.get_latest_message(inbox_id)
    if not msg:
        raise HTTPException(status_code=404, detail="No messages in inbox")
    msg["links"] = core.extract_links(msg.get("body_html", ""))
    if not msg["links"]:
        msg["links"] = core.extract_links_from_text(msg.get("body_text", ""))
    return msg


@app.get("/inboxes/{inbox_id}/messages/{msg_id}")
async def get_message(inbox_id: str, msg_id: str):
    """Get a full message by ID (headers, body, attachments)."""
    inbox = core.get_inbox(inbox_id)
    if not inbox:
        raise HTTPException(status_code=404, detail="Inbox not found")
    msg = core.get_message(inbox_id, msg_id)
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")
    msg["links"] = core.extract_links(msg.get("body_html", ""))
    if not msg["links"]:
        msg["links"] = core.extract_links_from_text(msg.get("body_text", ""))
    return msg


@app.get("/inboxes/{inbox_id}/wait")
async def wait_for_message(
    inbox_id: str,
    timeout: int = Query(default=30, ge=1, le=120, description="Timeout in seconds"),
    match: str = Query(default=None, description="Regex pattern to match subject"),
):
    """Long-poll for a message matching an optional pattern."""
    inbox = core.get_inbox(inbox_id)
    if not inbox:
        raise HTTPException(status_code=404, detail="Inbox not found")

    pattern = None
    if match:
        try:
            pattern = re.compile(match, re.IGNORECASE)
        except re.error as e:
            raise HTTPException(status_code=400, detail=f"Invalid regex: {e}")

    elapsed = 0
    while elapsed < timeout:
        messages = core.list_messages(inbox_id)
        for msg in messages:
            if pattern is None:
                return msg
            if pattern.search(msg.get("subject", "")):
                return msg
        await asyncio.sleep(1)
        elapsed += 1

    raise HTTPException(status_code=408, detail="Timeout waiting for matching message")


@app.get("/inboxes/{inbox_id}/links")
async def get_email_links(inbox_id: str):
    """Extract all links from the latest email in an inbox."""
    inbox = core.get_inbox(inbox_id)
    if not inbox:
        raise HTTPException(status_code=404, detail="Inbox not found")
    links = core.get_email_links(inbox_id)
    return {"inbox_id": inbox_id, "links": links}


@app.delete("/inboxes/{inbox_id}")
async def delete_inbox(inbox_id: str):
    """Delete an inbox and all its messages."""
    deleted = core.delete_inbox(inbox_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Inbox not found")
    return {"status": "deleted", "inbox_id": inbox_id}
