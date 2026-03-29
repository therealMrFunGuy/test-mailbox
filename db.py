"""SQLite database operations for TestMailbox."""

import sqlite3
import os
import threading
from datetime import datetime, timezone
from typing import Optional

DB_PATH = os.environ.get("DB_PATH", "/data/testmailbox/mailbox.db")

_local = threading.local()


def get_conn() -> sqlite3.Connection:
    """Get a thread-local SQLite connection."""
    if not hasattr(_local, "conn") or _local.conn is None:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        _local.conn = sqlite3.connect(DB_PATH)
        _local.conn.row_factory = sqlite3.Row
        _local.conn.execute("PRAGMA journal_mode=WAL")
        _local.conn.execute("PRAGMA foreign_keys=ON")
    return _local.conn


def init_db():
    """Create tables if they don't exist."""
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS inboxes (
            id TEXT PRIMARY KEY,
            email TEXT NOT NULL UNIQUE,
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY,
            inbox_id TEXT NOT NULL,
            from_addr TEXT NOT NULL,
            to_addr TEXT NOT NULL,
            subject TEXT NOT NULL DEFAULT '',
            body_text TEXT NOT NULL DEFAULT '',
            body_html TEXT NOT NULL DEFAULT '',
            raw TEXT NOT NULL DEFAULT '',
            received_at TEXT NOT NULL,
            FOREIGN KEY (inbox_id) REFERENCES inboxes(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_messages_inbox_id ON messages(inbox_id);
        CREATE INDEX IF NOT EXISTS idx_messages_received_at ON messages(received_at);
        CREATE INDEX IF NOT EXISTS idx_inboxes_email ON inboxes(email);
        CREATE INDEX IF NOT EXISTS idx_inboxes_expires_at ON inboxes(expires_at);
    """)
    conn.commit()


def create_inbox(inbox_id: str, email: str, created_at: str, expires_at: str) -> dict:
    conn = get_conn()
    conn.execute(
        "INSERT INTO inboxes (id, email, created_at, expires_at) VALUES (?, ?, ?, ?)",
        (inbox_id, email, created_at, expires_at),
    )
    conn.commit()
    return {"id": inbox_id, "email": email, "created_at": created_at, "expires_at": expires_at}


def get_inbox(inbox_id: str) -> Optional[dict]:
    conn = get_conn()
    row = conn.execute("SELECT * FROM inboxes WHERE id = ?", (inbox_id,)).fetchone()
    return dict(row) if row else None


def get_inbox_by_email(email: str) -> Optional[dict]:
    conn = get_conn()
    row = conn.execute("SELECT * FROM inboxes WHERE email = ?", (email,)).fetchone()
    return dict(row) if row else None


def delete_inbox(inbox_id: str) -> bool:
    conn = get_conn()
    cur = conn.execute("DELETE FROM inboxes WHERE id = ?", (inbox_id,))
    conn.commit()
    return cur.rowcount > 0


def purge_expired():
    """Delete all expired inboxes (and cascade to messages)."""
    conn = get_conn()
    now = datetime.now(timezone.utc).isoformat()
    cur = conn.execute("DELETE FROM inboxes WHERE expires_at < ?", (now,))
    conn.commit()
    return cur.rowcount


def store_message(
    msg_id: str,
    inbox_id: str,
    from_addr: str,
    to_addr: str,
    subject: str,
    body_text: str,
    body_html: str,
    raw: str,
    received_at: str,
) -> dict:
    conn = get_conn()
    conn.execute(
        """INSERT INTO messages (id, inbox_id, from_addr, to_addr, subject, body_text, body_html, raw, received_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (msg_id, inbox_id, from_addr, to_addr, subject, body_text, body_html, raw, received_at),
    )
    conn.commit()
    return {
        "id": msg_id,
        "inbox_id": inbox_id,
        "from_addr": from_addr,
        "to_addr": to_addr,
        "subject": subject,
        "body_text": body_text,
        "body_html": body_html,
        "received_at": received_at,
    }


def list_messages(inbox_id: str) -> list[dict]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, inbox_id, from_addr, to_addr, subject, body_text, body_html, received_at "
        "FROM messages WHERE inbox_id = ? ORDER BY received_at DESC",
        (inbox_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def get_message(inbox_id: str, msg_id: str) -> Optional[dict]:
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM messages WHERE inbox_id = ? AND id = ?",
        (inbox_id, msg_id),
    ).fetchone()
    return dict(row) if row else None


def get_latest_message(inbox_id: str) -> Optional[dict]:
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM messages WHERE inbox_id = ? ORDER BY received_at DESC LIMIT 1",
        (inbox_id,),
    ).fetchone()
    return dict(row) if row else None
