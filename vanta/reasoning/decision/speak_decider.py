"""
Speak Decider
Determines whether VANTA should respond to a given conversation context
"""

import logging
import time
import random
from typing import Dict, Any, List, Optional

from vanta.core.event_bus import bus, EventType

logger = logging.getLogger(__name__)


class SpeakDecider:
    """
    Decides whether VANTA should respond to user speech
    based on context and configuration
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the speak decider
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.speak_config = config.get("speak_decision", {})
        
        # Decision thresholds
        self.base_threshold = self.speak_config.get("base_threshold", 0.6)
        self.interrupt_penalty = self.speak_config.get("interrupt_penalty", 0.3)
        self.recency_penalty = self.speak_config.get("recency_penalty", 0.1)
        
        # Track when VANTA last spoke
        self.last_response_time = 0.0
        self.last_user_speech_time = 0.0
        self.is_speaking = False
        
        logger.info(f"Speak decider initialized with threshold {self.base_threshold}")
    
    async def start(self):
        """Start the speak decider"""
        logger.info("Starting speak decider")
        
        # Subscribe to relevant events
        bus.subscribe(EventType.TRANSCRIPTION_PROCESSED, self.handle_transcription)
        bus.subscribe(EventType.SPEECH_COMPLETE, self.handle_speech_complete)
    
    async def stop(self):
        """Stop the speak decider"""
        logger.info("Stopping speak decider")
    
    def handle_transcription(self, event_data: Dict[str, Any]):
        """
        Handle processed transcription and decide whether to respond
        
        Args:
            event_data: Event data containing transcription and context
        """
        # Extract data
        transcription = event_data.get("transcription", {})
        context = event_data.get("buffer", [])
        
        if not transcription or not context:
            return
            
        # Update last user speech time
        self.last_user_speech_time = transcription.get("end_time", time.time())
        
        # Decide whether to respond
        should_speak, confidence = self.should_respond(context)
        
        if should_speak:
            # Publish event to trigger response generation
            bus.publish(EventType.SHOULD_RESPOND, {
                "transcription": transcription,
                "context": context,
                "confidence": confidence,
                "timestamp": time.time()
            })
            logger.info(f"Decided to respond (confidence: {confidence:.2f})")
        else:
            logger.debug(f"Decided not to respond (confidence: {confidence:.2f})")
    
    def handle_speech_complete(self, event_data: Dict[str, Any]):
        """
        Handle system speech completion
        
        Args:
            event_data: Event data containing speech details
        """
        self.is_speaking = False
        self.last_response_time = time.time()
    
    def should_respond(self, context: List[Dict[str, Any]]) -> tuple[bool, float]:
        """
        Determine whether VANTA should respond to the current context
        
        Args:
            context: List of transcript entries
            
        Returns:
            Tuple of (should_respond, confidence)
        """
        # In this initial implementation, we'll use a simple heuristic approach
        # This will be enhanced with LLM-based decision making in the future
        
        # Start with the base threshold probability
        probability = self.base_threshold
        
        # Apply penalties and adjustments
        
        # 1. If VANTA is currently speaking, apply interrupt penalty
        if self.is_speaking:
            probability -= self.interrupt_penalty
            logger.debug(f"Applied interrupt penalty: -{self.interrupt_penalty}")
        
        # 2. If VANTA spoke recently, apply recency penalty
        time_since_last_response = time.time() - self.last_response_time
        if time_since_last_response < 5.0:  # 5 seconds threshold
            recency_factor = 1.0 - (time_since_last_response / 5.0)
            recency_adjustment = self.recency_penalty * recency_factor
            probability -= recency_adjustment
            logger.debug(f"Applied recency penalty: -{recency_adjustment:.2f}")
        
        # 3. Consider the content of recent messages (simplified version)
        # Look for indicators like questions
        question_indicators = ["?", "what", "how", "why", "when", "where", "who", "which", "can you", "could you"]
        
        # Get the most recent user message
        most_recent_user = None
        for entry in reversed(context):
            if entry.get("is_user", False):
                most_recent_user = entry
                break
        
        if most_recent_user:
            text = most_recent_user.get("text", "").lower()
            
            # Check for question indicators
            if any(indicator in text for indicator in question_indicators):
                probability += 0.2  # Boost probability for questions
                logger.debug("Question detected, boosting probability by 0.2")
            
            # Check for greeting indicators
            greetings = ["hello", "hi", "hey", "greetings", "good morning", "good afternoon", "good evening"]
            if any(greeting in text for greeting in greetings):
                probability += 0.2  # Boost probability for greetings
                logger.debug("Greeting detected, boosting probability by 0.2")
        
        # 4. Add slight randomness (±0.05)
        probability += (random.random() - 0.5) * 0.1
        
        # Ensure probability is within bounds
        probability = max(0.0, min(1.0, probability))
        
        # Decide based on probability threshold
        should_speak = probability > self.base_threshold
        
        return should_speak, probability