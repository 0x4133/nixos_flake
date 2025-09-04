from hls_lfcd2 import Lidar
from time import sleep
import sys

try:
    # Check if the serial port exists and is accessible
    import os
    if not os.path.exists("/dev/ttyACM0"):
        print("Error: /dev/ttyACM0 not found. Please check if your LIDAR is connected.")
        sys.exit(1)
    
    print("Initializing LIDAR...")
    lidar = Lidar("/dev/ttyACM0", angle_offset=0)
    
    print("Starting LIDAR...")
    lidar.start()

    # required to obtain valid data of 360 degrees
    print("Waiting for LIDAR to initialize...")
    sleep(2)

    print(f'rpm = {lidar.get_rpm()}')
    print(f'distance = {lidar.get_distance()}')
    print(f'intensity = {lidar.get_intensity()}')

    # stopped lidar can be started again
    print("Stopping LIDAR...")
    lidar.stop()

    # once terminated, it can not be started
    print("Terminating LIDAR...")
    lidar.terminate()
    
    print("LIDAR operation completed successfully!")

except Exception as e:
    print(f"Error occurred: {e}")
    print("Make sure your LIDAR is properly connected and you have the necessary permissions.")
    sys.exit(1)
