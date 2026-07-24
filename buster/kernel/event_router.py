"""
Buster Kernel - High-Performance Topic Trie Event Router & Message Broker

Provides hierarchical pattern matching (* and #) via Trie structures,
asynchronous multi-threaded dispatching, and thread-safe Dead-Letter Queue (DLQ) error isolation.
"""

from __future__ import annotations

import logging
import queue
import re
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import IntEnum
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger("BusterKernel.EventRouter")


class EventPriority(IntEnum):
    CRITICAL = 0   # Safety stops, critical hardware alerts
    HIGH = 10       # User commands, transactional events
    NORMAL = 20     # Standard agent IPC messaging
    LOW = 30        # System telemetry, metrics, background logs


@dataclass(order=True)
class KernelEvent:
    """Standardized event envelope across the Buster Agent OS."""
    priority: EventPriority = field(compare=True)
    topic: str = field(compare=False)
    payload: Dict[str, Any] = field(compare=False)
    source: str = field(compare=False)
    event_id: str = field(
        default_factory=lambda: f"EVT-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')[:17]}",
        compare=False
    )
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        compare=False
    )


@dataclass
class Subscription:
    pattern: str
    callback: Callable[[KernelEvent], None]
    subscriber_id: str

    def __hash__(self) -> int:
        return hash((self.pattern, self.subscriber_id))


class TrieNode:
    """Node structure for topic hierarchy prefix tree."""
    def __init__(self) -> None:
        self.children: Dict[str, TrieNode] = {}
        self.subscriptions: Set[Subscription] = set()


class EventRouter:
    """High-Performance, Multi-Threaded Hierarchical Message Broker for Buster AI OS."""

    def __init__(self, max_workers: int = 8, audit_service: Optional[Any] = None) -> None:
        self._trie_root = TrieNode()
        self._dead_letter_queue: queue.Queue[Dict[str, Any]] = queue.Queue()
        self.audit_service = audit_service
        self._lock = threading.RLock()
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers, 
            thread_name_prefix="BusterAgentWorker"
        )
        logger.info(f"Buster Kernel Event Router initialized. Worker Pool: {max_workers} threads.")

    def subscribe(self, pattern: str, callback: Callable[[KernelEvent], None], subscriber_id: str = "anonymous") -> Subscription:
        """Subscribes to an event pattern using Trie insertion."""
        sub = Subscription(pattern=pattern, callback=callback, subscriber_id=subscriber_id)
        tokens = pattern.split(".")

        with self._lock:
            current = self._trie_root
            for token in tokens:
                if token not in current.children:
                    current.children[token] = TrieNode()
                current = current.children[token]
            current.subscriptions.add(sub)

        logger.info(f"Subscriber '{subscriber_id}' registered for topic pattern: '{pattern}'")
        return sub

    def unsubscribe(self, subscriber_id: str, pattern: Optional[str] = None) -> None:
        """Removes subscriptions cleanly from the Trie structure."""
        with self._lock:
            if pattern:
                self._remove_pattern(self._trie_root, pattern.split("."), 0, subscriber_id)
            else:
                self._recursive_remove_subscriber(self._trie_root, subscriber_id)

    def _remove_pattern(self, node: TrieNode, tokens: List[str], index: int, subscriber_id: str) -> bool:
        if index == len(tokens):
            node.subscriptions = {s for s in node.subscriptions if s.subscriber_id != subscriber_id}
            return len(node.subscriptions) == 0 and len(node.children) == 0

        token = tokens[index]
        if token in node.children:
            should_delete = self._remove_pattern(node.children[token], tokens, index + 1, subscriber_id)
            if should_delete:
                del node.children[token]
        return len(node.subscriptions) == 0 and len(node.children) == 0

    def _recursive_remove_subscriber(self, node: TrieNode, subscriber_id: str) -> None:
        node.subscriptions = {s for s in node.subscriptions if s.subscriber_id != subscriber_id}
        for child in node.children.values():
            self._recursive_remove_subscriber(child, subscriber_id)

    def publish(
        self, 
        topic: str, 
        payload: Dict[str, Any], 
        source: str = "kernel", 
        priority: EventPriority = EventPriority.NORMAL
    ) -> KernelEvent:
        """Publishes an event asynchronously with instant Trie pattern matching."""
        event = KernelEvent(topic=topic, payload=payload, source=source, priority=priority)
        tokens = topic.split(".")
        matched_subs: Set[Subscription] = set()

        with self._lock:
            self._match_trie(self._trie_root, tokens, 0, matched_subs)

        if not matched_subs:
            logger.debug(f"Unrouted event published on topic '{topic}' (0 matches)")
            return event

        if self.audit_service and hasattr(self.audit_service, "log_event"):
            self._executor.submit(self.audit_service.log_event, event)

        for sub in matched_subs:
            self._executor.submit(self._dispatch_safely, sub, event)

        return event

    def _match_trie(self, node: TrieNode, tokens: List[str], index: int, result: Set[Subscription]) -> None:
        """Recursive Trie pattern matching engine handling wildcards '*' and '#'."""
        if "#" in node.children:
            result.update(node.children["#"].subscriptions)

        if index == len(tokens):
            result.update(node.subscriptions)
            return

        token = tokens[index]

        if token in node.children:
            self._match_trie(node.children[token], tokens, index + 1, result)

        if "*" in node.children:
            self._match_trie(node.children["*"], tokens, index + 1, result)

    def _dispatch_safely(self, sub: Subscription, event: KernelEvent) -> None:
        """Executes subscriber callback on an isolated pool thread to protect core kernel loop."""
        try:
            sub.callback(event)
        except Exception as exc:
            logger.error(f"Execution crash in subscriber '{sub.subscriber_id}' on topic '{event.topic}': {exc}")
            self._dead_letter_queue.put({
                "event": event,
                "subscriber_id": sub.subscriber_id,
                "error": str(exc),
                "failed_at": datetime.now(timezone.utc).isoformat()
            })

    def get_dlq(self) -> List[Dict[str, Any]]:
        """Thread-safe retrieval of dead-letter logs."""
        res = []
        while not self._dead_letter_queue.empty():
            try:
                res.append(self._dead_letter_queue.get_nowait())
            except queue.Empty:
                break
        return res

    def shutdown(self) -> None:
        """Cleanly drains worker thread pool."""
        logger.info("Shutting down Buster Kernel Event Router worker threads...")
        self._executor.shutdown(wait=True)