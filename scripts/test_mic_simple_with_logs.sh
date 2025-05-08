#\!/bin/bash

# Create logs directory if it doesn't exist
mkdir -p logs

# Use fixed log file
LOG_FILE="logs/mic_test.log"

# Clear existing log file
> "$LOG_FILE"

# Activate virtual environment
source venv/bin/activate

# Run the diagnostic script with the optimized parameters
echo "Starting Microphone Test with logging to $LOG_FILE"
echo "To view logs in real-time, run in another terminal: tail -f $LOG_FILE"
echo "Testing with: VAD mode 1, amplitude threshold 0.0005"
echo "Press Ctrl+C to stop the test and view statistics"

# Run the simple microphone test with our optimized settings
python scripts/test_mic_simple.py --vad-mode 1 --threshold 0.0005 2>&1 | tee "$LOG_FILE"

# Deactivate virtual environment
deactivate
