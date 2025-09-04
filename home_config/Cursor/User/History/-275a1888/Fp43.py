from hls_lfcd2 import Lidar
from time import sleep

lidar = Lidar("COM6", angle_offset=0)
lidar.start()

# required to obtain valid data of 360 degress
sleep(2)

print(f'rpm = {lidar.get_rpm()}')
print(f'distance = {lidar.get_distance()}')
print(f'intensity = {lidar.get_intensity()}')

# stopped lidar can be started again
lidar.stop()

# once termindated, it can not be started
lidar.terminate()
