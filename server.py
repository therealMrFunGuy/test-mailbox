"""FastAPI REST API for TestMailbox."""

import asyncio
import logging
import os
import re
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

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

LANDING_PAGE_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>TestMailbox - Disposable Email Inboxes for Testing</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <style>
    html { scroll-behavior: smooth; }
    .code-tab.active { background: #065f46; color: #fff; }
    .code-panel { display: none; }
    .code-panel.active { display: block; }
    pre code { font-size: 0.85rem; }
  </style>
</head>
<body class="bg-gray-950 text-gray-100 font-sans antialiased">

  <!-- Nav -->
  <nav class="fixed top-0 inset-x-0 z-50 bg-gray-950/80 backdrop-blur border-b border-gray-800">
    <div class="max-w-6xl mx-auto flex items-center justify-between px-6 py-4">
      <a href="#" class="text-xl font-bold text-emerald-400 tracking-tight">TestMailbox</a>
      <div class="hidden md:flex items-center gap-8 text-sm text-gray-400">
        <a href="#features" class="hover:text-emerald-400 transition">Features</a>
        <a href="#pricing" class="hover:text-emerald-400 transition">Pricing</a>
        <a href="#docs" class="hover:text-emerald-400 transition">Docs</a>
        <a href="https://github.com/therealMrFunGuy/test-mailbox" target="_blank" class="hover:text-emerald-400 transition">GitHub</a>
      </div>
    </div>
  </nav>

  <!-- Hero -->
  <section class="pt-32 pb-20 px-6">
    <div class="max-w-4xl mx-auto text-center">
      <h1 class="text-5xl md:text-6xl font-extrabold leading-tight">
        Disposable Email Inboxes<br/>
        <span class="text-emerald-400">for Testing</span>
      </h1>
      <p class="mt-6 text-lg text-gray-400 max-w-2xl mx-auto leading-relaxed">
        Spin up throwaway email addresses on demand. Long-poll for incoming messages,
        extract verification links, and integrate directly into your CI pipelines
        or MCP-powered AI agents.
      </p>
      <div class="mt-10 flex flex-col sm:flex-row items-center justify-center gap-4">
        <button id="tryBtn"
          class="px-8 py-3 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-semibold transition shadow-lg shadow-emerald-900/40 cursor-pointer">
          Try It &mdash; Create an Inbox
        </button>
        <a href="#docs"
          class="px-8 py-3 rounded-lg border border-gray-700 text-gray-300 hover:border-emerald-500 hover:text-emerald-400 transition font-semibold">
          Read the Docs
        </a>
      </div>
      <div id="tryResult" class="mt-8 hidden">
        <div class="inline-block text-left bg-gray-900 border border-gray-800 rounded-xl px-6 py-4 text-sm font-mono shadow-xl max-w-lg w-full">
          <div class="text-gray-500 mb-1">Response:</div>
          <pre id="tryOutput" class="text-emerald-300 whitespace-pre-wrap"></pre>
        </div>
      </div>
    </div>
  </section>

  <!-- Code Examples -->
  <section class="pb-20 px-6">
    <div class="max-w-4xl mx-auto">
      <h2 class="text-3xl font-bold text-center mb-10">Get Started in Seconds</h2>
      <div class="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden shadow-2xl">
        <div class="flex border-b border-gray-800">
          <button onclick="showTab('curl')" class="code-tab active px-5 py-3 text-sm font-medium transition">cURL</button>
          <button onclick="showTab('python')" class="code-tab px-5 py-3 text-sm font-medium text-gray-400 hover:text-white transition">Python</button>
          <button onclick="showTab('mcp')" class="code-tab px-5 py-3 text-sm font-medium text-gray-400 hover:text-white transition">MCP Config</button>
        </div>
        <div class="p-6">
          <div id="panel-curl" class="code-panel active">
            <pre class="text-gray-300"><code><span class="text-gray-500"># Create an inbox</span>
curl -s -X POST https://your-host/inboxes | jq .

<span class="text-gray-500"># Wait for an email (long-poll, 60s timeout)</span>
curl -s "https://your-host/inboxes/{id}/wait?timeout=60&amp;match=verify"

<span class="text-gray-500"># Get links from the latest email</span>
curl -s "https://your-host/inboxes/{id}/messages/latest" | jq '.links'</code></pre>
          </div>
          <div id="panel-python" class="code-panel">
            <pre class="text-gray-300"><code><span class="text-emerald-400">import</span> requests

<span class="text-gray-500"># Create inbox</span>
inbox = requests.post(<span class="text-amber-300">"https://your-host/inboxes"</span>).json()
email = inbox[<span class="text-amber-300">"email"</span>]
inbox_id = inbox[<span class="text-amber-300">"inbox_id"</span>]

<span class="text-gray-500"># Trigger your signup flow with `email` ...</span>

<span class="text-gray-500"># Wait for the verification email</span>
msg = requests.get(
    <span class="text-amber-300">f"https://your-host/inboxes/<span class="text-emerald-400">{inbox_id}</span>/wait"</span>,
    params={<span class="text-amber-300">"timeout"</span>: 60, <span class="text-amber-300">"match"</span>: <span class="text-amber-300">"verify"</span>}
).json()

<span class="text-emerald-400">print</span>(msg[<span class="text-amber-300">"links"</span>])</code></pre>
          </div>
          <div id="panel-mcp" class="code-panel">
            <pre class="text-gray-300"><code>{
  <span class="text-amber-300">"mcpServers"</span>: {
    <span class="text-amber-300">"testmailbox"</span>: {
      <span class="text-amber-300">"command"</span>: <span class="text-amber-300">"uvx"</span>,
      <span class="text-amber-300">"args"</span>: [<span class="text-amber-300">"mcp-server-testmailbox"</span>],
      <span class="text-amber-300">"env"</span>: {
        <span class="text-amber-300">"TESTMAILBOX_API_URL"</span>: <span class="text-amber-300">"https://your-host"</span>
      }
    }
  }
}</code></pre>
          </div>
        </div>
      </div>
    </div>
  </section>

  <!-- Features -->
  <section id="features" class="pb-20 px-6">
    <div class="max-w-6xl mx-auto">
      <h2 class="text-3xl font-bold text-center mb-12">Features</h2>
      <div class="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div class="bg-gray-900 border border-gray-800 rounded-xl p-6 hover:border-emerald-700 transition">
          <div class="w-12 h-12 rounded-lg bg-emerald-900/50 flex items-center justify-center text-emerald-400 text-2xl mb-4">+</div>
          <h3 class="text-lg font-semibold mb-2">Instant Inboxes</h3>
          <p class="text-gray-400 text-sm leading-relaxed">Create a unique disposable email address with a single POST request. No signup, no config, no waiting.</p>
        </div>
        <div class="bg-gray-900 border border-gray-800 rounded-xl p-6 hover:border-emerald-700 transition">
          <div class="w-12 h-12 rounded-lg bg-emerald-900/50 flex items-center justify-center text-emerald-400 text-2xl mb-4">&#8987;</div>
          <h3 class="text-lg font-semibold mb-2">Long-Poll Waiting</h3>
          <p class="text-gray-400 text-sm leading-relaxed">Block until an email arrives with optional subject regex matching. No polling loops needed in your tests.</p>
        </div>
        <div class="bg-gray-900 border border-gray-800 rounded-xl p-6 hover:border-emerald-700 transition">
          <div class="w-12 h-12 rounded-lg bg-emerald-900/50 flex items-center justify-center text-emerald-400 text-2xl mb-4">&#128279;</div>
          <h3 class="text-lg font-semibold mb-2">Link Extraction</h3>
          <p class="text-gray-400 text-sm leading-relaxed">Automatically extract verification links and URLs from HTML and plain-text email bodies.</p>
        </div>
        <div class="bg-gray-900 border border-gray-800 rounded-xl p-6 hover:border-emerald-700 transition">
          <div class="w-12 h-12 rounded-lg bg-emerald-900/50 flex items-center justify-center text-emerald-400 text-2xl mb-4">&#9854;</div>
          <h3 class="text-lg font-semibold mb-2">Auto-Cleanup</h3>
          <p class="text-gray-400 text-sm leading-relaxed">Expired inboxes are automatically purged. Zero maintenance, zero data leaks, zero clutter.</p>
        </div>
      </div>
    </div>
  </section>

  <!-- Pricing -->
  <section id="pricing" class="pb-20 px-6">
    <div class="max-w-5xl mx-auto">
      <h2 class="text-3xl font-bold text-center mb-4">Pricing</h2>
      <p class="text-center text-gray-400 mb-12">Start free. Scale when you need to.</p>
      <div class="grid md:grid-cols-3 gap-6">
        <!-- Free -->
        <div class="bg-gray-900 border border-gray-800 rounded-xl p-8 flex flex-col">
          <h3 class="text-lg font-semibold text-gray-300">Free</h3>
          <div class="mt-4 mb-6"><span class="text-4xl font-bold text-white">$0</span><span class="text-gray-500">/mo</span></div>
          <ul class="space-y-3 text-sm text-gray-400 flex-1">
            <li class="flex items-start gap-2"><span class="text-emerald-400 mt-0.5">&#10003;</span> 50 inboxes / day</li>
            <li class="flex items-start gap-2"><span class="text-emerald-400 mt-0.5">&#10003;</span> 15 minute TTL</li>
            <li class="flex items-start gap-2"><span class="text-emerald-400 mt-0.5">&#10003;</span> REST API + MCP server</li>
            <li class="flex items-start gap-2"><span class="text-emerald-400 mt-0.5">&#10003;</span> Community support</li>
          </ul>
          <a href="#docs" class="mt-8 block text-center py-2.5 rounded-lg border border-gray-700 text-gray-300 hover:border-emerald-500 hover:text-emerald-400 transition font-medium text-sm">Get Started</a>
        </div>
        <!-- Pro -->
        <div class="bg-gray-900 border-2 border-emerald-600 rounded-xl p-8 flex flex-col relative shadow-lg shadow-emerald-900/20">
          <span class="absolute -top-3 left-1/2 -translate-x-1/2 bg-emerald-600 text-white text-xs font-bold px-3 py-1 rounded-full">POPULAR</span>
          <h3 class="text-lg font-semibold text-emerald-400">Pro</h3>
          <div class="mt-4 mb-6"><span class="text-4xl font-bold text-white">$12</span><span class="text-gray-500">/mo</span></div>
          <ul class="space-y-3 text-sm text-gray-400 flex-1">
            <li class="flex items-start gap-2"><span class="text-emerald-400 mt-0.5">&#10003;</span> Unlimited inboxes</li>
            <li class="flex items-start gap-2"><span class="text-emerald-400 mt-0.5">&#10003;</span> 24 hour TTL</li>
            <li class="flex items-start gap-2"><span class="text-emerald-400 mt-0.5">&#10003;</span> Webhook notifications</li>
            <li class="flex items-start gap-2"><span class="text-emerald-400 mt-0.5">&#10003;</span> Priority support</li>
          </ul>
          <button class="mt-8 block w-full text-center py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-medium text-sm transition cursor-pointer">Subscribe</button>
        </div>
        <!-- Enterprise -->
        <div class="bg-gray-900 border border-gray-800 rounded-xl p-8 flex flex-col">
          <h3 class="text-lg font-semibold text-gray-300">Enterprise</h3>
          <div class="mt-4 mb-6"><span class="text-4xl font-bold text-white">Custom</span></div>
          <ul class="space-y-3 text-sm text-gray-400 flex-1">
            <li class="flex items-start gap-2"><span class="text-emerald-400 mt-0.5">&#10003;</span> Custom TTL &amp; retention</li>
            <li class="flex items-start gap-2"><span class="text-emerald-400 mt-0.5">&#10003;</span> SLA guarantee</li>
            <li class="flex items-start gap-2"><span class="text-emerald-400 mt-0.5">&#10003;</span> SMTP relay integration</li>
            <li class="flex items-start gap-2"><span class="text-emerald-400 mt-0.5">&#10003;</span> Dedicated support</li>
          </ul>
          <a href="mailto:hello@rjctdlabs.xyz" class="mt-8 block text-center py-2.5 rounded-lg border border-gray-700 text-gray-300 hover:border-emerald-500 hover:text-emerald-400 transition font-medium text-sm">Contact Us</a>
        </div>
      </div>
    </div>
  </section>

  <!-- API Reference -->
  <section id="docs" class="pb-20 px-6">
    <div class="max-w-4xl mx-auto">
      <h2 class="text-3xl font-bold text-center mb-12">API Reference</h2>
      <div class="space-y-4">
        <div class="bg-gray-900 border border-gray-800 rounded-xl p-6">
          <div class="flex items-center gap-3 mb-3">
            <span class="px-2.5 py-1 rounded text-xs font-bold bg-emerald-900 text-emerald-300">POST</span>
            <code class="text-sm text-white font-mono">/inboxes</code>
          </div>
          <p class="text-gray-400 text-sm">Create a new disposable inbox. Returns <code class="text-emerald-400">inbox_id</code>, <code class="text-emerald-400">email</code>, and <code class="text-emerald-400">expires_at</code>. No parameters required.</p>
        </div>
        <div class="bg-gray-900 border border-gray-800 rounded-xl p-6">
          <div class="flex items-center gap-3 mb-3">
            <span class="px-2.5 py-1 rounded text-xs font-bold bg-blue-900 text-blue-300">GET</span>
            <code class="text-sm text-white font-mono">/inboxes/{inbox_id}/wait</code>
          </div>
          <p class="text-gray-400 text-sm mb-3">Long-poll until a message arrives in the inbox. Returns the first matching message.</p>
          <div class="text-xs text-gray-500 space-y-1">
            <div><code class="text-gray-400">timeout</code> <span class="text-gray-600">(int, 1-120, default 30)</span> &mdash; Seconds to wait before 408 timeout</div>
            <div><code class="text-gray-400">match</code> <span class="text-gray-600">(string, optional)</span> &mdash; Regex pattern to match against subject line</div>
          </div>
        </div>
        <div class="bg-gray-900 border border-gray-800 rounded-xl p-6">
          <div class="flex items-center gap-3 mb-3">
            <span class="px-2.5 py-1 rounded text-xs font-bold bg-blue-900 text-blue-300">GET</span>
            <code class="text-sm text-white font-mono">/inboxes/{inbox_id}/messages/latest</code>
          </div>
          <p class="text-gray-400 text-sm">Retrieve the most recent message in an inbox. Response includes <code class="text-emerald-400">subject</code>, <code class="text-emerald-400">body_html</code>, <code class="text-emerald-400">body_text</code>, and extracted <code class="text-emerald-400">links</code>.</p>
        </div>
        <div class="bg-gray-900 border border-gray-800 rounded-xl p-6">
          <div class="flex items-center gap-3 mb-3">
            <span class="px-2.5 py-1 rounded text-xs font-bold bg-blue-900 text-blue-300">GET</span>
            <code class="text-sm text-white font-mono">/inboxes/{inbox_id}/messages</code>
          </div>
          <p class="text-gray-400 text-sm">List all messages in an inbox. Returns <code class="text-emerald-400">count</code> and <code class="text-emerald-400">messages</code> array.</p>
        </div>
        <div class="bg-gray-900 border border-gray-800 rounded-xl p-6">
          <div class="flex items-center gap-3 mb-3">
            <span class="px-2.5 py-1 rounded text-xs font-bold bg-blue-900 text-blue-300">GET</span>
            <code class="text-sm text-white font-mono">/inboxes/{inbox_id}/links</code>
          </div>
          <p class="text-gray-400 text-sm">Extract all links from the latest email. Returns a <code class="text-emerald-400">links</code> array of URLs found in the message body.</p>
        </div>
        <div class="bg-gray-900 border border-gray-800 rounded-xl p-6">
          <div class="flex items-center gap-3 mb-3">
            <span class="px-2.5 py-1 rounded text-xs font-bold bg-red-900 text-red-300">DELETE</span>
            <code class="text-sm text-white font-mono">/inboxes/{inbox_id}</code>
          </div>
          <p class="text-gray-400 text-sm">Delete an inbox and all its messages immediately.</p>
        </div>
      </div>
    </div>
  </section>

  <!-- Footer -->
  <footer class="border-t border-gray-800 py-10 px-6">
    <div class="max-w-6xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4 text-sm text-gray-500">
      <div class="flex items-center gap-6">
        <a href="https://github.com/therealMrFunGuy/test-mailbox" target="_blank" class="hover:text-emerald-400 transition">GitHub</a>
        <a href="https://pypi.org/project/mcp-server-testmailbox/" target="_blank" class="hover:text-emerald-400 transition">PyPI</a>
        <a href="/docs" class="hover:text-emerald-400 transition">OpenAPI Docs</a>
      </div>
      <div>Powered by <a href="https://rjctdlabs.xyz" target="_blank" class="text-emerald-500 hover:text-emerald-400 transition">rjctdlabs.xyz</a></div>
    </div>
  </footer>

  <script>
    function showTab(name) {
      document.querySelectorAll('.code-tab').forEach(t => t.classList.remove('active'));
      document.querySelectorAll('.code-panel').forEach(p => p.classList.remove('active'));
      event.target.classList.add('active');
      document.getElementById('panel-' + name).classList.add('active');
    }

    document.getElementById('tryBtn').addEventListener('click', async () => {
      const btn = document.getElementById('tryBtn');
      const result = document.getElementById('tryResult');
      const output = document.getElementById('tryOutput');
      btn.disabled = true;
      btn.textContent = 'Creating...';
      try {
        const res = await fetch('/inboxes', { method: 'POST' });
        const data = await res.json();
        output.textContent = JSON.stringify(data, null, 2);
        result.classList.remove('hidden');
      } catch (err) {
        output.textContent = 'Error: ' + err.message;
        result.classList.remove('hidden');
      }
      btn.disabled = false;
      btn.textContent = 'Try It \\u2014 Create an Inbox';
    });
  </script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
async def landing_page():
    """Serve the landing page."""
    return HTMLResponse(content=LANDING_PAGE_HTML)


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
