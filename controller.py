# controller.py
import can
import time
import os
import pandas as pd
import json
from datetime import datetime
from core.mks_servo import MksServo

# Constants for conversion
DEGREES_TO_UNITS = 16390 / 360

class ServoController:
    def __init__(self, config_path='config.json', can_interface='socketcan', channel='can0', bitrate=500000, device_id=1):
        # Load configuration from JSON
        self.config = self.load_config(config_path)
        
        # Set up CAN bus and servo controller
        self.bus = can.interface.Bus(interface=can_interface, channel=channel, bitrate=bitrate)
        self.notifier = can.Notifier(self.bus, [])
        self.servo = MksServo(self.bus, self.notifier, device_id)

    def load_config(self, config_path):
        """Load the configuration file with limits for degrees, speed, and acceleration."""
        if os.path.exists(config_path):
            with open(config_path, 'r') as file:
                return json.load(file)
        else:
            raise FileNotFoundError(f"Configuration file '{config_path}' not found.")

    def shutdown(self):
        """Shutdown the CAN bus and the notifier."""
        self.notifier.stop()
        self.bus.shutdown()

    def wait_for_motor_idle(self, timeout):
        """Wait for the motor to finish its current operation or until the timeout is reached."""
        start_time = time.perf_counter()
        while (time.perf_counter() - start_time < timeout) and self.servo.is_motor_running():
            time.sleep(0.1)  # Small sleep to prevent busy waiting
        return self.servo.is_motor_running()

    def clamp_value(self, value, max_value):
        """Clamp the value to the specified maximum limit."""
        return min(value, max_value)

    def execute_instruction(self, degrees, speed, acceleration, duration, label):
        # Clamp the values to the maximum limits from the config
        degrees = self.clamp_value(degrees, self.config['degrees_max'])
        speed = self.clamp_value(speed, self.config['speed_max'])
        acceleration = self.clamp_value(acceleration, self.config['acceleration_max'])

        start_time_dt = datetime.now()
        start_time = time.perf_counter()
        print(f"**[{self.format_time(start_time_dt)}]** Starting {label}: Moving to {degrees} degrees at speed {speed} with acceleration {acceleration}")

        # Move the motor to the specified degrees with the given speed and acceleration
        position_units = self.degrees_to_units(degrees)
        self.servo.run_motor_absolute_motion_by_axis(speed, acceleration, position_units)

        # Wait until the motor reaches the target position, ignoring the duration for now
        while self.servo.is_motor_running():
            time.sleep(0.1)  # Sleep briefly to prevent busy waiting

        # Calculate the actual time taken to reach the target position
        elapsed_time = time.perf_counter() - start_time

        # If the motor took longer than the specified duration, generate a warning
        if elapsed_time > duration:
            warning_msg = f"Warning: {label} did not complete within the specified duration of {duration} seconds, the actual time taken was: {elapsed_time:.2f} seconds."
            print(f"**[{self.format_time(datetime.now())}]** {warning_msg}")
            return elapsed_time, warning_msg

        # If the motor completed within the specified duration, calculate the remaining time
        remaining_time = duration - elapsed_time
        if remaining_time > 0:
            time.sleep(remaining_time)  # Sleep to complete the total duration

        return elapsed_time, None  # No warning, operation completed in time

    def execute_sequence_from_csv(self, file_path):
        """Execute a sequence of instructions from a CSV file."""
        if os.path.exists(file_path):
            sequence_df = pd.read_csv(file_path)
            for _, row in sequence_df.iterrows():
                self.execute_instruction(row['Degrees'], row['Speed'], row['Acceleration'], row['Duration'], row['Label'])
        else:
            raise FileNotFoundError(f"Sequence file '{file_path}' not found.")

    def format_time(self, dt):
        """Format the datetime object to a string with millisecond precision."""
        return dt.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

    def degrees_to_units(self, degrees):
        """Convert degrees to motor units."""
        return int(degrees * DEGREES_TO_UNITS)
    
    def units_to_degrees(self, units):
        """Convert motor units to degrees."""
        return int(units / DEGREES_TO_UNITS)
    
    def get_motor_degrees(self) -> int:
        """Get the current position of the motor in degrees."""
        return self.units_to_degrees(self.servo.read_encoder_value_addition())
    

if __name__ == "__main__":
    # Create an instance of the ServoController with the default configuration
    controller = ServoController()

    try:
        # Fetch the max values from the configuration
        max_degrees = controller.config['degrees_max']
        max_speed = controller.config['speed_max']
        max_acceleration = controller.config['acceleration_max']
        
        # Set a duration for the movement (adjust as needed)
        duration = 5  # 5 seconds to move to the max position
        
        # Move the motor to the maximum degrees with max speed and acceleration
        print("Moving to maximum position...")
        controller.execute_instruction(degrees=max_degrees, speed=max_speed, acceleration=max_acceleration, duration=duration, label="Move to Max Position")
        
        # Wait for 2 seconds before returning to 0 position
        time.sleep(2)
        
        # Move the motor back to 0 degrees with max speed and acceleration
        print("Returning to 0 degrees...")
        controller.execute_instruction(degrees=0, speed=max_speed, acceleration=max_acceleration, duration=duration, label="Return to 0 Position")
    
    except Exception as e:
        print(f"An error occurred: {e}")
    
    finally:
        # Shut down the controller
        controller.shutdown()
        print("Controller shutdown complete.")