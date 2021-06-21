import cv2
import time
import math
import serial
import numpy as np
import threading
import json
import sys
import atexit

port = '/dev/ttyACM0' 

buffer_string = ''
last_received = ''
ser = serial.Serial(port, 115200, timeout=2)
ser.flushInput()

def exit_handler():
    ser.close()
    
atexit.register(exit_handler)

#logging file setup
epoch = str(math.floor(time.time()))
f = open("log/" + sys.argv[1] + "_" +  epoch + ".csv", "x")
f.write("x_pos, y_pos, z_pos")

#home machine and set speed
print("homing...")
ser.write("G28 R\n".encode())
ser.write("M205 T75\n".encode())
print("sent homing")

#hang until we get a response from Marlin
last_command_complete = False
while(last_command_complete == False):
    response = ser.read_until()
    print(response)
    if(response == b'ok\n'):
        last_command_complete = True

#----------
#main loop, one cycle results in a row in the csv
#----------
while True:
    #defines which test should be run
    g = open('probe.gcode','r')
    for line in g:
        l = line.strip() # Strip all EOL characters for consistency
        print('Sending: ' + l)
        block = l + '\n'
        ser.write(block.encode()) # Send g-code block to grbl
        grbl_out = ser.readline() # Wait for grbl response with carriage return
        print(grbl_out.strip())

    #hang until all moves are complete so we capture an image only after the head is in position
    #for some reason, Marlin randomly chooses to not send back the M118 string, so I added a timeout to this bit of blocking code that is long enough for a ~30 second cycle
    last_command_complete = False
    timeout_time = time.time()
    while(last_command_complete == False):
        response = ser.read_until()
        print(response)
        if(response == b'test\r\n' or time.time() - timeout_time > 10040):
            last_command_complete = True
    last_command_complete = False
    timeout_time = time.time()
    while(last_command_complete == False):
        response = ser.read_until()
        print(response)
        if(response == b'ok\n' or time.time() - timeout_time > 5):
            last_command_complete = True
    while True:
        #do nothing
        print("exited loop")
    if cv2.waitKey(1) & 0xFF is ord(' '):
        break
