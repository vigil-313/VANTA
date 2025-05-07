# VANTA

**V**oice-based **A**mbient **N**eural **T**hought **A**ssistant

## Overview

VANTA is a real-time, voice-based AI assistant that behaves like an ambient presence in your environment. It's designed to be a persistent, conversational agent that listens continuously, responds verbally, maintains memory, and evolves its personality over time.

## Features

- **Always Listening**: No wake word required
- **Voice Response**: Natural spoken responses using TTS
- **Memory System**: Remembers and stores all conversations with semantic understanding
- **Selective Responses**: Intelligent decision-making about when to speak
- **Evolving Personality**: Configurable traits and adaptive behavior
- **Goal Tracking**: Tracks personal goals and provides reflective advice

## Project Status

This project is in early development. See [PROGRESS_TRACKING.md](PROGRESS_TRACKING.md) for current status.

## Architecture

VANTA uses a modular, event-driven architecture with clear separation of concerns:

1. **Voice Pipeline**: Audio input/output processing
2. **Memory Engine**: Conversation storage and semantic retrieval
3. **Reasoning Engine**: LLM-based intelligence and decision making
4. **Personality System**: Traits, mood, and behavioral characteristics
5. **Scheduler**: Goal tracking and regular events

For full details, see [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md).

## Development

Follow the [SESSION_PROTOCOL.md](SESSION_PROTOCOL.md) for development workflow practices.

## Requirements

- Python 3.10+
- macOS (initially)
- Internet connection for LLM API access
- Microphone and speakers

## Future Plans

- Integration with workflow platforms
- Deployment to Synology NAS
- Expanded capabilities and integrations