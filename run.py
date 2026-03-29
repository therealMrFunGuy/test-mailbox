"""Starts both SMTP server and FastAPI server together in one process."""

import asyncio
import logging
import os
import signal

import uvicorn

import db
from smtp_server import start_smtp_server, stop_smtp_server

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("testmailbox")

API_HOST = os.environ.get("API_HOST", "0.0.0.0")
API_PORT = int(os.environ.get("API_PORT", "8501"))


async def main():
    # Initialize database
    db.init_db()
    logger.info("Database initialized")

    # Start SMTP server
    smtp_controller = await start_smtp_server()

    # Start FastAPI via uvicorn
    config = uvicorn.Config(
        "server:app",
        host=API_HOST,
        port=API_PORT,
        log_level="info",
        access_log=True,
    )
    uvicorn_server = uvicorn.Server(config)

    # Handle shutdown signals
    loop = asyncio.get_event_loop()
    shutdown_event = asyncio.Event()

    def handle_shutdown(sig, frame):
        logger.info(f"Received signal {sig}, shutting down...")
        shutdown_event.set()

    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    # Run uvicorn in background
    uvicorn_task = asyncio.create_task(uvicorn_server.serve())

    logger.info(f"TestMailbox running — API on :{API_PORT}, SMTP on :{os.environ.get('SMTP_PORT', '2525')}")

    # Wait for shutdown or uvicorn exit
    done, pending = await asyncio.wait(
        [uvicorn_task, asyncio.create_task(shutdown_event.wait())],
        return_when=asyncio.FIRST_COMPLETED,
    )

    # Cleanup
    stop_smtp_server(smtp_controller)
    if not uvicorn_task.done():
        uvicorn_server.should_exit = True
        await uvicorn_task

    logger.info("TestMailbox shut down cleanly")


if __name__ == "__main__":
    asyncio.run(main())
