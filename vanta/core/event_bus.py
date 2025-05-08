"""
Event Bus
Central communication mechanism for VANTA components
"""

import logging
import asyncio
from typing import Dict, List, Callable, Any, Coroutine, Optional, Set
from enum import Enum, auto

logger = logging.getLogger(__name__)


class EventType(Enum):
    """Core event types for the VANTA system"""
    # Voice events
    AUDIO_CAPTURED = auto()
    SPEECH_DETECTED = auto()
    TRANSCRIPTION_COMPLETE = auto()
    
    # Reasoning events
    TRANSCRIPTION_PROCESSED = auto()
    RESPONSE_READY = auto()
    SHOULD_RESPOND = auto()
    
    # Speech output events
    SPEAK_TEXT = auto()
    SPEECH_COMPLETE = auto()
    
    # Memory events
    CONVERSATION_STORED = auto()
    MEMORY_RETRIEVED = auto()
    
    # System events
    SYSTEM_STARTUP = auto()
    SYSTEM_SHUTDOWN = auto()
    ERROR = auto()
    
    # Personality events
    MOOD_UPDATED = auto()
    
    # Scheduler events
    SCHEDULED_EVENT = auto()


class EventBus:
    """
    Central event pub/sub system to handle communication between components
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EventBus, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """Initialize the event bus"""
        self._subscribers: Dict[EventType, List[Callable]] = {}
        self._event_queue = asyncio.Queue()
        self._running = False
        self._processing_task = None
        self._loop = None
        self._active_subscribers: Set[int] = set()
    
    async def start(self):
        """Start the event processing loop"""
        if self._running:
            return
        
        self._running = True
        self._loop = asyncio.get_running_loop()
        self._processing_task = asyncio.create_task(self._process_events())
        logger.info("Event bus started")
    
    async def stop(self):
        """Stop the event processing loop"""
        if not self._running:
            return
        
        self._running = False
        if self._processing_task:
            self._processing_task.cancel()
            try:
                await self._processing_task
            except asyncio.CancelledError:
                pass
            self._processing_task = None
        logger.info("Event bus stopped")
    
    def subscribe(self, event_type: EventType, callback: Callable) -> int:
        """
        Subscribe to an event type
        
        Args:
            event_type: The event type to subscribe to
            callback: Function to call when event occurs
            
        Returns:
            Subscriber ID for unsubscribing
        """
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        
        self._subscribers[event_type].append(callback)
        subscriber_id = id(callback)
        self._active_subscribers.add(subscriber_id)
        logger.debug(f"Subscribed to {event_type.name}, total subscribers: {len(self._subscribers[event_type])}")
        return subscriber_id
    
    def unsubscribe(self, event_type: EventType, subscriber_id: int) -> bool:
        """
        Unsubscribe from an event type
        
        Args:
            event_type: The event type to unsubscribe from
            subscriber_id: ID returned from subscribe()
            
        Returns:
            True if successfully unsubscribed
        """
        if event_type not in self._subscribers:
            return False
        
        for i, callback in enumerate(self._subscribers[event_type]):
            if id(callback) == subscriber_id:
                self._subscribers[event_type].pop(i)
                self._active_subscribers.discard(subscriber_id)
                logger.debug(f"Unsubscribed from {event_type.name}")
                return True
        
        return False
    
    def publish(self, event_type: EventType, data: Any = None):
        """
        Publish an event to the bus
        
        Args:
            event_type: Type of event to publish
            data: Data payload for the event
        """
        # Handle calls from other threads by using call_soon_threadsafe
        if self._loop and self._loop.is_running():
            try:
                # For callbacks from other threads, use call_soon_threadsafe
                import threading
                if threading.current_thread() is not threading.main_thread():
                    self._loop.call_soon_threadsafe(
                        lambda: asyncio.create_task(self._publish_async(event_type, data))
                    )
                    logger.debug(f"Published event {event_type.name} from background thread")
                else:
                    # Normal case for the main thread
                    asyncio.create_task(self._publish_async(event_type, data))
                    logger.debug(f"Published event {event_type.name}")
            except Exception as e:
                logger.error(f"Error publishing event {event_type.name}: {e}")
        else:
            logger.warning(f"Event loop not running, cannot publish {event_type.name}")
    
    async def publish_async(self, event_type: EventType, data: Any = None):
        """
        Publish an event to the bus (async version)
        
        Args:
            event_type: Type of event to publish
            data: Data payload for the event
        """
        await self._publish_async(event_type, data)
    
    async def _publish_async(self, event_type: EventType, data: Any = None):
        """Internal async publish implementation"""
        await self._event_queue.put((event_type, data))
        logger.debug(f"Published event {event_type.name}")
    
    async def _process_events(self):
        """Process events from the queue"""
        logger.debug("Event processing started")
        while self._running:
            try:
                event_type, data = await self._event_queue.get()
                await self._handle_event(event_type, data)
                self._event_queue.task_done()
            except asyncio.CancelledError:
                logger.debug("Event processing cancelled")
                break
            except Exception as e:
                logger.error(f"Error processing event: {e}")
        
        logger.debug("Event processing stopped")
    
    async def _handle_event(self, event_type: EventType, data: Any):
        """Handle a single event by calling all subscribers"""
        if event_type not in self._subscribers:
            return
        
        for callback in list(self._subscribers[event_type]):
            try:
                result = callback(data)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                logger.error(f"Error in event handler for {event_type.name}: {e}")


# Singleton instance
bus = EventBus()