#!/usr/bin/env python3
"""
Simple microphone test script to diagnose audio capture issues.
Displays real-time audio levels and VAD detection status.
"""

import numpy as np
import pyaudio
import time
import argparse
from matplotlib import pyplot as plt
import webrtcvad
import threading
import sys

# Constants
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000  # Must be 8000, 16000, 32000 or 48000 for WebRTC VAD
CHUNK = 480  # Must be 10, 20, or 30ms for WebRTC VAD (480 samples = 30ms at 16kHz)
DISPLAY_TIME = 5  # seconds of history to display

class MicrophoneTest:
    def __init__(self, vad_mode=3, threshold=0.003):
        self.p = pyaudio.PyAudio()
        self.vad = webrtcvad.Vad(vad_mode)  # 0-3, where 3 is the most aggressive
        self.threshold = threshold
        self.stream = None
        self.levels = []
        self.is_speech = []
        self.timestamps = []
        self.running = False
        self.lock = threading.Lock()
        
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
        
        # Start plot in a separate thread
        self.plot_thread = threading.Thread(target=self.update_plot)
        self.plot_thread.daemon = True
        self.plot_thread.start()
        
        # Process audio in main thread
        try:
            print("Listening to microphone... (Press Ctrl+C to stop)")
            print(f"Using VAD mode: {self.vad.get_mode()}, Amplitude threshold: {self.threshold}")
            
            while self.running:
                self.process_audio()
        except KeyboardInterrupt:
            print("\nStopping...")
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
        
        # Check if VAD detects speech
        try:
            vad_speech = self.vad.is_speech(audio_bytes, RATE)
        except:
            vad_speech = False
            
        # Also detect based on simple threshold
        threshold_speech = level > self.threshold
        
        # Combined detection (either method)
        combined_speech = vad_speech or threshold_speech
        
        with self.lock:
            now = time.time()
            self.timestamps.append(now)
            self.levels.append(level)
            self.is_speech.append(combined_speech)
            
            # Keep only the most recent history
            cutoff_time = now - DISPLAY_TIME
            while self.timestamps and self.timestamps[0] < cutoff_time:
                self.timestamps.pop(0)
                self.levels.pop(0)
                self.is_speech.pop(0)
        
        # Print current level and detection status
        speech_status = "SPEECH" if combined_speech else "silence"
        vad_status = "VAD+" if vad_speech else "VAD-"
        thresh_status = "THRESH+" if threshold_speech else "THRESH-"
        print(f"\rLevel: {level:.6f} | Status: {speech_status} | {vad_status} {thresh_status}        ", end="")
        
    def update_plot(self):
        """Update the plot with audio levels and speech detection"""
        plt.ion()  # Enable interactive mode
        fig, ax = plt.subplots(figsize=(10, 6))
        
        level_line, = ax.plot([], [], 'b-', label='Audio Level')
        threshold_line, = ax.plot([], [], 'r--', label=f'Threshold ({self.threshold})')
        speech_scatter = ax.scatter([], [], c='green', marker='o', alpha=0.5, label='Speech Detected')
        
        ax.set_ylim(0, 0.1)  # Start with a reasonable range
        ax.set_title('Microphone Audio Levels')
        ax.set_xlabel('Time (s)')
        ax.set_ylabel('Amplitude (normalized)')
        ax.grid(True)
        ax.legend()
        
        while self.running:
            with self.lock:
                if not self.timestamps:
                    plt.pause(0.1)
                    continue
                    
                # Calculate time relative to start
                if len(self.timestamps) > 1:
                    rel_times = [t - self.timestamps[0] for t in self.timestamps]
                    
                    # Update level line
                    level_line.set_data(rel_times, self.levels)
                    
                    # Update threshold line
                    threshold_line.set_data([rel_times[0], rel_times[-1]], 
                                            [self.threshold, self.threshold])
                    
                    # Update speech detection points
                    speech_indices = [i for i, is_speech in enumerate(self.is_speech) if is_speech]
                    if speech_indices:
                        speech_times = [rel_times[i] for i in speech_indices]
                        speech_levels = [self.levels[i] for i in speech_indices]
                        speech_scatter.set_offsets(list(zip(speech_times, speech_levels)))
                    else:
                        speech_scatter.set_offsets([])
                    
                    # Adjust y-axis if needed
                    max_level = max(self.levels) if self.levels else 0.1
                    if max_level > ax.get_ylim()[1] * 0.8:
                        ax.set_ylim(0, max_level * 1.5)
                    
                    # Adjust x-axis to show the time window
                    ax.set_xlim(rel_times[0], max(rel_times[-1], DISPLAY_TIME))
            
            # Update plot
            fig.canvas.draw_idle()
            fig.canvas.flush_events()
            plt.pause(0.1)
    
    def stop(self):
        """Stop capturing and release resources"""
        self.running = False
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        if hasattr(self, 'plot_thread') and self.plot_thread.is_alive():
            self.plot_thread.join(timeout=1.0)
        self.p.terminate()
        plt.close('all')

def main():
    parser = argparse.ArgumentParser(description="Test microphone input levels and VAD detection")
    parser.add_argument("--vad-mode", type=int, choices=[0, 1, 2, 3], default=3,
                        help="WebRTC VAD aggressiveness (0=least, 3=most)")
    parser.add_argument("--threshold", type=float, default=0.003,
                        help="Amplitude threshold for speech detection")
    
    args = parser.parse_args()
    
    try:
        test = MicrophoneTest(vad_mode=args.vad_mode, threshold=args.threshold)
        test.start()
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())