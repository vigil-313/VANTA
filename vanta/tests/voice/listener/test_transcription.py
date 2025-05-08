"""
Tests for the transcription components

These tests validate the operation of the transcription architecture components.
"""

import asyncio
import json
import os
import signal
import subprocess
import sys
import time
import unittest
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from vanta.voice.listener.basic_stt import simple_transcription, detect_speech_content
from vanta.voice.listener.transcription_manager import TranscriptionManager
from vanta.voice.listener.whisper_process import WhisperProcess


class TestBasicSTT(unittest.TestCase):
    """Tests for the basic STT module"""
    
    def test_detect_speech_content(self):
        """Test speech content detection"""
        # Create silent audio
        silent_audio = np.zeros(16000, dtype=np.float32)
        self.assertFalse(detect_speech_content(silent_audio))
        
        # Create audio with some content
        speech_audio = np.zeros(16000, dtype=np.float32)
        speech_audio[4000:8000] = np.sin(np.linspace(0, 20*np.pi, 4000)) * 0.5
        self.assertTrue(detect_speech_content(speech_audio))
    
    def test_simple_transcription(self):
        """Test simple transcription function"""
        # Test with silent audio
        silent_audio = np.zeros(16000, dtype=np.float32)
        self.assertEqual(simple_transcription(silent_audio), "")
        
        # Test with short speech
        short_audio = np.zeros(8000, dtype=np.float32)  # 0.5 seconds
        short_audio[2000:6000] = np.sin(np.linspace(0, 20*np.pi, 4000)) * 0.5
        self.assertEqual(simple_transcription(short_audio), "...")
        
        # Test with medium speech
        med_audio = np.zeros(24000, dtype=np.float32)  # 1.5 seconds
        med_audio[4000:20000] = np.sin(np.linspace(0, 100*np.pi, 16000)) * 0.5
        result = simple_transcription(med_audio)
        self.assertTrue(result in ["... sentence ...", "... short phrase ..."])
        
        # Test with longer speech
        long_audio = np.zeros(48000, dtype=np.float32)  # 3 seconds
        long_audio[8000:40000] = np.sin(np.linspace(0, 200*np.pi, 32000)) * 0.5
        self.assertEqual(simple_transcription(long_audio), "... longer speech ...")


@pytest.mark.asyncio
class TestWhisperProcess:
    """Tests for the Whisper Process module"""
    
    @pytest.mark.skipif(not os.path.exists(os.path.join(os.path.dirname(__file__), 
                                                        "../../../voice/listener/whisper_worker.py")),
                        reason="Whisper worker script not found")
    async def test_whisper_process_creation(self):
        """Test creating and stopping a WhisperProcess"""
        # This test verifies that the process can be created and stopped without errors
        # It does not actually perform transcription to avoid requiring Whisper
        
        with patch('subprocess.Popen') as mock_popen:
            # Mock the process
            mock_process = MagicMock()
            mock_process.pid = 12345
            mock_process.poll.return_value = None
            mock_popen.return_value = mock_process
            
            # Create the WhisperProcess
            wp = WhisperProcess(model_name="tiny", language="en")
            
            # Verify the process was started
            assert wp.is_running
            assert wp.process is not None
            
            # Stop the process
            wp.shutdown()
            
            # Verify process was terminated
            mock_process.terminate.assert_called_once()
    
    @patch('vanta.voice.listener.whisper_process.WhisperProcess.transcribe')
    async def test_transcription_timeout(self, mock_transcribe):
        """Test that transcription timeouts are handled properly"""
        # Setup mock to timeout
        mock_transcribe.side_effect = asyncio.TimeoutError("Timeout")
        
        # Create the process
        wp = WhisperProcess(model_name="tiny", language="en")
        
        # Create dummy audio
        audio = np.zeros(16000, dtype=np.float32)
        
        # Call transcribe
        text, metadata = wp.transcribe(audio, timeout=1.0)
        
        # Verify the result
        assert text == ""
        assert "error" in metadata
        assert "timeout" in metadata["error"].lower()


@pytest.mark.asyncio
class TestTranscriptionManager:
    """Tests for the Transcription Manager module"""
    
    @patch('vanta.voice.listener.transcription_manager.WhisperProcess')
    async def test_transcription_manager_init(self, mock_wp_class):
        """Test TranscriptionManager initialization"""
        # Create config
        config = {
            "stt": {
                "service": "whisper",
                "model": "tiny",
                "language": "en",
                "max_failures": 3
            },
            "microphone": {
                "sample_rate": 16000
            }
        }
        
        # Create the manager
        tm = TranscriptionManager(config)
        
        # Start the manager
        await tm.start()
        
        # Verify the WhisperProcess was created
        mock_wp_class.assert_called_once_with(model_name="tiny", language="en")
    
    @patch('vanta.voice.listener.transcription_manager.WhisperProcess')
    async def test_transcription_fallback(self, mock_wp_class):
        """Test fallback behavior when WhisperProcess fails"""
        # Setup mock to fail
        mock_wp = MagicMock()
        mock_wp.transcribe.return_value = ("", {"error": "Mock error"})
        mock_wp_class.return_value = mock_wp
        
        # Create config
        config = {
            "stt": {
                "service": "whisper",
                "model": "tiny",
                "language": "en",
                "max_failures": 2
            },
            "microphone": {
                "sample_rate": 16000
            }
        }
        
        # Create the manager
        tm = TranscriptionManager(config)
        await tm.start()
        
        # Create test audio
        audio = np.zeros(16000, dtype=np.float32)
        audio[4000:12000] = np.sin(np.linspace(0, 100*np.pi, 8000)) * 0.5
        
        # First transcription should try Whisper, then fall back
        text, metadata = await tm.transcribe(audio, 0.0, 1.0)
        
        # Verify Whisper was called
        mock_wp.transcribe.assert_called_once()
        
        # Verify failures were counted
        assert tm.failures == 1
        
        # Second transcription should repeat the process
        text2, metadata2 = await tm.transcribe(audio, 0.0, 1.0)
        
        # Verify we've now hit max failures
        assert tm.failures == 2
        
        # Third transcription should go straight to fallback
        text3, metadata3 = await tm.transcribe(audio, 0.0, 1.0)
        
        # Verify we're now in fallback mode
        assert tm.in_fallback_mode is True


if __name__ == "__main__":
    unittest.main()