"""
HTTP Exporter for sending telemetry data to the observability API.
"""

import asyncio
import atexit
import json
import logging
import queue
import threading
import time
from typing import Any, Dict, List, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ..config import ObservabilityConfig
from ..models import BaseEvent

logger = logging.getLogger(__name__)


class HTTPExporter:
    """
    HTTP exporter that batches and sends events to the observability API.

    Features:
    - Automatic batching
    - Background thread for async sending
    - Retry with exponential backoff
    - Graceful shutdown
    """

    def __init__(self, config: ObservabilityConfig):
        self.config = config
        self._queue: queue.Queue = queue.Queue(maxsize=config.batch.max_queue_size)
        self._shutdown_event = threading.Event()
        self._worker_thread: Optional[threading.Thread] = None
        self._session: Optional[requests.Session] = None
        self._started = False

        # Initialize session with retry logic
        self._init_session()

    def _init_session(self):
        """Initialize HTTP session with retry configuration."""
        self._session = requests.Session()

        retry_strategy = Retry(
            total=self.config.retry.max_retries,
            backoff_factor=self.config.retry.initial_backoff_seconds,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["POST"],
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        self._session.mount("http://", adapter)
        self._session.mount("https://", adapter)

        # Set default headers
        self._session.headers.update({
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.config.api_key}",
            "X-Agent-ID": self.config.agent_id,
            "User-Agent": f"genai-observability-sdk/{self.config.agent_version}",
        })

    def start(self):
        """Start the background worker thread."""
        if self._started:
            return

        self._started = True
        self._shutdown_event.clear()
        self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker_thread.start()

        # Register shutdown handler
        atexit.register(self.shutdown)

        if self.config.debug:
            logger.debug("HTTPExporter started")

    def shutdown(self, timeout: float = 5.0):
        """Gracefully shutdown the exporter."""
        if not self._started:
            return

        if self.config.debug:
            logger.debug("Shutting down HTTPExporter...")

        # Signal shutdown
        self._shutdown_event.set()

        # Wait for worker to finish
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=timeout)

        # Flush remaining events
        self._flush_queue()

        # Close session
        if self._session:
            self._session.close()

        self._started = False

        if self.config.debug:
            logger.debug("HTTPExporter shutdown complete")

    def export(self, event: BaseEvent):
        """Add an event to the export queue."""
        if not self.config.enabled:
            return

        if not self._started:
            self.start()

        try:
            self._queue.put_nowait(event)
        except queue.Full:
            logger.warning("Event queue is full, dropping event")

    def export_batch(self, events: List[BaseEvent]):
        """Add multiple events to the export queue."""
        for event in events:
            self.export(event)

    def _worker_loop(self):
        """Background worker that batches and sends events."""
        batch: List[BaseEvent] = []
        last_flush_time = time.time()

        while not self._shutdown_event.is_set():
            try:
                # Try to get an event with timeout
                try:
                    event = self._queue.get(timeout=0.1)
                    batch.append(event)
                except queue.Empty:
                    pass

                # Check if we should flush
                current_time = time.time()
                should_flush = (
                    len(batch) >= self.config.batch.max_batch_size or
                    (len(batch) > 0 and current_time - last_flush_time >= self.config.batch.max_batch_interval_seconds)
                )

                if should_flush:
                    self._send_batch(batch)
                    batch = []
                    last_flush_time = current_time

            except Exception as e:
                logger.error(f"Error in worker loop: {e}")

        # Final flush on shutdown
        if batch:
            self._send_batch(batch)

    def _flush_queue(self):
        """Flush all remaining events in the queue."""
        batch: List[BaseEvent] = []

        while True:
            try:
                event = self._queue.get_nowait()
                batch.append(event)

                if len(batch) >= self.config.batch.max_batch_size:
                    self._send_batch(batch)
                    batch = []
            except queue.Empty:
                break

        if batch:
            self._send_batch(batch)

    def _send_batch(self, batch: List[BaseEvent]):
        """Send a batch of events to the API."""
        if not batch:
            return

        endpoint = f"{self.config.api_endpoint.rstrip('/')}/v1/events"

        payload = {
            "agent_id": self.config.agent_id,
            "agent_type": self.config.agent_type,
            "agent_version": self.config.agent_version,
            "environment": self.config.environment,
            "events": [event.to_dict() for event in batch],
            "global_tags": self.config.global_tags,
        }

        try:
            response = self._session.post(
                endpoint,
                data=json.dumps(payload, default=str),
                timeout=30,
            )

            if response.status_code == 200 or response.status_code == 202:
                if self.config.debug:
                    logger.debug(f"Successfully sent {len(batch)} events")
            else:
                logger.warning(
                    f"Failed to send events: {response.status_code} - {response.text}"
                )

        except requests.exceptions.RequestException as e:
            logger.error(f"Error sending events: {e}")

    def flush(self):
        """Force flush all pending events."""
        self._flush_queue()


class AsyncHTTPExporter:
    """
    Async HTTP exporter for use with asyncio-based applications.
    """

    def __init__(self, config: ObservabilityConfig):
        self.config = config
        self._queue: asyncio.Queue = None
        self._task: Optional[asyncio.Task] = None
        self._shutdown = False

    async def start(self):
        """Start the async exporter."""
        self._queue = asyncio.Queue(maxsize=self.config.batch.max_queue_size)
        self._shutdown = False
        self._task = asyncio.create_task(self._worker_loop())

    async def shutdown(self):
        """Shutdown the async exporter."""
        self._shutdown = True
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def export(self, event: BaseEvent):
        """Add an event to the export queue."""
        if not self.config.enabled:
            return

        try:
            self._queue.put_nowait(event)
        except asyncio.QueueFull:
            logger.warning("Event queue is full, dropping event")

    async def _worker_loop(self):
        """Background worker that batches and sends events."""
        try:
            import aiohttp
        except ImportError:
            logger.error("aiohttp is required for AsyncHTTPExporter. Install with: pip install aiohttp")
            return

        batch: List[BaseEvent] = []
        last_flush_time = time.time()

        async with aiohttp.ClientSession() as session:
            while not self._shutdown:
                try:
                    # Try to get an event with timeout
                    try:
                        event = await asyncio.wait_for(
                            self._queue.get(),
                            timeout=0.1
                        )
                        batch.append(event)
                    except asyncio.TimeoutError:
                        pass

                    # Check if we should flush
                    current_time = time.time()
                    should_flush = (
                        len(batch) >= self.config.batch.max_batch_size or
                        (len(batch) > 0 and current_time - last_flush_time >= self.config.batch.max_batch_interval_seconds)
                    )

                    if should_flush:
                        await self._send_batch(session, batch)
                        batch = []
                        last_flush_time = current_time

                except Exception as e:
                    logger.error(f"Error in async worker loop: {e}")

    async def _send_batch(self, session, batch: List[BaseEvent]):
        """Send a batch of events using aiohttp."""
        if not batch:
            return

        endpoint = f"{self.config.api_endpoint.rstrip('/')}/v1/events"

        payload = {
            "agent_id": self.config.agent_id,
            "agent_type": self.config.agent_type,
            "agent_version": self.config.agent_version,
            "environment": self.config.environment,
            "events": [event.to_dict() for event in batch],
            "global_tags": self.config.global_tags,
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.config.api_key}",
            "X-Agent-ID": self.config.agent_id,
        }

        try:
            async with session.post(
                endpoint,
                json=payload,
                headers=headers,
                timeout=30,
            ) as response:
                if response.status in (200, 202):
                    if self.config.debug:
                        logger.debug(f"Successfully sent {len(batch)} events")
                else:
                    text = await response.text()
                    logger.warning(f"Failed to send events: {response.status} - {text}")

        except Exception as e:
            logger.error(f"Error sending events: {e}")
