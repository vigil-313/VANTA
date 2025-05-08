#\!/bin/bash

# Create logs directory if it doesn't exist
mkdir -p logs

# Use fixed log file
LOG_FILE="logs/vanta.log"

# Clear existing log file
> "$LOG_FILE"

# Activate virtual environment
source venv/bin/activate

# Run the main VANTA application with logging
echo "Starting VANTA with logging to $LOG_FILE"
echo "To view logs in real-time, run in another terminal: tail -f $LOG_FILE"

# Run the application and tee output to both console and log file
python main.py 2>&1 | tee "$LOG_FILE"

# Deactivate virtual environment
deactivate
