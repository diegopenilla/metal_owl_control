#!/bin/bash

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
METAL_OWL_CONTROL_DIR=$(realpath $SCRIPT_DIR/..)

source $METAL_OWL_CONTROL_DIR/env/bin/activate

# Run the FastAPI server in the background
python3 $METAL_OWL_CONTROL_DIR/server.py &

# Get the process ID of the FastAPI server
FASTAPI_PID=$!

sleep 3

# Run the Streamlit app
streamlit run $METAL_OWL_CONTROL_DIR/app_server.py &

# Get the process ID of the Streamlit app
STREAMLIT_PID=$!

# Wait for both processes to complete
wait $FASTAPI_PID $STREAMLIT_PID