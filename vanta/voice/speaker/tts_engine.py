"""
TTS Engine
Converts text to speech using configured TTS provider
"""

import asyncio
import logging
import time
import os
from typing import Dict, Any, Optional, Tuple

from vanta.core.event_bus import bus, EventType
from vanta.core.utils.async_helpers import run_in_executor

logger = logging.getLogger(__name__)

# These will be imported at runtime to avoid unnecessary dependencies
try:
    import numpy as np
    from elevenlabs import generate, set_api_key
    from elevenlabs.api import Voice
    import sounddevice as sd
    import soundfile as sf
except ImportError:
    logger.warning("TTS dependencies not installed - text-to-speech functionality unavailable")


class TTSEngine:
    """
    Text-to-Speech engine that generates speech using the configured provider
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the TTS engine
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.tts_config = config.get("tts", {})
        self.service = self.tts_config.get("service", "elevenlabs")
        self.voice = self.tts_config.get("voice", "default")
        self.rate = self.tts_config.get("rate", 1.0)
        self.pitch = self.tts_config.get("pitch", 0.0)
        self.volume = self.tts_config.get("volume", 1.0)
        
        # For caching audio temporarily
        self.data_dir = config.get("system", {}).get("data_dir", "data")
        self.cache_dir = f"{self.data_dir}/tts_cache"
        os.makedirs(self.cache_dir, exist_ok=True)
        
        logger.info(f"TTS engine initialized with {self.service} service")
    
    async def start(self):
        """Start the TTS engine"""
        logger.info("Starting TTS engine")
        
        # Subscribe to speak text events
        bus.subscribe(EventType.SPEAK_TEXT, self.handle_speak_text)
        
        # Initialize API keys if needed
        if self.service == "elevenlabs":
            api_key = os.environ.get("ELEVENLABS_API_KEY")
            if api_key:
                asyncio.create_task(self._setup_elevenlabs(api_key))
            else:
                logger.warning("ELEVENLABS_API_KEY not found in environment")
    
    async def stop(self):
        """Stop the TTS engine"""
        logger.info("Stopping TTS engine")
    
    @run_in_executor
    def _setup_elevenlabs(self, api_key: str):
        """Set up ElevenLabs API (runs in executor)"""
        try:
            set_api_key(api_key)
            logger.info("ElevenLabs API key set successfully")
        except Exception as e:
            logger.error(f"Error setting up ElevenLabs: {e}")
    
    def handle_speak_text(self, event_data: Dict[str, Any]):
        """
        Handle speak text event
        
        Args:
            event_data: Event data containing text to speak
        """
        text = event_data.get("text", "")
        if not text.strip():
            return
            
        # Generate and play speech
        asyncio.create_task(self.speak(text))
    
    async def speak(self, text: str):
        """
        Convert text to speech and play it
        
        Args:
            text: Text to speak
        """
        start_time = time.time()
        logger.info(f"Converting to speech: '{text}'")
        
        # Indicate that VANTA is speaking
        bus.publish(EventType.SPEECH_COMPLETE, {
            "is_speaking": True,
            "text": text,
            "start_time": start_time
        })
        
        try:
            # Generate audio
            audio_data = await self._generate_speech(text)
            
            if audio_data:
                # Play the audio
                await self._play_audio(audio_data)
                
                # Calculate duration
                end_time = time.time()
                duration = end_time - start_time
                
                # Publish speech complete event
                bus.publish(EventType.SPEECH_COMPLETE, {
                    "text": text,
                    "start_time": start_time,
                    "end_time": end_time,
                    "duration": duration,
                    "is_speaking": False
                })
                
                logger.info(f"Speech complete: '{text}' ({duration:.2f}s)")
            else:
                logger.error("Failed to generate speech audio")
                
        except Exception as e:
            logger.error(f"Error in speech synthesis: {e}")
            # Publish speech complete with error
            bus.publish(EventType.SPEECH_COMPLETE, {
                "text": text,
                "start_time": start_time,
                "end_time": time.time(),
                "error": str(e),
                "is_speaking": False
            })
    
    async def _generate_speech(self, text: str) -> Optional[np.ndarray]:
        """
        Generate speech audio for the text
        
        Args:
            text: Text to convert to speech
            
        Returns:
            Audio data as numpy array, or None if generation failed
        """
        if self.service == "elevenlabs":
            return await self._generate_elevenlabs(text)
        elif self.service == "system":
            return await self._generate_system_tts(text)
        else:
            logger.warning(f"Unsupported TTS service: {self.service}")
            return None
    
    @run_in_executor
    def _generate_elevenlabs(self, text: str) -> Optional[np.ndarray]:
        """
        Generate speech using ElevenLabs API (runs in executor)
        
        Args:
            text: Text to convert to speech
            
        Returns:
            Audio data as numpy array
        """
        try:
            import numpy as np
            from elevenlabs import generate
            from elevenlabs.api import Voice
            import soundfile as sf
            
            # Generate unique filename for caching
            import hashlib
            text_hash = hashlib.md5(text.encode()).hexdigest()
            cache_file = f"{self.cache_dir}/{text_hash}.wav"
            
            # Check if already cached
            if os.path.exists(cache_file):
                logger.debug(f"Using cached audio for '{text}'")
                audio_data, sample_rate = sf.read(cache_file)
                return audio_data
            
            # Generate audio
            voice = Voice(
                voice_id=self.voice if self.voice != "default" else None,
                settings={
                    "stability": 0.5,
                    "similarity_boost": 0.75
                }
            )
            
            audio = generate(
                text=text,
                voice=voice,
                model="eleven_monolingual_v1"
            )
            
            # Save to temporary file
            with open(cache_file, "wb") as f:
                f.write(audio)
            
            # Load as numpy array
            audio_data, sample_rate = sf.read(cache_file)
            return audio_data
            
        except Exception as e:
            logger.error(f"Error generating speech with ElevenLabs: {e}")
            return None
    
    @run_in_executor
    def _generate_system_tts(self, text: str) -> Optional[np.ndarray]:
        """
        Generate speech using system TTS (macOS say command)
        
        Args:
            text: Text to convert to speech
            
        Returns:
            Audio data as numpy array
        """
        try:
            import numpy as np
            import soundfile as sf
            import subprocess
            
            # Generate unique filename for caching
            import hashlib
            text_hash = hashlib.md5(text.encode()).hexdigest()
            cache_file = f"{self.cache_dir}/{text_hash}.wav"
            
            # Check if already cached
            if os.path.exists(cache_file):
                logger.debug(f"Using cached audio for '{text}'")
                audio_data, sample_rate = sf.read(cache_file)
                return audio_data
                
            # Use macOS say command to generate speech
            subprocess.run([
                "say", 
                "-v", self.voice if self.voice != "default" else "Alex",
                "-r", str(int(self.rate * 200)),  # Rate conversion
                "-o", cache_file,
                "--data-format=LEF32@22050",  # Output format
                text
            ])
            
            # Load as numpy array
            audio_data, sample_rate = sf.read(cache_file)
            return audio_data
            
        except Exception as e:
            logger.error(f"Error generating speech with system TTS: {e}")
            return None
    
    @run_in_executor
    def _play_audio(self, audio_data: np.ndarray):
        """
        Play audio data using sounddevice (runs in executor)
        
        Args:
            audio_data: Audio data as numpy array
        """
        try:
            import sounddevice as sd
            
            # Get the sample rate (assume 22050 for ElevenLabs)
            sample_rate = 22050
            
            # Play the audio
            sd.play(audio_data, sample_rate)
            sd.wait()
            
        except Exception as e:
            logger.error(f"Error playing audio: {e}")