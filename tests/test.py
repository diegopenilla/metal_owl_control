import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../source')))

import can 
import time
from core.mks_servo import MksServo


# Initialize the interface
bus = can.interface.Bus(interface='slcan', channel='/dev/ttyACM0', bitrate=500000)
notifier = can.Notifier(bus, [])

# Connect to the servo, CAN ID 1
servo = MksServo(bus, notifier, 1)



def wait_for_motor_idle2(timeout):    
    start_time = time.perf_counter()
    while (time.perf_counter() - start_time < timeout) and servo.is_motor_running():
        print(servo.read_motor_speed(), flush=True)
        time.sleep(0.1)  # Small sleep to prevent busy waiting
    return servo.is_motor_running()

def move_motor(absolute_position, speed = 600):  
    print(f"Moving motor to absolute position {absolute_position}", flush=True)
    print(servo.run_motor_absolute_motion_by_axis(speed, 0, absolute_position), flush=True)
    wait_for_motor_idle2(30)
    value = servo.read_encoder_value_addition()
    error = absolute_position - value
    print(f"Movement at {absolute_position} with error {error}")    
    print(f"", flush=True)
    print()


if __name__ == "__main__":
    
    # Send a command
    pos = servo.read_encoder_value_addition()
    speed = servo.read_motor_speed()
    
    from core.can_motor import *

    enable_motor(servo, 1)
    
    print("step 1")
    move_motor(pos+3000, 10)
    
    print("step2")
    pos = servo.read_encoder_value_addition()
    move_motor(pos+3000, 10)
    
    print("returnt to 0 ")
    move_motor(0)
    
    pos = servo.read_encoder_value_addition()
    print(pos)
    

    # # # Close the connection
    notifier.stop()
    bus.shutdown()