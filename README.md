# TestMailbox

Disposable email inbox service for testing. Exposed as both a REST API and an MCP server.

## Quick Start

```bash
# Docker
docker compose up -d

# Or local
pip install -r requirements.txt
python run.py
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | /inboxes | Create inbox |
| GET | /inboxes/{id}/messages | List messages |
| GET | /inboxes/{id}/messages/latest | Latest message |
| GET | /inboxes/{id}/messages/{msg_id} | Full message |
| GET | /inboxes/{id}/wait?timeout=30&match=regex | Long-poll for message |
| GET | /inboxes/{id}/links | Extract links from latest email |
| DELETE | /inboxes/{id} | Delete inbox |

## MCP Tools

- `create_inbox` - Create disposable inbox
- `check_inbox` - List messages
- `wait_for_email` - Wait for email matching pattern
- `get_email_links` - Extract links from latest email
- `delete_inbox` - Cleanup

## Ports

- **8501** - REST API
- **2525** - SMTP server

## Usage Example

```bash
# Create inbox
curl -X POST http://localhost:8501/inboxes
# {"id": "abc123...", "email": "test-a1b2c3@testmailbox.dev", ...}

# Send test email
python -c "
import smtplib
from email.mime.text import MIMEText
msg = MIMEText('<a href=\"https://example.com/verify?token=abc\">Verify</a>', 'html')
msg['Subject'] = 'Verify your account'
msg['From'] = 'noreply@example.com'
msg['To'] = 'test-a1b2c3@testmailbox.dev'
with smtplib.SMTP('localhost', 2525) as s:
    s.send_message(msg)
"

# Check messages
curl http://localhost:8501/inboxes/{id}/messages/latest

# Get verification links
curl http://localhost:8501/inboxes/{id}/links
```
