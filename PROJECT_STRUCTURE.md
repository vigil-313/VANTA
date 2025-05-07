# VANTA Project Structure

## Directory Structure

```
vanta/
├── config/                        # Configuration files
│   ├── __init__.py
│   ├── default_config.yaml        # Default system configuration
│   ├── personality_profiles/      # Different personality configurations
│   │   ├── default.yaml           # Default personality settings
│   │   └── custom_profiles/       # User-defined personalities
│   └── app_settings.py            # Configuration loader/manager
│
├── core/                          # Core system components
│   ├── __init__.py
│   ├── event_bus.py               # Central event system for module communication
│   ├── main_loop.py               # Main application loop
│   ├── system_status.py           # Overall system state tracking
│   └── utils/                     # Shared utilities
│       ├── __init__.py
│       ├── async_helpers.py       # Async processing utilities
│       ├── logging_utils.py       # Enhanced logging functionality
│       └── time_utils.py          # Time-related helpers
│
├── voice/                         # Voice I/O modules
│   ├── __init__.py
│   ├── listener/                  # Speech-to-Text pipeline
│   │   ├── __init__.py
│   │   ├── microphone.py          # Real-time audio capture 
│   │   ├── vad.py                 # Voice activity detection
│   │   ├── stt_service.py         # Speech-to-text conversion service
│   │   └── transcript_processor.py # Process STT results
│   │
│   └── speaker/                   # Text-to-Speech pipeline
│       ├── __init__.py
│       ├── tts_engine.py          # Text-to-speech generation
│       ├── audio_output.py        # Audio playback handling
│       └── speech_queue.py        # Manages voice response queue
│
├── memory/                        # Memory and storage modules
│   ├── __init__.py
│   ├── conversation/
│   │   ├── __init__.py
│   │   ├── transcript_store.py    # Raw conversation storage
│   │   └── session_manager.py     # Conversation session handling
│   │
│   ├── semantic/
│   │   ├── __init__.py
│   │   ├── embeddings.py          # Vector embedding generation
│   │   ├── vector_store.py        # Vector database interface
│   │   └── semantic_search.py     # Memory retrieval functions
│   │
│   └── storage/
│       ├── __init__.py
│       ├── db_connector.py        # Database connection management
│       └── persistence.py         # Data persistence utilities
│
├── reasoning/                     # Reasoning and intelligence
│   ├── __init__.py
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── claude_client.py       # Claude API integration
│   │   ├── gpt_client.py          # Optional GPT-4o integration
│   │   └── prompt_templates.py    # System prompts for LLM
│   │
│   ├── decision/
│   │   ├── __init__.py
│   │   ├── speak_decider.py       # "Should I speak" logic
│   │   └── response_generator.py  # Response content generation
│   │
│   └── context/
│       ├── __init__.py
│       ├── context_builder.py     # Builds context for LLM from memory
│       └── context_analyzer.py    # Analyzes current conversation context
│
├── personality/                   # Personality system
│   ├── __init__.py
│   ├── traits.py                  # Personality trait definitions
│   ├── mood_manager.py            # Dynamic mood state management
│   ├── role_manager.py            # Role emphasis configuration
│   └── tone_adjuster.py           # Response tone modification
│
├── scheduler/                     # Scheduling and timing
│   ├── __init__.py
│   ├── event_scheduler.py         # Schedule recurring events
│   ├── goal_tracker.py            # Personal goal tracking
│   └── reminder_manager.py        # Reminder functionality
│
├── integration/                   # Future integration capabilities
│   ├── __init__.py
│   └── api/
│       ├── __init__.py
│       └── rest_server.py         # REST API for external integrations
│
├── ui/                            # Optional minimal UI components
│   ├── __init__.py
│   ├── status_indicator.py        # Visual system status
│   └── admin_panel.py             # Admin control interface
│
├── scripts/                       # Utility scripts
│   ├── setup_environment.py       # Environment setup helper
│   └── generate_test_data.py      # Creates test data for development
│
├── tests/                         # Test suite
│   ├── __init__.py
│   ├── test_voice.py
│   ├── test_memory.py
│   ├── test_reasoning.py
│   ├── test_personality.py
│   └── test_scheduler.py
│
├── logs/                          # Log directory (gitignored)
│
├── data/                          # Data directory for storage (gitignored)
│   ├── conversations/             # Stored conversation history
│   ├── vector_db/                 # Vector database files
│   └── user_data/                 # User-specific data
│
├── docs/                          # Documentation
│   ├── architecture.md            # System architecture documentation
│   ├── modules/                   # Module-specific documentation
│   └── development_guide.md       # Development guidelines
│
├── .env.example                   # Example environment variables
├── .gitignore                     # Git ignore file
├── LICENSE                        # Project license
├── README.md                      # Project overview
├── PROGRESS_TRACKING.md           # Development progress tracking
├── requirements.txt               # Python dependencies
├── main.py                        # Application entry point
└── setup.py                       # Package setup script
```

## Component Communication

The VANTA system will use an event-driven architecture where components communicate primarily through an event bus, reducing tight coupling:

1. **Event Bus (Core)**: Central communication mechanism where modules publish and subscribe to events
   - All modules will import the event bus for loosely coupled communication

2. **Main Data Flows**:
   - `Voice Listener → Event Bus → Reasoning Engine → Event Bus → Voice Speaker`
   - `Reasoning Engine → Memory Engine → Reasoning Engine`
   - `Scheduler → Event Bus → Reasoning Engine`

3. **Key Dependencies**:
   - `main.py` imports and initializes all core modules
   - `core/main_loop.py` orchestrates the overall system flow
   - `voice/listener/transcript_processor.py` triggers new input events on the event bus
   - `reasoning/decision/speak_decider.py` decides whether to respond
   - `reasoning/decision/response_generator.py` generates responses using the LLM
   - `voice/speaker/speech_queue.py` consumes speech output events

4. **Data Persistence**:
   - All modules use `memory/storage/persistence.py` for data persistence
   - `memory/semantic/vector_store.py` manages embeddings and semantic search

5. **Configuration**:
   - All modules import configuration from `config/app_settings.py`
   - The personality system adjusts LLM behavior through `reasoning/llm/prompt_templates.py`

## Implementation Approach

1. **Phase 1**: Core Infrastructure 
   - Implement event bus and basic module communication
   - Set up voice input/output pipeline with minimal functionality
   - Create simple memory storage for conversations

2. **Phase 2**: Primary Functionality
   - Integrate LLM reasoning engine
   - Implement basic semantic memory
   - Add personality system baseline

3. **Phase 3**: Enhanced Features
   - Implement advanced decision-making logic
   - Add scheduling and goal tracking
   - Enhance semantic memory capabilities

4. **Phase 4**: Refinement
   - Optimize for real-time performance
   - Add admin interface for configuration
   - Implement system resilience features