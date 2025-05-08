# Audio Calibration Findings and Fixes

## Problem Statement
Speech was being detected by the Voice Activity Detector (VAD) but not properly transcribed, creating a disconnect in the processing pipeline.

## Root Causes Identified
1. **Speech End Detection Issues** - The VAD was not reliably marking the end of speech segments
2. **State Management Problems** - Speech state was not consistently communicated between components
3. **Sensitivity Calibration** - Parameters needed optimization for quiet microphone input
4. **Safety Mechanisms** - Lacking fallback mechanisms for continuous speech

## Key Fixes Implemented

### 1. Voice Activity Detector (VAD) Improvements
- **Dual Detection** - Combined WebRTC VAD with amplitude threshold approach
- **Forced Transcription** - Added mechanism to force transcription after 4.5 seconds
- **Parameter Exposure** - Made silence thresholds configurable from config file
- **State Reset** - Ensured proper state reset after speech ends
- **Improved Logging** - Added detailed logging for debugging speech detection

### 2. STT Service Enhancements  
- **Alternate Activation** - Added ability to activate from audio event flags
- **Buffer Management** - Improved handling of speech buffer with race condition protection
- **Immediate Reset** - Reset speech state before processing to allow new detection sooner
- **Fail Safety** - Added state reset in exception handlers
- **Detailed Logging** - Enhanced logging with emoji markers for easy identification

### 3. Configuration Optimization
- **VAD Sensitivity** - Increased to mode 2 for better filtering of background noise
- **Silence Threshold** - Increased to 500ms for better handling of natural speech pauses
- **Phrase Duration** - Maintained at 10s for reasonable phrase lengths
- **Amplitude Threshold** - Calibrated to 0.003 based on observed speech levels
- **Speech Frames** - Require 5 consecutive frames (~150ms) to trigger speech detection

### 4. Documentation
- **Audio Pipeline** - Created comprehensive documentation of the audio processing flow
- **Calibration Guide** - Documented findings for typical audio levels
- **Troubleshooting** - Added troubleshooting guides for common issues

## Key Parameter Changes
Parameter | Old Value | New Value | Reason
--- | --- | --- | ---
vad_sensitivity | 0 | 2 | Better filtering of background noise
silence_threshold | 200ms | 500ms | Better handling of natural pauses in speech
audio_threshold | 0.0005 | 0.003 | Calibrated to actual observed speech levels
min_speech_frames | 2 frames | 5 frames | Require 150ms of consistent sound to trigger speech
max_speech_frames | 150 frames | 200 frames | Allow slightly longer phrases (~6s) before forced end

## Industry Standard Parameters

Based on extensive research of speech recognition systems:

1. **WebRTC VAD Mode**:
   - Mode 0: Use only in ultra-quiet environments for maximum sensitivity
   - Mode 1: Good for quiet rooms with minimal background noise
   - **Mode 2: Recommended for most environments** (our new setting)
   - Mode 3: Best for noisy environments, may miss some speech

2. **Silence Detection**:
   - 300-500ms: Preserves natural speech with brief pauses
   - 500-750ms: Standard in most commercial systems
   - 750-1000ms: More lenient, better for slower speakers

3. **Amplitude Thresholds** (for normalized audio):
   - 0.001-0.002: Extremely sensitive, catches very quiet speech
   - **0.003-0.005: Good balance for typical microphones** (our new setting)
   - 0.01-0.02: Better for noisy environments

4. **Min Speech Frames**:
   - 3-5 frames (90-150ms): Industry standard to avoid false triggers
   - Shorter values risk detecting noise as speech

## Testing Recommendations
1. Run with adjusted settings and monitor logs for:
   - `🎙️ SPEECH DETECTED` markers
   - `🛑 SPEECH ENDED` or forced transcription markers
   - `✅ Transcription complete` confirmations

2. If issues persist, run diagnostic scripts:
   ```
   python scripts/test_mic_simple.py --vad-mode 2 --threshold 0.003
   ```

3. Observe speech detection percentage and adjust parameters accordingly:
   - If speech detection % is too low: Decrease VAD mode to 0, lower threshold
   - If speech detection % is too high: Increase VAD mode to 2, raise threshold

## Expected Outcomes
- Speech will be detected with 5+ consecutive frames above threshold (~150ms of consistent sound)
- Speech segments will end after 500ms of silence or 6s of continuous speech
- Transcription will be triggered by speech_ended flags
- The STT service will process all detected speech segments
- Better filtering of background noise with fewer false triggers
- Improved handling of natural speech patterns with appropriate pauses