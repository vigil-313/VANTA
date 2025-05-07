# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

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