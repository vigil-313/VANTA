# Audio Pipeline Documentation

## Overview

VANTA's audio pipeline processes real-time speech from microphone input through a series of steps:

1. **Audio Capture** - `MicrophoneListener` captures raw audio from the system microphone
2. **Speech Detection** - `VoiceActivityDetector` (VAD) identifies speech segments
3. **Speech Recognition** - `STTService` transcribes speech segments to text
4. **Transcript Processing** - `TranscriptProcessor` manages transcribed speech

## Components and Flow

### Microphone Listener
- Captures audio through sounddevice library
- Calculates RMS audio level for each chunk
- Publishes `AUDIO_CAPTURED` events with audio data
- Tracks min/max levels for diagnostics

### Voice Activity Detector (VAD)
- Uses dual detection approach:
  - WebRTC VAD algorithm
  - Amplitude threshold detection
- Manages speech state (start, continue, end)
- Publishes `SPEECH_DETECTED` events
- Adds `speech_ended` flag to audio events

### STT Service
- Buffers audio frames during active speech
- Processes complete speech segments
- Uses Whisper for transcription
- Publishes `TRANSCRIPTION_COMPLETE` events

### Transcript Processor
- Manages conversation context buffer
- Logs transcriptions to file
- Triggers response processing

## Critical Optimizations

### Speech Detection
The VAD uses two parallel detection methods:
1. **WebRTC VAD** - Traditional voice activity detection
2. **Amplitude Threshold** - Backup for low volume microphones

Key parameters:
- `vad_sensitivity: 1` - Balanced WebRTC sensitivity
- `audio_threshold: 0.0005` - Extremely low amplitude threshold for quiet mics
- `silence_threshold: 200` - 200ms of silence to mark end of speech
- `max_speech_frames: 150` - ~4.5 seconds before forcing transcription
- `max_phrase_duration: 10000` - 10 seconds maximum before forced transcription

### Speech End Detection
Multiple mechanisms trigger transcription:
1. **Silence Detection** - Normal pauses in speech
2. **Forced Ending** - For very long continuous speech
3. **Safety Timeout** - As a fallback for missed endings

### Audio Level Calculations
RMS amplitude calculation provides more accurate level detection:
```python
audio_level = np.sqrt(np.mean(np.square(audio_data_float)))
```

## Troubleshooting

### Speech Not Detected
- Check microphone input levels using test scripts
- Consider decreasing `audio_threshold` below 0.0005
- Try VAD mode 0 for less aggressive detection

### Speech Not Transcribed
- Check VAD is properly adding `speech_ended` flag
- Ensure STT service is processing audio
- Verify Whisper model is loading correctly

### Continuous Speech Problem
- Adjust `max_speech_frames` and `silence_threshold`
- Look for gaps in the speech stream
- Monitor CPU usage for processing bottlenecks

## Diagnostic Tools

Use the included diagnostic scripts:
- `scripts/test_mic_simple.py` - Terminal-based audio level visualization
- `scripts/test_microphone.py` - Full audio visualization with matplotlib

Example:
```bash
python scripts/test_mic_simple.py --vad-mode 1 --threshold 0.0005
```

## Typical Audio Levels

Based on diagnostic testing:
- Normal speech: 0.001 - 0.01
- Loud speech: 0.01 - 0.05
- Very loud speech/noise: 0.05 - 0.2

Recommended settings:
- For normal microphones: `audio_threshold: 0.001`
- For quiet/distant microphones: `audio_threshold: 0.0005`
- For loud environments: `vad_sensitivity: 2` with `audio_threshold: 0.002`