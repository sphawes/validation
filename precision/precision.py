import cv2
import time
import math
import serial
import numpy as np
import threading
import json
import sys
import subprocess
import atexit

#defining port and cv thresholds
port = '/dev/ttyACM0' 
hsvLower = (80, 160, 160)
hsvUpper = (120, 255, 255)

w = 640.0
minRadius = 10
maxRadius = 40
buffer_string = ''
last_received = ''
font = cv2.FONT_HERSHEY_SIMPLEX
ser = serial.Serial(port, 115200, timeout=2)
ser.flushInput()

def exit_handler():
    ser.close()
    
atexit.register(exit_handler)

#connect to webcam
capture = cv2.VideoCapture(0)
#print(capture.get(cv2.CAP_PROP_FPS))

#setting camera exposure config
bash1 = "v4l2-ctl -c exposure_auto=1"
bash2 = "v4l2-ctl -c exposure_absolute=25"
process = subprocess.Popen(bash1.split(), stdout=subprocess.PIPE)
output, error = process.communicate()

process2 = subprocess.Popen(bash2.split(), stdout=subprocess.PIPE)
output,error = process2.communicate()

#logging file setup
epoch = str(math.floor(time.time()))
filename = "log/" + sys.argv[1] + "_" + epoch + ".csv"
f = open(filename, "x")
f.write("x_pos_pixel, y_pos_pixel")
f.close()

#home machine and set speed
print("homing...")
ser.write("G28 R\n".encode())
ser.write("M205 T75\n".encode())
ser.write("M92 X57.15 Y40.50 Z57.15 E4.43\n".encode())
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
    g = open('xy_cycle.gcode','r')
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
        if(response == b'test\r\n' or time.time() - timeout_time > 60):
            last_command_complete = True
    last_command_complete = False
    timeout_time = time.time()
    while(last_command_complete == False):
        response = ser.read_until()
        print(response)
        if(response == b'ok\n' or time.time() - timeout_time > 5):
            last_command_complete = True

    time.sleep(1)

    print("about to do the vision stuff!")
    #take image from webcam
    ret, image = capture.read()

    #scaling down for faster processing
    img_height, img_width, depth = image.shape
    scale = w / img_width
    h = img_height * scale
    image = cv2.resize(image, (0,0), fx=scale, fy=scale)
    scaledHeight, scaledWidth, scaledDepth = image.shape

    #image processing
    blurred = cv2.GaussianBlur(image, (11, 11), 0)
    hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)
    mask1 = cv2.inRange(hsv, hsvLower, hsvUpper)
    mask2 = cv2.erode(mask1, None, iterations=2)
    mask = cv2.dilate(mask2, None, iterations=2)

    #find contours
    cnts = cv2.findContours(mask.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[-2]
    center = None

    #establish coordinate variables for centerpoint of dot
    x = 0
    y = 0

    #only proceed if at least one contour was found
    if len(cnts) > 0:
		# find the largest contour in the mask, then use
		# it to compute the minimum enclosing circle and
		# centroid
        c = max(cnts, key=cv2.contourArea)
        ((x, y), radius) = cv2.minEnclosingCircle(c)
        M = cv2.moments(c)
        center = (int(M["m10"] / M["m00"]), int(M["m01"] / M["m00"]))

		# only proceed if the radius meets a minimum size
        if radius > minRadius and radius < maxRadius:

            cv2.circle(image, (int(x), int(y)), int(radius), (0, 255, 255), 2)
            cv2.circle(image, center, 5, (0, 0, 0), -1)

            posX = 100 - int((x / scaledWidth)*100)
            posY = int((y / scaledHeight)*100)
            posZ = int((radius*2) - (minRadius*2))
    else:
        x = -1
        y = -1

    # prints data to csv
    f = open(filename, "a")

    f.write(str(x) + ", " + str(y) + "\n")

    f.close()

    #prints flipped image with tracked blob superimposed
    image = cv2.flip(image, 1)
    cv2.imshow('precision', image)

    cv2.imshow('test', mask1)

    cv2.imwrite("image.jpg", image)
    cv2.imwrite("mask.jpg", mask1)
    #turn off the ring light
    ser.write("M150 P0\n".encode())

    if cv2.waitKey(1) & 0xFF is ord(' '):
        break
