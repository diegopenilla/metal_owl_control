# controller.py
import can
import time
import os
import pandas as pd
from datetime import datetime
from core.mks_servo import MksServo

# Constants for conversion
DEGREES_TO_UNITS = 16390 / 360

class ServoController:
    def __init__(self, can_interface='slcan', channel='/dev/ttyACM0', bitrate=500000, device_id=1):
        self.bus = can.interface.Bus(interface=can_interface, channel=channel, bitrate=bitrate)
        self.notifier = can.Notifier(self.bus, [])
        self.servo = MksServo(self.bus, self.notifier, device_id)

    def shutdown(self):
        self.notifier.stop()
        
        self.bus.shutdown()

    def wait_for_motor_idle(self, timeout):
        start_time = time.perf_counter()
        while (time.perf_counter() - start_time < timeout) and self.servo.is_motor_running():
            time.sleep(0.1)  # Small sleep to prevent busy waiting
        return self.servo.is_motor_running()

    def execute_instruction(self, degrees, speed, duration, label):
        start_time_dt = datetime.now()
        start_time = time.perf_counter()
        print(f"**[{self.format_time(start_time_dt)}]** Starting {label}: Moving to {degrees} degrees at speed {speed}")

        # Move the motor to the specified degrees
        position_units = self.degrees_to_units(degrees)
        self.servo.run_motor_absolute_motion_by_axis(speed, 0, position_units)

        # Wait for the motor to stop or until the timeout
        motor_stopped = self.wait_for_motor_idle(duration)

        # Calculate remaining time to match the specified duration
        elapsed_time = time.perf_counter() - start_time
        remaining_time = duration - elapsed_time

        if remaining_time > 0:
            time.sleep(remaining_time)  # Sleep to complete the total duration

        end_time_dt = datetime.now()
        if motor_stopped:
            print(f"**[{self.format_time(end_time_dt)}]** {label} completed successfully.")
        else:
            print(f"**[{self.format_time(end_time_dt)}]** {label} did not complete within the specified duration.")

    def execute_sequence_from_csv(self, file_path):
        if os.path.exists(file_path):
            sequence_df = pd.read_csv(file_path)
            for _, row in sequence_df.iterrows():
                self.execute_instruction(row['Degrees'], row['Speed'], row['Duration'], row['Label'])

    def format_time(self, dt):
        return dt.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

    def degrees_to_units(self, degrees):
        return int(degrees * DEGREES_TO_UNITS)
    
    def units_to_degrees(self, units):
        return int(units / DEGREES_TO_UNITS)
    
    def get_motor_degrees(self)->int:
        return self.units_to_degrees(self.servo.read_encoder_value_addition())
    