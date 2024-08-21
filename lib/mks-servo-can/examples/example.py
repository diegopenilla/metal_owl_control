import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../source')))

import can 
import time
from mks_servo import MksServo


# Initialize the interface
bus = can.interface.Bus(interface='slcan', channel='/dev/ttyACM0', bitrate=500000)
notifier = can.Notifier(bus, [])

# Connect to the servo, CAN ID 1
servo = MksServo(bus, notifier, 1)

# Send a command
print(servo.read_encoder_value_addition())

# Close the connection
notifier.stop()
bus.shutdown()