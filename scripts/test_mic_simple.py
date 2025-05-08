#!/usr/bin/env python3
"""
Simple microphone test script to diagnose audio capture issues.
Displays real-time audio levels and VAD detection status without GUI elements.
"""

import numpy as np
import pyaudio
import time
import argparse
import webrtcvad
import sys

# Constants
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000  # Must be 8000, 16000, 32000 or 48000 for WebRTC VAD
CHUNK = 480  # Must be 10, 20, or 30ms for WebRTC VAD (480 samples = 30ms at 16kHz)
HISTOGRAM_SIZE = 20  # Bins for ASCII histogram

class SimpleMicrophoneTest:
    def __init__(self, vad_mode=3, threshold=0.003):
        self.p = pyaudio.PyAudio()
        self.vad = webrtcvad.Vad()
        self.vad.set_mode(vad_mode)  # 0-3, where 3 is the most aggressive
        self.vad_mode = vad_mode
        self.threshold = threshold
        self.stream = None
        self.running = False
        
        # Stats tracking
        self.max_level = 0
        self.min_level = 1.0
        self.levels_history = []
        self.speech_detected_count = 0
        self.total_frames = 0
        self.start_time = None
        
    def start(self):
        """Start capturing audio from microphone"""
        self.stream = self.p.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            frames_per_buffer=CHUNK
        )
        self.running = True
        self.start_time = time.time()
        
        # Process audio in main thread
        try:
            print(f"Listening to microphone... (Press Ctrl+C to stop)")
            print(f"Using VAD mode: {self.vad_mode}, Amplitude threshold: {self.threshold}")
            print(f"{'Level':^10}|{'VOL':^20}|{'Status':^10}|{'VAD':^5}|{'THRESH':^7}")
            print("-" * 55)
            
            while self.running:
                self.process_audio()
                time.sleep(0.01)  # Small delay to prevent CPU overuse
        except KeyboardInterrupt:
            print("\nStopping...")
            self.print_stats()
        finally:
            self.stop()
    
    def process_audio(self):
        """Process one chunk of audio data"""
        audio_bytes = self.stream.read(CHUNK, exception_on_overflow=False)
        audio_array = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32)
        
        # Normalize to [-1.0, 1.0]
        audio_array = audio_array / 32768.0
        
        # Calculate RMS amplitude
        level = np.sqrt(np.mean(np.square(audio_array)))
        self.levels_history.append(level)
        
        # Track min/max
        self.max_level = max(self.max_level, level)
        self.min_level = min(self.min_level, level) if level > 0 else self.min_level
        
        # Keep only recent history
        if len(self.levels_history) > 100:
            self.levels_history.pop(0)
        
        # Check if VAD detects speech
        try:
            vad_speech = self.vad.is_speech(audio_bytes, RATE)
        except Exception as e:
            vad_speech = False
            
        # Also detect based on simple threshold
        threshold_speech = level > self.threshold
        
        # Combined detection (either method)
        combined_speech = vad_speech or threshold_speech
        
        if combined_speech:
            self.speech_detected_count += 1
        
        self.total_frames += 1
        
        # Print current level and detection status with ASCII visualization
        speech_status = "SPEECH" if combined_speech else "silence"
        vad_status = "+" if vad_speech else "-"
        thresh_status = "+" if threshold_speech else "-"
        
        # Create simple ASCII volume meter
        meter_len = 20
        filled = int(min(level / 0.1, 1.0) * meter_len)
        meter = "█" * filled + "░" * (meter_len - filled)
        
        print(f"\r{level:.6f} |{meter}| {speech_status:^8} | {vad_status:^3} | {thresh_status:^5}", end="")
    
    def print_stats(self):
        """Print statistics about the audio capture session"""
        duration = time.time() - self.start_time
        
        print("\n\n===== Microphone Test Statistics =====")
        print(f"Duration: {duration:.2f} seconds")
        print(f"Frames processed: {self.total_frames}")
        print(f"Minimum level: {self.min_level:.6f}")
        print(f"Maximum level: {self.max_level:.6f}")
        print(f"Average level: {np.mean(self.levels_history):.6f}")
        
        # Speech detection stats
        speech_percentage = (self.speech_detected_count / max(1, self.total_frames)) * 100
        print(f"Speech detected: {self.speech_detected_count} frames ({speech_percentage:.2f}%)")
        
        # Recommendations based on levels
        print("\n===== Analysis =====")
        if self.max_level < 0.01:
            print("ISSUE: Audio levels are VERY LOW. Check microphone connection and system input settings.")
        elif self.max_level < 0.05:
            print("ISSUE: Audio levels are LOW. Consider increasing microphone input gain in system settings.")
        
        # Threshold recommendations
        recommended_threshold = self.max_level * 0.3
        print(f"Recommended threshold setting: {recommended_threshold:.6f} (30% of max observed level)")
        
        print("\n===== Recommendations =====")
        if self.max_level < 0.01:
            print("1. Check if microphone is properly connected")
            print("2. Check system sound settings to ensure correct input device is selected")
            print("3. Increase input volume/gain in system sound settings")
        elif speech_percentage < 10 and self.max_level > 0.01:
            print(f"1. Try running with --threshold {recommended_threshold:.6f}")
            print(f"2. Try running with --vad-mode 1 (less aggressive)")
            print("3. Speak louder or move closer to microphone")
    
    def stop(self):
        """Stop capturing and release resources"""
        self.running = False
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        self.p.terminate()

def main():
    parser = argparse.ArgumentParser(description="Test microphone input levels and VAD detection")
    parser.add_argument("--vad-mode", type=int, choices=[0, 1, 2, 3], default=3,
                        help="WebRTC VAD aggressiveness (0=least, 3=most)")
    parser.add_argument("--threshold", type=float, default=0.003,
                        help="Amplitude threshold for speech detection")
    
    args = parser.parse_args()
    
    try:
        test = SimpleMicrophoneTest(vad_mode=args.vad_mode, threshold=args.threshold)
        test.start()
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())