# server.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import uvicorn
import os
import pandas as pd
from controller import ServoController
import threading
import time
from datetime import datetime
from contextlib import asynccontextmanager

# Initialize the FastAPI app with lifespan context
@asynccontextmanager
async def lifespan(app: FastAPI):
    global execution_thread, stop_event

    # Code to run during startup
    stop_event.clear()  # Ensure the stop event is cleared
    file_path = "instructions/sequence.csv"

    if os.path.exists(file_path):
        execution_thread = threading.Thread(target=loop_sequence, args=(file_path,))
        execution_thread.start()
    else:
        print("sequence.csv not found. Please ensure the file exists in the 'instructions' directory.")
    
    yield  # Run the app

    # Code to run during shutdown
    stop_event.set()  # Signal to stop any ongoing sequence
    if execution_thread and execution_thread.is_alive():
        execution_thread.join()  # Wait for the thread to finish
    servo_controller.shutdown()

app = FastAPI(lifespan=lifespan)

# Initialize the ServoController
servo_controller = ServoController()

# Shared state to manage the execution thread and stopping
stop_event = threading.Event()
execution_thread = None

# Global variable to store the last executed step information
last_step_info = {
    "degrees": None,
    "speed": None,
    "acceleration": None,
    "duration": None,
    "label": None,
    "start_time": None,
    "elapsed_time": None,
    "sequence_file": None,
    "step_number": None,
    "warning": None,  # New field to store warnings
}

class PositionCommand(BaseModel):
    degrees: int
    speed: int
    acceleration: int  # Added acceleration field
    duration: float
    label: str

class SequenceCommand(BaseModel):
    file_path: str

def loop_sequence(file_path: str):
    global stop_event, last_step_info
    sequence_df = pd.read_csv(file_path)

    print(sequence_df)
    while not stop_event.is_set():
        try:
            for i, row in sequence_df.iterrows():
                if stop_event.is_set():
                    break
                
                print(f"Processing row {i}: {row}")

                if not row.empty:
                    try:
                        # Extract row values with checks for None
                        degrees = row['Degrees']
                        speed = row['Speed']
                        acceleration = row['Acceleration']
                        duration = row['Duration']
                        label = row['Label']

                        # Check if any required field is None
                        if any(x is None for x in [degrees, speed, acceleration, duration, label]):
                            print(f"One or more required fields are None in row {i}. Skipping this row.")
                            continue

                        # Debugging information
                        print(f"Executing instruction: Degrees={degrees}, Speed={speed}, Acceleration={acceleration}, Duration={duration}, Label={label}")
                        
                        # Execute the instruction and get the result
                        elapsed_time, warning_msg = servo_controller.execute_instruction(degrees, speed, acceleration, duration, label)

                        # Update last step information
                        last_step_info.update({
                            "degrees": degrees,
                            "speed": speed,
                            "acceleration": acceleration,
                            "duration": duration,
                            "label": label,
                            "start_time": datetime.now(),
                            "step_number": i + 1,  # Step number is 1-based index
                            "warning": warning_msg,
                            "elapsed_time": elapsed_time
                        })

                    except TypeError as e:
                        print(f"Error accessing row data at step {i}: {e}")
                        break
                    except Exception as e:
                        print(f"Unexpected error at step {i}: {e}")
                        break
                else:
                    print(f"Skipping empty row {i}")

        except Exception as e:
            print(f"Error executing sequence: {e}")
            break

        if not stop_event.is_set():
            print("Sequence completed. Restarting...")

@app.get("/execute_position")
def execute_position(degrees: int, speed: int, acceleration: int, duration: float, label: str):
    global last_step_info
    try:
        elapsed_time, warning_msg = servo_controller.execute_instruction(degrees, speed, acceleration, duration, label)
        last_step_info.update({
            "degrees": degrees,
            "speed": speed,
            "acceleration": acceleration,
            "duration": duration,
            "label": label,
            "start_time": datetime.now(),
            "elapsed_time": elapsed_time,
            "warning": warning_msg,
            "step_number": None,  # Not part of a sequence, so no step number
            "sequence_file": None,  # Not part of a sequence, so no sequence file
        })
        return {"status": "success", "message": f"Executed {label} to {degrees} degrees at speed {speed} with acceleration {acceleration}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/run_sequence")
def run_sequence(file_path: str):
    global execution_thread, stop_event

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    # Ensure any previous sequence is stopped before starting a new one
    if execution_thread and execution_thread.is_alive():
        stop_event.set()  # Signal the thread to stop
        execution_thread.join()  # Wait for the thread to finish

    stop_event.clear()  # Reset the stop event for the new sequence

    execution_thread = threading.Thread(target=loop_sequence, args=(file_path,))
    execution_thread.start()

    return {"status": "success", "message": f"Started executing sequence from {file_path}"}

@app.get("/emergency_stop")
def emergency_stop():
    global stop_event

    try:
        stop_event.set()  # Signal the sequence execution to stop
        if execution_thread and execution_thread.is_alive():
            execution_thread.join()  # Wait for the thread to finish
        servo_controller.servo.emergency_stop_motor()
        return {"status": "success", "message": "Servo motor stopped successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/last_step_info")
def get_last_step_info():
    global last_step_info

    if last_step_info['start_time']:
        last_step_info['elapsed_time'] = (datetime.now() - last_step_info['start_time']).total_seconds()
    
    last_step_info['degrees'] = servo_controller.get_motor_degrees()
        
    return last_step_info

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=9120)