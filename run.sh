#!/bin/bash

# Run the FastAPI server in the background
python3 server.py &

# Get the process ID of the FastAPI server
FASTAPI_PID=$!

# Run the Streamlit app
streamlit run app_server.py &

# Get the process ID of the Streamlit app
STREAMLIT_PID=$!

# Wait for both processes to complete
wait $FASTAPI_PID $STREAMLIT_PID