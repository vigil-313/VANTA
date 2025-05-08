"""
Response Generator
Generates text responses based on conversation context
"""

import logging
import time
from typing import Dict, Any, List, Optional

from vanta.core.event_bus import bus, EventType

logger = logging.getLogger(__name__)


class ResponseGenerator:
    """
    Generates text responses to user speech
    (will be expanded with LLM integration in the future)
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the response generator
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        
        # For now, we'll use a simple template-based approach
        # This will be replaced with LLM integration
        self.templates = {
            "greeting": [
                "Hello there!",
                "Hi! How can I help you?",
                "Hey, I'm listening.",
                "Good to hear from you."
            ],
            "question": [
                "I'm still learning how to answer questions properly.",
                "That's an interesting question.",
                "Let me think about that.",
                "I wish I could give you a better answer right now."
            ],
            "default": [
                "I heard you.",
                "I'm listening.",
                "I understand.",
                "Interesting.",
                "I see.",
                "Tell me more."
            ]
        }
        
        logger.info("Response generator initialized with template approach")
    
    async def start(self):
        """Start the response generator"""
        logger.info("Starting response generator")
        
        # Subscribe to should respond events
        bus.subscribe(EventType.SHOULD_RESPOND, self.handle_should_respond)
    
    async def stop(self):
        """Stop the response generator"""
        logger.info("Stopping response generator")
    
    def handle_should_respond(self, event_data: Dict[str, Any]):
        """
        Handle should respond events
        
        Args:
            event_data: Event data containing context for response
        """
        context = event_data.get("context", [])
        transcription = event_data.get("transcription", {})
        
        if not context or not transcription:
            return
            
        # Generate a response
        response = self.generate_response(transcription, context)
        
        if response:
            # Publish speak text event
            bus.publish(EventType.SPEAK_TEXT, {
                "text": response,
                "context": context,
                "timestamp": time.time()
            })
            logger.info(f"Generated response: {response}")
    
    def generate_response(
        self, 
        transcription: Dict[str, Any], 
        context: List[Dict[str, Any]]
    ) -> str:
        """
        Generate a response based on transcription and context
        
        This is a simple template-based implementation that will
        be replaced with LLM integration in the future
        
        Args:
            transcription: The most recent user transcription
            context: List of conversation context entries
            
        Returns:
            Generated response text
        """
        import random
        
        text = transcription.get("text", "").lower()
        
        # Determine response category
        category = "default"
        
        # Check for questions
        question_indicators = ["?", "what", "how", "why", "when", "where", "who", "which", "can you", "could you"]
        if any(indicator in text for indicator in question_indicators):
            category = "question"
        
        # Check for greetings
        greetings = ["hello", "hi", "hey", "greetings", "good morning", "good afternoon", "good evening"]
        if any(greeting in text for greeting in greetings):
            category = "greeting"
        
        # Select a random response from the appropriate template category
        templates = self.templates.get(category, self.templates["default"])
        response = random.choice(templates)
        
        return response