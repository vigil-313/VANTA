#!/bin/bash

# Create logs directory if it doesn't exist
mkdir -p logs

# Use fixed log file
LOG_FILE="logs/transcription_test.log"

# Clear existing log file
> "$LOG_FILE"

# Activate virtual environment
source venv/bin/activate

# Run the diagnostic script with verbose logging
echo "Starting Transcription Test with logging to $LOG_FILE"
echo "To view logs in real-time, run in another terminal: tail -f $LOG_FILE"
echo "Please speak clearly when prompted: 'Testing one two three. This is a voice recognition test.'"
echo "Press Ctrl+C to stop the test"

# Run the python script with full logging
python scripts/test_transcription_only.py --duration 5 2>&1 | tee "$LOG_FILE"

# Deactivate virtual environment
deactivate