#!/bin/bash

# Create logs directory if it doesn't exist
mkdir -p logs

# Use fixed log file
LOG_FILE="logs/speech_debug.log"

# Clear existing log file
> "$LOG_FILE"

# Activate virtual environment
source venv/bin/activate

# Run the diagnostic script with the optimized parameters
echo "Starting Speech Recognition Debug Test with full logging to $LOG_FILE"
echo "To view logs in real-time, run in another terminal: tail -f $LOG_FILE"
echo "Testing with: VAD mode 2, amplitude threshold 0.003, silence threshold 500ms"
echo "Speak clearly to test detection and transcription"
echo "Press Ctrl+C to stop the test"

# Run the main VANTA application WITHOUT filtering logs
python main.py 2>&1 | tee "$LOG_FILE"

# Deactivate virtual environment
deactivate