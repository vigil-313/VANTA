# VANTA Transcription Architecture

This document describes the architecture of the transcription module in VANTA, which handles Speech-to-Text (STT) processing.

## Overview

The transcription system has been designed with these key principles:

1. **Stability** - The system should never crash, even if individual components fail
2. **Isolation** - Problematic components (like Whisper) run in separate processes
3. **Graceful Degradation** - Fallback mechanisms ensure continued operation
4. **Resource Management** - Memory limits and timeouts prevent resource exhaustion

## Architecture Components

The transcription architecture consists of these key components:

### STT Service (`stt_service.py`)

The STT Service is the primary interface for transcription in VANTA. It:

- Manages audio buffers for speech segments
- Coordinates with VAD (Voice Activity Detection) to identify speech
- Delegates actual transcription to the Transcription Manager
- Handles speech state tracking and events

### Transcription Manager (`transcription_manager.py`)

The Transcription Manager coordinates between different transcription backends:

- Selects the appropriate transcription service based on context and history
- Implements fallback logic when services fail
- Tracks failure counts and implements recovery strategies
- Provides a consistent interface regardless of backend

### Whisper Process (`whisper_process.py`)

The Whisper Process Manager isolates Whisper in a separate process:

- Runs Whisper in a completely separate Python process
- Communicates using serialized IPC (Inter-Process Communication)
- Implements watchdog timers to detect and recover from hangs
- Sets resource limits to prevent memory exhaustion
- Automatically restarts failed processes

### Basic STT (`basic_stt.py`)

The Basic STT provides a lightweight fallback transcription service:

- Uses simple heuristics to estimate speech content
- Provides generic responses based on audio characteristics
- Requires minimal resources and never crashes
- Serves as an ultimate fallback when Whisper fails

### Whisper Worker (`whisper_worker.py`)

The Whisper Worker runs in a separate process:

- Loads the Whisper model and performs transcription
- Communicates via stdin/stdout JSON messages
- Implements memory limits and self-monitoring
- Processes one transcription request at a time

## Flow of Operation

1. **Speech Detection**
   - VAD detects speech and notifies the STT Service
   - STT Service buffers the audio frames

2. **Speech End Detection**
   - VAD detects the end of speech
   - STT Service completes the current audio buffer

3. **Audio Processing**
   - STT Service sends complete audio to Transcription Manager
   - Transcription Manager selects the appropriate backend

4. **Transcription**
   - If using Whisper Process:
     - Audio is serialized and sent to worker process
     - Worker transcribes with timeout protection
     - Result is returned via IPC
   - If using Basic STT:
     - Audio is analyzed for speech content and duration
     - Generic response is provided based on characteristics

5. **Result Handling**
   - Transcription Manager processes the result
   - STT Service publishes the transcription event
   - Error handling occurs at each level

## Failure Handling

The system implements multiple layers of failure protection:

1. **Timeout Protection**
   - All transcription operations have timeout limits
   - ThreadPoolExecutor provides timeout enforcement

2. **Process Isolation**
   - Whisper runs in a separate process
   - Crashes in Whisper won't affect the main application

3. **Resource Limits**
   - Memory limits are set on the worker process
   - Audio duration is capped to prevent resource exhaustion

4. **Fallback Cascade**
   - System tracks failures and automatically switches to simpler methods
   - After a cooling-off period, it attempts to recover primary services

5. **Graceful Degradation**
   - Even if Whisper fails completely, Basic STT provides minimal functionality
   - User experience degrades gracefully rather than crashing

## Configuration Options

The transcription system can be configured through the main config:

```yaml
stt:
  service: "whisper"  # Primary service to use
  model: "base"       # Whisper model size
  language: "en"      # Default language
  max_failures: 3     # Failures before fallback
  failure_backoff: 300  # Seconds to wait before retry
  timeout_short: 5.0    # Timeout for short segments
  timeout_standard: 10.0  # Timeout for standard segments
```

## Future Improvements

Potential future improvements to the transcription architecture:

1. **Multiple Transcription Backends**
   - Support for cloud services like Google Speech, AWS Transcribe
   - Local alternatives like Vosk or Mozilla DeepSpeech

2. **Stream Processing**
   - Stream processing for incremental transcriptions
   - Early results while speech is ongoing

3. **Multi-model Approach**
   - Use tiny models for fast responses
   - Refine with larger models asynchronously

4. **Error Analysis**
   - Track and analyze transcription errors
   - Tune parameters based on error patterns

5. **Pre/Post Processing**
   - Audio noise filtering before transcription
   - Text post-processing for corrections