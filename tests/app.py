# app.py
import streamlit as st
import pandas as pd
import os
import requests

# Define the FastAPI server URL
API_URL = "http://localhost:9120"

# Initialize session state variables
if 'degrees' not in st.session_state:
    st.session_state['degrees'] = 0
if 'speed' not in st.session_state:
    st.session_state['speed'] = 50
if 'sequence_df' not in st.session_state:
    st.session_state['sequence_df'] = pd.DataFrame(columns=['Degrees', 'Speed', 'Duration', 'Label'])
if 'client_connected' not in st.session_state:
    st.session_state['client_connected'] = False

# Function to move motor to 0 degrees when the client connects
def move_to_origin_on_connect():
    response = requests.get(f"{API_URL}/execute_position", params={
        "degrees": 0,
        "speed": st.session_state['speed'],
        "duration": 2,
        "label": "Move to origin (0 degrees)"
    })
    if response.status_code == 200:
        st.success(response.json()['message'])
    else:
        st.error(response.json()['detail'])

# Ensure the motor moves to 0 degrees on client connection
if not st.session_state['client_connected']:
    move_to_origin_on_connect()
    st.session_state['client_connected'] = True

# Ensure the /instructions folder exists
if not os.path.exists('instructions'):
    os.makedirs('instructions')

# Sidebar controls for speed, degrees, label, and duration
st.sidebar.header("Motor Control")

st.session_state['speed'] = st.sidebar.number_input("Speed", min_value=1, max_value=1000, value=st.session_state['speed'])
st.session_state['degrees'] = st.sidebar.number_input("Degrees", value=st.session_state['degrees'], step=1)
label = st.sidebar.text_input("Label", value="Command Label")
duration = st.sidebar.number_input("Duration (seconds)", min_value=0.1, value=1.0)

# Button to add the current command to the sequence
if st.sidebar.button("Add to Sequence"):
    new_row = pd.DataFrame({
        'Degrees': [st.session_state['degrees']], 
        'Speed': [st.session_state['speed']], 
        'Duration': [duration], 
        'Label': [label]
    })
    st.session_state['sequence_df'] = pd.concat([st.session_state['sequence_df'], new_row], ignore_index=True)
    st.success(f"Added command: {label}")

# Button to save the current sequence to a CSV file
if st.sidebar.button("Save Sequence"):
    if not st.session_state['sequence_df'].empty:
        file_name = st.sidebar.text_input("Enter file name", "sequence.csv")
        file_path = os.path.join("instructions", file_name)
        st.session_state['sequence_df'].to_csv(file_path, index=False)
        st.success(f"Sequence saved as {file_name}")
    else:
        st.warning("No sequence to save.")

# Dropdown menu to list CSV files in /instructions folder
file_list = [f for f in os.listdir('instructions') if f.endswith('.csv')]
selected_file = st.sidebar.selectbox("Select a file to load", file_list)

# Button to load the selected file
if st.sidebar.button("Load Sequence"):
    if selected_file:
        file_path = os.path.join("instructions", selected_file)
        st.session_state['sequence_df'] = pd.read_csv(file_path)
        st.success(f"Loaded sequence from {selected_file}")

# Display the current sequence of commands
st.write("### Command Sequence")
st.dataframe(st.session_state['sequence_df'])

# Button to execute the sequence with deterministic timing
if st.button("Execute Sequence"):
    st.write("Executing Sequence...")
    for _, row in st.session_state['sequence_df'].iterrows():
        response = requests.get(f"{API_URL}/execute_position", params={
            "degrees": row['Degrees'],
            "speed": row['Speed'],
            "duration": row['Duration'],
            "label": row['Label']
        })
        if response.status_code == 200:
            st.success(response.json()['message'])
        else:
            st.error(response.json()['detail'])
    st.success("Sequence execution complete!")

# Button to execute the entire sequence in the CSV file
if st.sidebar.button("Execute Full Sequence"):
    if selected_file:
        response = requests.get(f"{API_URL}/run_sequence", params={"file_path": os.path.join("instructions", selected_file)})
        if response.status_code == 200:
            st.success(response.json()['message'])
        else:
            st.error(response.json()['detail'])

# Button to trigger emergency stop
if st.sidebar.button("Emergency Stop"):
    response = requests.get(f"{API_URL}/emergency_stop")
    if response.status_code == 200:
        st.error(response.json()['message'])
    else:
        st.error(response.json()['detail'])

# Display current state
st.write(f"Current Degrees: {st.session_state['degrees']}")
st.write(f"Current Speed: {st.session_state['speed']}")

# Clean up the CAN bus on app shutdown
def shutdown_controller():
    requests.get(f"{API_URL}/shutdown")

st.sidebar.button("Shutdown", on_click=shutdown_controller)