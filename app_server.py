import streamlit as st
import pandas as pd
import os
import requests
import time



API_URL = "http://localhost:9120"

# Function to fetch and display the last step information
def fetch_last_step():
    response = requests.get(f"{API_URL}/last_step_info")
    if response.status_code == 200:
        data = response.json()
        return data
    else:
        return "Failed to fetch info"
    
def fetch_last_step_info(data=None):
    if data:
        if data['step_number'] is not None:
            step_number = data.get("step_number")
            step_number_display = step_number - 1
        else:
            step_number_display = "N/A"
        
        info_text = (
            f"- **Step Number**: {step_number_display}\n"
            f"- **Label**: {data['label']}\n"
            f"- **Degrees**: {data['degrees']}\n"
            f"- **Speed**: {data['speed']}\n"
            f"- **Acceleration**: {data['acceleration']}\n"  # Display acceleration
            f"- **Duration**: {data['duration']}\n"
            f"- **Elapsed Time**: {round(data['elapsed_time'],2)} seconds\n"
        )
        return info_text, data.get("warning")
    else:
        return st.error("No fetch last step data"), None

# Ensure the /instructions folder exists
if not os.path.exists('instructions'):
    os.makedirs('instructions')

# Hide the "Running..." text using CSS
hide_running_text = """
    <style>
    [data-testid="stStatusWidget"] {
        display: none !important;
    }
    [data-testid="stHeader"] {
        display: none !important;
    }
    </style>
"""

# Inject the custom CSS into the app
st.markdown(hide_running_text, unsafe_allow_html=True)


# Default sequence file
default_sequence_file = "instructions/sequence.csv"

# Initialize session state variables
if 'degrees' not in st.session_state:
    st.session_state['degrees'] = 0
if 'speed' not in st.session_state:
    st.session_state['speed'] = 50
if 'acceleration' not in st.session_state:
    st.session_state['acceleration'] = 5  # Default value for acceleration
if 'sequence_df' not in st.session_state:
    st.session_state['sequence_df'] = pd.read_csv(default_sequence_file)

# Sidebar sections and controls
with st.sidebar:
    st.header("Bird Control")
    
    # Sequence Control Section
    with st.container():
        st.header("Choose Sequence")
        file_list = [f for f in os.listdir('instructions') if f.endswith('.csv')]
        selected_file = st.selectbox("Choose a file", file_list)


        if st.button("Load Sequence"):
            if selected_file:
                file_path = os.path.join("instructions", selected_file)
                st.session_state['sequence_df'] = pd.read_csv(file_path)
                st.success(f"Loaded sequence from {selected_file}")

    # Motor Control Section
    st.header("Add Step")
    with st.container():
        st.session_state['speed'] = st.number_input("Speed", min_value=1, max_value=600, value=st.session_state['speed'])
        st.session_state['degrees'] = st.number_input("Position (deg)", value=st.session_state['degrees'], step=1)
        st.session_state['acceleration'] = int(st.number_input("Acceleration", min_value=0, max_value=50, value=st.session_state['acceleration']))  # New field for acceleration
        label = st.text_input("Label", value="Command Label")
        duration = st.number_input("Duration (seconds)", min_value=0.1, value=1.0)

        st.warning("Adding steps to the sequence will stop the motor...")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Add to Sequence"):
                
                stop_message = st.empty()
                stop_message.info("Stopping motor. Please wait ")
                response = requests.get(f"{API_URL}/emergency_stop")
                if response.status_code == 200:
                    st.error(response.json()['message'])
                else:
                    st.error(response.json()['detail'])
                stop_message.empty()
                    
                # Create new row to add to sequence_df
                new_row = pd.DataFrame({
                    'Degrees': [st.session_state['degrees']], 
                    'Speed': [st.session_state['speed']], 
                    'Acceleration': [st.session_state['acceleration']],  # Include acceleration
                    'Duration': [duration], 
                    'Label': [label]
                })
                
                
                # Append the new row to the sequence_df in session state
                st.session_state['sequence_df'] = pd.concat([st.session_state['sequence_df'], new_row], ignore_index=True)

        with col2:
            file_name = st.text_input("Enter file name", "sequence.csv")
            
            if st.button("Save Sequence"):
                if not st.session_state['sequence_df'].empty:
                    file_path = os.path.join("instructions", file_name)
                    st.session_state['sequence_df'].to_csv(file_path, index=False)
                    st.success(f"Sequence saved as {file_name}")
                else:
                    st.warning("No sequence to save.")
                    
# Main content
button_loop = st.button("Play")
loop_info = st.empty()
if button_loop:
    
    # First, move the motor to 0 degrees
    loop_info.info("Moving motor to 0 degrees...")
    
    # Send the execute_position request to move to 0 degrees
    try:
        response = requests.get(f"{API_URL}/execute_position", params={
            "degrees": 0,
            "speed": st.session_state['speed'],  # Use the current speed setting
            "acceleration": st.session_state['acceleration'],  # Use the current acceleration setting
            "duration": 1.0,  # Set a reasonable duration for this movement
            "label": "Move to 0 degrees"
        })
        response.raise_for_status()
        loop_info.success(response.json()['message'])
    except requests.exceptions.RequestException as e:
        loop_info.error(f"Failed to move motor to 0 degrees: {str(e)}")
        st.stop()  # Stop further execution if the motor cannot be moved to 0

    # Check if the motor has reached 0 degrees
    while True:
        last_step_info = fetch_last_step()
        if last_step_info['degrees'] == 0:
            loop_info.success("Motor is at 0 degrees. Starting sequence...")
            break
        time.sleep(1)

    # Now proceed with executing the sequence
    sequence_df = st.session_state.get('sequence_df')
    if not sequence_df.empty:

        # Define the temporary file path
        temp_file_path = os.path.join("instructions", "temp.csv")
        sequence_df.to_csv(temp_file_path, index=False)
        time.sleep(0.5)

        # Send the temporary file path to the API
        response = requests.get(f"{API_URL}/run_sequence", params={"file_path": temp_file_path})
        if response.status_code == 200:
            loop_info.success(response.json()['message'])
        else:
            st.error(response.json()['detail'])
    else:
        st.error("Sequence is empty... load a new file or add steps to the sequence.")
    
    loop_info.empty()

if st.button("Stop"):
    stop_message = st.empty()
    stop_message.info("Stopping motor. Please wait ")
    response = requests.get(f"{API_URL}/emergency_stop")
    if response.status_code == 200:
        st.error(response.json()['message'])
    else:
        st.error(response.json()['detail'])
    stop_message.empty()
    
st.write(f"### Sequence")
st.dataframe(st.session_state['sequence_df'])


# Create a placeholder to display the last step information
info_placeholder = st.empty()
warning_placeholder = st.empty()

# Create a section at the bottom of the app for the manual
with st.expander("Show Manual"):
    st.markdown("""
    ## Owl Controller

    ### Sequence File: (`sequence.csv`)
    - **Purpose**: This is the primary sequence file that the robot will loop over automatically once it is reset.
    - **How to Use**: 
        - To ensure the robot uses your current sequence, save the sequence shown in the main window to this file using the "Save Sequence" button.

    ### Modifying the Sequence
    - **Adding Steps**:
        - Use the "Add Step" section in the sidebar to add new steps to your sequence.
        - Remember to set the appropriate speed, position (degrees), acceleration, and duration for each step.
        - Label your steps for better clarity.

    ### Important Notes
    - **Stopping the Motor**: 
        - Adding new steps to the sequence will stop the motor. The motor will remain stopped until you start the sequence again.
    - **Loading a New Sequence**: 
        - You can load a different sequence file from the "Choose Sequence" section in the sidebar. This will replace the current sequence in the main window with the new one from the selected file.
    - All saved sequences are saved as .csv files in the `/instructions` folder.
""")
    
# Periodically fetch and update the last step information
while True:
    data = fetch_last_step()
    if type(data) == str:
        st.warning("fetch last step failed... server error")
    else:
        info_text, warning = fetch_last_step_info(data)
        info_placeholder.markdown(info_text)  # Update the info box with the latest data  
        if warning:
            warning_msg = f"Step Number {data['step_number']} - {warning}"
            warning_placeholder.error(warning_msg)
        time.sleep(0.3)
