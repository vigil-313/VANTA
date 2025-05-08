# VANTA Diagnostic Scripts

This directory contains scripts for diagnosing and testing VANTA components.

## Available Scripts

### Microphone Test (`test_microphone.py`)

A diagnostic tool to test microphone input levels and speech detection sensitivity.

**Features:**
- Real-time visualization of audio levels
- WebRTC VAD speech detection
- Amplitude threshold-based detection
- Adjustable sensitivity parameters

**Usage:**
```bash
# Run with default settings (VAD mode 3, threshold 0.003)
./scripts/test_microphone.py

# Adjust VAD aggressiveness (0=least, 3=most aggressive)
./scripts/test_microphone.py --vad-mode 2

# Adjust amplitude threshold for speech detection
./scripts/test_microphone.py --threshold 0.005
```

### Microphone Test with Logging (`test_microphone_with_logs.sh`)

Runs the microphone test with output logged to a file for tailing.

**Usage:**
```bash
# Run with default settings
./scripts/test_microphone_with_logs.sh

# Pass arguments to the underlying test script
./scripts/test_microphone_with_logs.sh --threshold 0.001 --vad-mode 1

# In a separate terminal, tail the logs
tail -f logs/microphone_test.log
```

**Requirements:**
- numpy
- pyaudio
- matplotlib
- webrtcvad

Press Ctrl+C to exit the test.

## Interpreting Results

When running the microphone test:
- The graph shows audio levels over time
- Green dots indicate detected speech
- The red dashed line shows the threshold level
- Terminal output shows real-time level and detection status

If speech is not being detected properly:
1. Try lowering the threshold (e.g., `--threshold 0.001`)
2. Try different VAD modes
3. Check if audio levels are consistently very low (may indicate a hardware or driver issue)