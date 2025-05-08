# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## IMPORTANT: Session Protocol

At the start of EVERY new Claude Code session (#command SESSION_START), IMMEDIATELY perform these steps in order:

1. Review PROGRESS_TRACKING.md to understand current project status
2. Check status_report.txt from the previous session
3. Identify which prompt file to work on next based on progress
4. Update PROGRESS_TRACKING.md with a new session entry:
   ```
   ### Session X (YYYY-MM-DD HH:MM - In Progress)
   - Session goals:
     - [List primary objectives for this session]
   ```

For full protocol details, see SESSION_PROTOCOL.md which defines procedures for:
- #command SESSION_START - Beginning a new session
- #command PROGRESS_UPDATE - Making significant progress
- #command NEW_MODULE - Creating new modules
- #command SESSION_END - Concluding sessions

## IMPORTANT: Logging Protocol

For any script execution:
1. ALWAYS create a shell script wrapper for each Python script that:
   - Captures output with tee to both console and log file
   - Puts logs in the logs/ directory
   - Allows for tailing logs in a separate terminal
2. Name these scripts with "_with_logs.sh" suffix
3. Make these scripts executable with chmod +x
4. Provide clear instructions for tailing logs in a separate terminal

## Project Overview

VANTA (Voice-based Ambient Neural Thought Assistant) is a modular, voice-based, memory-augmented AI companion that:
- Listens continuously without a wake word
- Provides voice responses
- Maintains conversation memory and semantic understanding
- Has personality traits and goal-tracking capabilities
- Decides autonomously when to speak
- Runs on macOS (with future Synology NAS deployment)

## Architecture

The system is structured around these core modules:

1. **Voice Pipeline** - Real-time audio processing:
   - STT (Speech-to-Text) processing
   - TTS (Text-to-Speech) output

2. **Memory Engine** - Conversation storage and retrieval:
   - Transcript logging
   - Vector embedding for semantic memory

3. **Personality System** - Agent's behavioral characteristics:
   - Configurable traits
   - Mood and tone management

4. **Goals and Scheduling** - Self-management capabilities:
   - Personal goal tracking
   - Regular check-ins and events

5. **Reasoning Engine** - Decision logic:
   - LLM integration (Claude API or GPT-4o)
   - "Should I speak" determination

## Development Guidelines

This is a Python-based project with emphasis on:
- Modularity for easy component replacement
- Future extensibility
- Clean separation of concerns

## Commands

The following commands should be implemented in upcoming development:

```
# Setup environment
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run the VANTA assistant
python main.py

# Run tests (once implemented)
pytest tests/

# Run specific test suite
pytest tests/test_memory_engine.py
```