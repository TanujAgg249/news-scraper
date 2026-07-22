"""
Server-Sent Events (SSE) progress manager for topic scraping.
"""
import asyncio
from typing import Dict, List

class ScrapeProgressManager:
    def __init__(self):
        self.queues: Dict[str, List[asyncio.Queue]] = {}

    def add_listener(self, topic_id: str) -> asyncio.Queue:
        """Add a new listener for a specific topic scrape."""
        if topic_id not in self.queues:
            self.queues[topic_id] = []
        q = asyncio.Queue()
        self.queues[topic_id].append(q)
        return q

    def remove_listener(self, topic_id: str, q: asyncio.Queue):
        """Remove a listener."""
        if topic_id in self.queues and q in self.queues[topic_id]:
            self.queues[topic_id].remove(q)
            if not self.queues[topic_id]:
                del self.queues[topic_id]

    async def broadcast(self, topic_id: str, message: str):
        """Broadcast a message asynchronously to all listeners of a topic."""
        if topic_id in self.queues:
            for q in self.queues[topic_id]:
                await q.put(message)

    def broadcast_sync(self, topic_id: str, message: str):
        """Broadcast a message synchronously (used inside background threads/tasks)."""
        if topic_id in self.queues:
            for q in self.queues[topic_id]:
                try:
                    q.put_nowait(message)
                except asyncio.QueueFull:
                    pass

progress_manager = ScrapeProgressManager()
