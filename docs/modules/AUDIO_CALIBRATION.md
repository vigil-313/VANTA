# Audio Detection Calibration Guide

This document describes how to calibrate VANTA's audio detection system for optimal speech recognition, especially in environments with low microphone input levels.

## Overview

VANTA uses a dual-detection approach for identifying speech in audio input:

1. **WebRTC VAD** (Voice Activity Detection) - A specialized algorithm for detecting human speech
2. **Amplitude threshold detection** - A simple backup method that triggers on audio level

This combination provides reliable speech detection even with microphones that produce low-level signals.

## Diagnostic Testing Results

Testing was performed using the `scripts/test_mic_simple.py` diagnostic tool, which revealed:

- Typical background noise levels: 0.0001-0.0005
- Typical quiet speech levels: 0.001-0.01
- Louder speech peaks: 0.05-0.18

Based on this analysis, we calibrated the system as follows:

1. Reduced WebRTC VAD sensitivity to mode 0 (least aggressive)
2. Set amplitude threshold very low (0.0005) to catch quiet speech
3. Improved audio level calculation for more accurate measurement
4. Added extensive logging to monitor detection performance

## Configuration Parameters

The following parameters in `vanta/config/default_config.yaml` control speech detection:

```yaml
microphone:
  vad_sensitivity: 0  # 0-3, where 0 is least aggressive (best for low volume microphones)
  audio_threshold: 0.0005  # Amplitude threshold for speech detection
```

## Troubleshooting

If speech detection is not working properly:

1. **Too few detections** (system doesn't hear you):
   - Lower the `audio_threshold` value (try 0.0003)
   - Make sure microphone is positioned closer to speaker
   - Check system sound settings to ensure input levels are adequate

2. **Too many false detections** (triggers on background noise):
   - Increase the `audio_threshold` value slightly (try 0.001)
   - Increase `vad_sensitivity` to 1 or 2 for more aggressive filtering
   - Increase consecutive frames required by adjusting `min_speech_frames` in the code

## Diagnostic Tools

VANTA includes diagnostic tools to help with audio calibration:

1. **Microphone Level Visualization** (`scripts/test_mic_simple.py`):
   ```bash
   # Run with default settings
   ./scripts/test_mic_simple_with_logs.sh
   
   # Run with custom threshold
   ./scripts/test_mic_simple_with_logs.sh --threshold 0.001 --vad-mode 1
   ```

2. **Real-time Logging**:
   - Set log level to DEBUG in config
   - Monitor logs with `tail -f logs/vanta.log`
   - Look for lines with "Audio level" to see actual input levels

## Implementation Details

The VAD system is implemented in `vanta/voice/listener/vad.py` and uses:

- WebRTC's VAD algorithm via the `webrtcvad` Python package
- Custom amplitude threshold detection as a backup mechanism
- Frame-based processing with state tracking
- Detailed logging for diagnostic purposes

The diagnostic script at `scripts/test_mic_simple.py` provides a standalone tool for measuring audio levels and testing speech detection settings without running the full VANTA system.

## Hardware Recommendations

For optimal speech detection:

- Use a high-quality microphone when possible
- Position microphone within 1-2 feet of speaker
- Minimize background noise in the environment
- Consider a USB microphone with preamp if built-in microphone produces very low levels