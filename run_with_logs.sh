#!/bin/bash
# Run VANTA with output shown and saved to log file

# Create logs directory if it doesn't exist
mkdir -p logs

# Activate virtual environment
source venv/bin/activate

# Run VANTA with output going to both console and log file
python main.py 2>&1 | tee logs/runtime.log