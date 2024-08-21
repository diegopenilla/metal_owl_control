import streamlit as st
import pandas as pd
import os
import requests
import time

# Define the FastAPI server URL
API_URL = "http://localhost:8000"

# Ensure the /instructions folder exists
if not os.path.exists('instructions'):
    os.makedirs('instructions')

# Default sequence file
default_sequence_file = "instructions/sequence.csv"

# Automatically load and start the sequence.csv file if it exists
if os.path.exists(default_sequence_file):
    st.session_state['sequence_df'] = pd.read_csv(default_sequence_file)
else:
    st.warning("Default sequence.csv not found. Please create a sequence.csv in the instructions folder.")

# Initialize session state variables
if 'degrees' not in st.session_state:
    st.session_state['degrees'] = 0
if 'speed' not in st.session_state:
    st.session_state['speed'] = 50
if 'sequence_df' not in st.session_state:
    st.session_state['sequence_df'] = pd.DataFrame(columns=['Degrees', 'Speed', 'Duration', 'Label'])
if 'client_connected' not in st.session_state:
    st.session_state['client_connected'] = False

# Sidebar sections and controls
with st.sidebar:
    st.header("Bird Control")
    
        # Sequence Control Section
    with st.container():
        st.header("Choose Sequence")
        file_list = [f for f in os.listdir('instructions') if f.endswith('.csv')]
        selected_file = st.selectbox("", file_list)

        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("Load Sequence"):
                if selected_file:
                    file_path = os.path.join("instructions", selected_file)
                    st.session_state['sequence_df'] = pd.read_csv(file_path)
                    st.success(f"Loaded sequence from {selected_file}")

        with col2:
            if st.button("Play"):
                if selected_file:
                    response = requests.get(f"{API_URL}/run_sequence", params={"file_path": os.path.join("instructions", selected_file)})
                    if response.status_code == 200:
                        st.success(response.json()['message'])
                    else:
                        st.error(response.json()['detail'])
        
        with col3:
            if st.button("Stop"):
                response = requests.get(f"{API_URL}/emergency_stop")
                if response.status_code == 200:
                    st.error(response.json()['message'])
                else:
                    st.error(response.json()['detail'])

    
    # Motor Control Section
    st.header("Add Step")
    with st.container():
        st.session_state['speed'] = st.number_input("Speed", min_value=1, max_value=1000, value=st.session_state['speed'])
        st.session_state['degrees'] = st.number_input("Position (deg)", value=st.session_state['degrees'], step=1)
        label = st.text_input("Label", value="Command Label")
        duration = st.number_input("Duration (seconds)", min_value=0.1, value=1.0)

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Add to Sequence"):
                new_row = pd.DataFrame({
                    'Degrees': [st.session_state['degrees']], 
                    'Speed': [st.session_state['speed']], 
                    'Duration': [duration], 
                    'Label': [label]
                })
                st.session_state['sequence_df'] = pd.concat([st.session_state['sequence_df'], new_row], ignore_index=True)
                st.success(f"Added command: {label}")
        
        with col2:
            if st.button("Save Sequence"):
                if not st.session_state['sequence_df'].empty:
                    file_name = st.text_input("Enter file name", "sequence.csv")
                    file_path = os.path.join("instructions", file_name)
                    st.session_state['sequence_df'].to_csv(file_path, index=False)
                    st.success(f"Sequence saved as {file_name}")
                else:
                    st.warning("No sequence to save.")
    

# Main content
st.write(f"### `{selected_file}`")
st.dataframe(st.session_state['sequence_df'])

# Function to fetch and display the last step information
def fetch_last_step_info():
    response = requests.get(f"{API_URL}/last_step_info")
    if response.status_code == 200:
        data = response.json()
        info_text = (
            f"**Last Step Information** `{os.path.basename(data['sequence_file'])}`\n"
            f"- **Step Number**: {data['step_number'] - 1}\n"
            f"- **Label**: {data['label']}\n"
            f"- **Degrees**: {data['degrees']}\n"
            f"- **Speed**: {data['speed']}\n"
            f"- **Duration**: {data['duration']}\n"
            f"- **Elapsed Time**: {data['elapsed_time']} seconds"
        )
        return info_text
    else:
        return "Failed to fetch last step information"

# Create a placeholder to display the last step information
info_placeholder = st.empty()

# Periodically fetch and update the last step information
while True:
    info_text = fetch_last_step_info()
    info_placeholder.markdown(info_text)  # Update the info box with the latest data
    time.sleep(1)