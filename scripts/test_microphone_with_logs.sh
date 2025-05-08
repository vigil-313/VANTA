#!/bin/bash
# Run the microphone test script with output shown and saved to log file

# Create logs directory if it doesn't exist
mkdir -p logs

# Activate virtual environment
source venv/bin/activate

# Parse any arguments to pass to the script
ARGS=""
if [ $# -gt 0 ]; then
  ARGS="$@"
fi

# Run the test script with output going to both console and log file
python scripts/test_microphone.py $ARGS 2>&1 | tee logs/microphone_test.log