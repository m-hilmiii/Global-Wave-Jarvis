"""
JARVIS High-Performance In-Memory Pub/Sub & Task Event Bus
Provides loose coupling, non-blocking asynchronous event distribution,
worker pool execution, and TTL-based memory leak prevention without external daemon overhead.
"""

import asyncio
import time
import uuid
import threading
from typing import Dict, Any, List, Callable, Optional, Set
from collections import defaultdict
from core_jarvis.logger import get_logger

logger = get_logger("Jarvis.EventBus")


class Event:
    """Encapsulates a timestamped event with automatic TTL expiration."""
    def __init__(self, topic: str, data: Any, ttl_seconds: float = 300.0, event_id: Optional[str] = None):
        self.event_id = event_id or uuid.uuid4().hex[:12]
        self.topic = topic
        self.data = data
        self.created_at = time.time()
        self.expires_at = self.created_at + ttl_seconds

    def is_expired(self) -> bool:
        return time.time() > self.expires_at

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "topic": self.topic,
            "data": self.data,
            "created_at": self.created_at,
            "expires_at": self.expires_at
        }


class EventBus:
    """
    In-Memory Pub/Sub and Asynchronous Task Broker.
    Designed to emulate Redis Pub/Sub semantics natively with zero RAM bloat for RX 9060 XT workstations.
    """
    def __init__(self, max_history_per_topic: int = 50, cleanup_interval_seconds: float = 60.0):
        self._subscribers: Dict[str, List[Callable[[Event], Any]]] = defaultdict(list)
        self._async_subscribers: Dict[str, List[Callable[[Event], Any]]] = defaultdict(list)
        self._history: Dict[str, List[Event]] = defaultdict(list)
        self._lock = threading.RLock()
        self.max_history_per_topic = max_history_per_topic
        self.cleanup_interval = cleanup_interval_seconds
        self._last_cleanup = time.time()
        self._active_workers: Set[str] = set()

    # -------------------------------------------------------------------------
    # Subscription Management
    # -------------------------------------------------------------------------
    def subscribe(self, topic: str, callback: Callable[[Event], Any]) -> None:
        """Subscribes a synchronous or background callback to a topic."""
        with self._lock:
            if callback not in self._subscribers[topic]:
                self._subscribers[topic].append(callback)
                logger.debug(f"[EventBus] Subscribed handler to '{topic}'")

    def subscribe_async(self, topic: str, coro_callback: Callable[[Event], Any]) -> None:
        """Subscribes an asynchronous coroutine callback to a topic."""
        with self._lock:
            if coro_callback not in self._async_subscribers[topic]:
                self._async_subscribers[topic].append(coro_callback)
                logger.debug(f"[EventBus] Subscribed async handler to '{topic}'")

    def unsubscribe(self, topic: str, callback: Callable) -> None:
        """Removes a handler from a topic."""
        with self._lock:
            if callback in self._subscribers.get(topic, []):
                self._subscribers[topic].remove(callback)
            if callback in self._async_subscribers.get(topic, []):
                self._async_subscribers[topic].remove(callback)

    # -------------------------------------------------------------------------
    # Event Publication & Dispatch
    # -------------------------------------------------------------------------
    def publish(self, topic: str, data: Any, ttl_seconds: float = 300.0) -> Event:
        """
        Publishes an event to all subscribers synchronously and enqueues async tasks.
        Includes TTL-based automatic memory eviction to prevent leaks.
        """
        event = Event(topic=topic, data=data, ttl_seconds=ttl_seconds)

        with self._lock:
            # 1. Maintain bounded history
            hist = self._history[topic]
            hist.append(event)
            if len(hist) > self.max_history_per_topic:
                self._history[topic] = hist[-self.max_history_per_topic:]

            # 2. Check periodic TTL memory cleanup
            if time.time() - self._last_cleanup > self.cleanup_interval:
                self._evict_expired_events()

            sync_handlers = list(self._subscribers.get(topic, []))
            wildcard_sync = list(self._subscribers.get("*", []))
            async_handlers = list(self._async_subscribers.get(topic, []))
            wildcard_async = list(self._async_subscribers.get("*", []))

        # 3. Execute synchronous callbacks safely
        for handler in sync_handlers + wildcard_sync:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"[EventBus] Handler error on topic '{topic}': {e}", exc_info=True)

        # 4. Schedule async handlers if loop is running
        if async_handlers or wildcard_async:
            try:
                loop = asyncio.get_running_loop()
                for a_handler in async_handlers + wildcard_async:
                    loop.create_task(self._safe_async_dispatch(a_handler, event))
            except RuntimeError:
                # No running event loop in current thread; dispatch in background thread
                threading.Thread(
                    target=self._dispatch_async_threaded,
                    args=(async_handlers + wildcard_async, event),
                    daemon=True
                ).start()

        return event

    async def _safe_async_dispatch(self, handler: Callable, event: Event) -> None:
        try:
            await handler(event)
        except Exception as e:
            logger.error(f"[EventBus] Async handler error on '{event.topic}': {e}", exc_info=True)

    def _dispatch_async_threaded(self, handlers: List[Callable], event: Event) -> None:
        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)
        try:
            tasks = [self._safe_async_dispatch(h, event) for h in handlers]
            new_loop.run_until_complete(asyncio.gather(*tasks))
        finally:
            new_loop.close()

    # -------------------------------------------------------------------------
    # Asynchronous Worker Pool (Fire-and-Forget Job Delegation)
    # -------------------------------------------------------------------------
    def dispatch_worker_job(self, job_name: str, task_func: Callable, args: tuple = (), kwargs: dict = None) -> str:
        """
        Dispatches a CPU/IO-heavy job to an isolated background thread.
        Broadcasts lifecycle events ('job.started', 'job.completed', 'job.failed') automatically.
        """
        job_id = f"job_{uuid.uuid4().hex[:8]}"
        kwargs = kwargs or {}

        def _worker_wrapper():
            worker_id = f"{job_name}-{job_id}"
            with self._lock:
                self._active_workers.add(worker_id)
            self.publish("worker.job.started", {"job_id": job_id, "name": job_name, "time": time.time()})
            logger.info(f"[EventBus Worker] Starting {job_name} ({job_id})")

            start_t = time.time()
            try:
                result = task_func(*args, **kwargs)
                elapsed = round(time.time() - start_t, 2)
                self.publish("worker.job.completed", {
                    "job_id": job_id,
                    "name": job_name,
                    "elapsed_seconds": elapsed,
                    "result": result
                })
                logger.info(f"[EventBus Worker] Completed {job_name} ({job_id}) in {elapsed}s")
            except Exception as e:
                elapsed = round(time.time() - start_t, 2)
                self.publish("worker.job.failed", {
                    "job_id": job_id,
                    "name": job_name,
                    "elapsed_seconds": elapsed,
                    "error": str(e)
                })
                logger.error(f"[EventBus Worker] Failed {job_name} ({job_id}) after {elapsed}s: {e}", exc_info=True)
            finally:
                with self._lock:
                    self._active_workers.discard(worker_id)

        threading.Thread(target=_worker_wrapper, name=f"EventBusWorker-{job_name}", daemon=True).start()
        return job_id

    # -------------------------------------------------------------------------
    # Memory Leak Prevention & TTL Eviction
    # -------------------------------------------------------------------------
    def _evict_expired_events(self) -> int:
        """Prunes events past their TTL to maintain strict bounded memory usage."""
        now = time.time()
        evicted = 0
        with self._lock:
            for topic in list(self._history.keys()):
                valid_events = [ev for ev in self._history[topic] if ev.expires_at > now]
                evicted += len(self._history[topic]) - len(valid_events)
                self._history[topic] = valid_events
                if not self._history[topic]:
                    del self._history[topic]
            self._last_cleanup = now

        if evicted > 0:
            logger.debug(f"[EventBus] Evicted {evicted} expired events from memory history")
        return evicted

    def get_stats(self) -> Dict[str, Any]:
        """Returns real-time telemetry of active subscribers, queues, and memory footprint."""
        with self._lock:
            return {
                "active_topics": list(self._subscribers.keys()),
                "total_sync_subscribers": sum(len(v) for v in self._subscribers.values()),
                "total_async_subscribers": sum(len(v) for v in self._async_subscribers.values()),
                "history_topics_count": len(self._history),
                "total_buffered_events": sum(len(v) for v in self._history.values()),
                "active_background_workers": list(self._active_workers)
            }


# Singleton Global Instance
event_bus = EventBus()
